"""複数銘柄を一括で最適化し、ランキングを出力するCLI。"""

from __future__ import annotations

import argparse
import json
import sys
import time
from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd
from sqlalchemy import text

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from app.models.base import engine
from app.strategy.engine import StrategyEngine, compile_strategy
from app.strategy.optimization_utils import build_param_grid, objective_info
from enhanced_backtest import RiskManagement

OBJECTIVE_LABELS = [
    "ロバストスコア(最大化)",
    "純利益(最大化)",
    "期待値(円/1トレード, 最大化)",
    "安定成長スコア(最大化)",
    "シャープレシオ(最大化)",
    "最大ドローダウン(最小化)",
    "勝率(最大化)",
]


def _table_suffix(duration: str) -> str:
    return duration.upper()


def _decode_code_from_table(table_name: str, duration: str) -> str | None:
    prefix = "CANDLE_"
    suffix = f"_{_table_suffix(duration)}"
    if not table_name.startswith(prefix) or not table_name.endswith(suffix):
        return None

    body = table_name[len(prefix) : -len(suffix)]
    if not body:
        return None

    # create_candle_class で ^ は IDX_ に変換される
    if body.startswith("IDX_"):
        return "^" + body[len("IDX_") :]
    return body


def load_codes_from_db(duration: str) -> list[str]:
    suffix = _table_suffix(duration)
    with engine.connect() as conn:
        rows = conn.execute(
            text("SELECT name FROM sqlite_master WHERE type='table' AND name LIKE :pattern ORDER BY name"),
            {"pattern": f"CANDLE_%_{suffix}"},
        ).fetchall()

    codes: list[str] = []
    for (name,) in rows:
        code = _decode_code_from_table(str(name), duration)
        if code:
            codes.append(code)

    return list(dict.fromkeys(codes))


def load_codes_from_file(path: str) -> list[str]:
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(f"codes file not found: {path}")

    # 1行1銘柄を想定。カンマ区切りにも対応。
    text_data = p.read_text(encoding="utf-8")
    tokens = []
    for line in text_data.splitlines():
        for t in line.replace(",", " ").split():
            tokens.append(t.strip())

    codes = [t for t in tokens if t]
    return list(dict.fromkeys(codes))


def calc_objective(metrics: dict, objective_key: str) -> float:
    total_trades = int(metrics.get("total_trades", 0) or 0)
    total_profit = float(metrics.get("total_profit", 0.0) or 0.0)

    if objective_key == "expectancy_per_trade":
        return float(total_profit / total_trades) if total_trades > 0 else float("nan")

    value = metrics.get(objective_key)
    if value is None:
        return float("nan")
    try:
        return float(value)
    except Exception:
        return float("nan")


def optimize_symbol(
    code: str,
    strategy_fn,
    grid: list[dict],
    objective_key: str,
    maximize: bool,
    exclude_no_trade: bool,
    period_days: int,
    duration: str,
    market: str,
    risk: RiskManagement,
) -> dict:
    engine_obj = StrategyEngine.from_db_or_yahoo(
        product_code=code,
        period_days=period_days,
        duration=duration,
        market=market,
        risk_management=risk,
        force_refresh=False,
    )

    if not engine_obj.candles:
        return {
            "symbol": code,
            "status": "no_data",
            "data_source": engine_obj.data_source,
            "best_params": {},
            "objective": np.nan,
            "total_trades": 0,
        }

    best_score = None
    best_metrics = None
    best_params = None
    valid_trials = 0

    for params in grid:
        result = engine_obj.run(strategy_fn, params=params)
        metrics = result.get("metrics", {})
        score = calc_objective(metrics, objective_key)
        total_trades = int(metrics.get("total_trades", 0) or 0)

        if exclude_no_trade and total_trades <= 0:
            continue
        if np.isnan(score):
            continue

        valid_trials += 1
        if best_score is None:
            best_score = score
            best_metrics = metrics
            best_params = params
            continue

        if maximize and score > best_score:
            best_score = score
            best_metrics = metrics
            best_params = params
        elif (not maximize) and score < best_score:
            best_score = score
            best_metrics = metrics
            best_params = params

    if best_metrics is None:
        return {
            "symbol": code,
            "status": "no_valid_trial",
            "data_source": engine_obj.data_source,
            "best_params": {},
            "objective": np.nan,
            "total_trades": 0,
            "valid_trials": 0,
            "executed_trials": len(grid),
        }

    return {
        "symbol": code,
        "status": "ok",
        "data_source": engine_obj.data_source,
        "best_params": best_params or {},
        "objective": float(best_score),
        "total_profit": float(best_metrics.get("total_profit", 0.0) or 0.0),
        "total_trades": int(best_metrics.get("total_trades", 0) or 0),
        "win_rate": float(best_metrics.get("win_rate", 0.0) or 0.0),
        "max_drawdown": float(best_metrics.get("max_drawdown", 0.0) or 0.0),
        "sharpe_ratio": float(best_metrics.get("sharpe_ratio", 0.0) or 0.0),
        "robust_score": float(best_metrics.get("robust_score", 0.0) or 0.0),
        "valid_trials": valid_trials,
        "executed_trials": len(grid),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="全銘柄一括最適化")
    parser.add_argument("--strategy-file", required=True, help="strategy(ctx, params) を含むPythonファイル")
    parser.add_argument("--optimize-spec", required=True, help="最適化範囲テキスト。例: fast=5:30:5")
    parser.add_argument("--objective", default=OBJECTIVE_LABELS[1], choices=OBJECTIVE_LABELS, help="目的関数")
    parser.add_argument("--duration", default="1d", choices=["5s", "1m", "1h", "1d"], help="時間軸")
    parser.add_argument("--days", type=int, default=365, help="取得日数")
    parser.add_argument("--market", default="T", help="市場サフィックス")
    parser.add_argument("--max-trials", type=int, default=200, help="銘柄あたりの最大試行数")
    parser.add_argument("--include-no-trade", action="store_true", help="取引0件も候補に含める")
    parser.add_argument("--codes-file", default="", help="対象銘柄ファイル(省略時DB全銘柄)")
    parser.add_argument("--max-symbols", type=int, default=0, help="先頭N銘柄のみ実行(0で全件)")
    parser.add_argument("--sleep-sec", type=float, default=0.0, help="銘柄間の待機秒")
    parser.add_argument("--capital", type=float, default=1_000_000, help="初期資金")
    parser.add_argument("--cost", type=float, default=0.1, help="片道取引コスト(%%)")
    parser.add_argument("--slippage", type=float, default=0.02, help="スリッページ(%%)")
    parser.add_argument("--top-n", type=int, default=20, help="表示する上位件数")
    parser.add_argument("--output", default="", help="出力CSVパス")

    args = parser.parse_args()

    strategy_code = Path(args.strategy_file).read_text(encoding="utf-8")
    strategy_fn = compile_strategy(strategy_code)

    objective_key, maximize = objective_info(args.objective)
    optimize_spec_text = args.optimize_spec.replace("\\n", "\n")
    grid = build_param_grid(optimize_spec_text, max_trials=int(args.max_trials))
    if not grid:
        raise SystemExit("optimize_spec からパラメータ候補を作成できませんでした")

    if args.codes_file:
        codes = load_codes_from_file(args.codes_file)
    else:
        codes = load_codes_from_db(args.duration)

    if args.max_symbols > 0:
        codes = codes[: args.max_symbols]

    if not codes:
        raise SystemExit("対象銘柄が見つかりません。DBまたは codes-file を確認してください")

    risk = RiskManagement(
        initial_capital=float(args.capital),
        transaction_cost_percent=float(args.cost),
        slippage_percent=float(args.slippage),
    )

    rows: list[dict] = []
    total = len(codes)
    print(f"start bulk optimize symbols={total} trials_per_symbol={len(grid)} objective={args.objective}")

    for idx, code in enumerate(codes, start=1):
        row = optimize_symbol(
            code=code,
            strategy_fn=strategy_fn,
            grid=grid,
            objective_key=objective_key,
            maximize=maximize,
            exclude_no_trade=not args.include_no_trade,
            period_days=int(args.days),
            duration=args.duration,
            market=args.market,
            risk=risk,
        )
        rows.append(row)
        print(
            f"[{idx}/{total}] symbol={code} status={row.get('status')} objective={row.get('objective')} params={row.get('best_params')}"
        )
        if args.sleep_sec > 0:
            time.sleep(float(args.sleep_sec))

    df = pd.DataFrame(rows)
    ok_df = df[df["status"] == "ok"].copy()
    if not ok_df.empty:
        ok_df = ok_df.sort_values("objective", ascending=not maximize).reset_index(drop=True)

    out_path = args.output.strip()
    if not out_path:
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        out_path = f"results/bulk_optimize_{args.duration}_{ts}.csv"
    Path(out_path).parent.mkdir(parents=True, exist_ok=True)

    # best_params はJSON文字列で保存しやすくする
    save_df = df.copy()
    if "best_params" in save_df.columns:
        save_df["best_params"] = save_df["best_params"].map(lambda x: json.dumps(x, ensure_ascii=False))
    save_df.to_csv(out_path, index=False, encoding="utf-8-sig")

    print("=" * 80)
    print(f"saved dataframe: {out_path}")
    print(f"total_symbols={len(df)} ok={len(ok_df)} no_data={(df['status'] == 'no_data').sum()} no_valid_trial={(df['status'] == 'no_valid_trial').sum()}")

    if ok_df.empty:
        print("有効な最適化結果がありませんでした。")
        return

    display_cols = [
        "symbol",
        "objective",
        "total_profit",
        "total_trades",
        "win_rate",
        "max_drawdown",
        "sharpe_ratio",
        "robust_score",
        "best_params",
    ]
    available_cols = [c for c in display_cols if c in ok_df.columns]
    print(f"top {args.top_n} symbols")
    print(ok_df[available_cols].head(int(args.top_n)).to_string(index=False))

    best = ok_df.iloc[0]
    print("-" * 80)
    print("最上位銘柄")
    print(f"symbol={best['symbol']}")
    print(f"objective={best['objective']}")
    print(f"best_params={best['best_params']}")


if __name__ == "__main__":
    main()
