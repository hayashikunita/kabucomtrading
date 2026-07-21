"""
複数銘柄の一括バックテスト機能
"""

import json
import logging
import os
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from itertools import product
from pathlib import Path
from typing import Dict, List, Optional

import pandas as pd

if __package__ is None or __package__ == "":
    repo_root = Path(__file__).resolve().parent.parent
    if str(repo_root) not in sys.path:
        sys.path.insert(0, str(repo_root))

import settings
from app.strategy.engine import StrategyEngine, compile_strategy
from enhanced_backtest import RiskManagement

logging.basicConfig(level=logging.INFO, stream=sys.stdout)
logger = logging.getLogger(__name__)


def run_backtest_analysis(product_code: str, period_days: int, duration: str, detailed: bool = False):
    """銘柄1つ分の戦略最適化バックテストを実行する。"""
    risk = RiskManagement(
        initial_capital=1_000_000,
        transaction_cost_percent=0.1,
        slippage_percent=0.02,
    )

    engine = StrategyEngine.from_yahoo(
        product_code=product_code,
        period_days=period_days,
        duration=duration,
        market="T",
        risk_management=risk,
    )

    strategy_specs = {
        "ema": {
            "code": """
def strategy(ctx, params):
    ta = ctx.ta
    fast_n = int(params.get('period1', 12))
    slow_n = int(params.get('period2', 26))
    fast = ta.ema(ctx.close, fast_n)
    slow = ta.ema(ctx.close, slow_n)
    if ta.crossover(fast, slow) and ctx.position == 0:
        ctx.strategy.entry('long', ctx.strategy.long)
    elif ta.crossunder(fast, slow) and ctx.position == 1:
        ctx.strategy.close('long')
""",
            "params": [
                {"period1": p1, "period2": p2}
                for p1, p2 in product([5, 7, 10, 12, 14, 20], [20, 26, 30, 50, 75])
                if p1 < p2
            ],
        },
        "bollinger_bands": {
            "code": """
def strategy(ctx, params):
    ta = ctx.ta
    n = int(params.get('n', 20))
    k = float(params.get('k', 2.0))
    upper, middle, lower = ta.bbands(ctx.close, n, k)
    price = ctx.close[ctx.index]
    if price != price:
        return
    if price < lower[ctx.index] and ctx.position == 0:
        ctx.strategy.entry('long', ctx.strategy.long)
    elif price > upper[ctx.index] and ctx.position == 1:
        ctx.strategy.close('long')
""",
            "params": [{"n": n, "k": k} for n, k in product([10, 20, 30], [1.5, 2.0, 2.5])],
        },
        "ichimoku": {
            "code": """
def strategy(ctx, params):
    ta = ctx.ta
    conv = ta.sma((ctx.high + ctx.low) / 2.0, 9)
    base = ta.sma((ctx.high + ctx.low) / 2.0, 26)
    if ta.crossover(conv, base) and ctx.position == 0:
        ctx.strategy.entry('long', ctx.strategy.long)
    elif ta.crossunder(conv, base) and ctx.position == 1:
        ctx.strategy.close('long')
""",
            "params": [{}],
        },
        "rsi": {
            "code": """
def strategy(ctx, params):
    ta = ctx.ta
    period = int(params.get('period', 14))
    buy_thr = float(params.get('buy_threshold', 30))
    sell_thr = float(params.get('sell_threshold', 70))
    rsi = ta.rsi(ctx.close, period)
    value = rsi[ctx.index]
    if value != value:
        return
    if value < buy_thr and ctx.position == 0:
        ctx.strategy.entry('long', ctx.strategy.long)
    elif value > sell_thr and ctx.position == 1:
        ctx.strategy.close('long')
""",
            "params": [
                {"period": period, "buy_threshold": buy_thr, "sell_threshold": sell_thr}
                for period, buy_thr, sell_thr in product([8, 14, 21], [20, 25, 30], [65, 70, 75])
                if buy_thr < sell_thr
            ],
        },
        "macd": {
            "code": """
def strategy(ctx, params):
    ta = ctx.ta
    fast = int(params.get('fast_period', 12))
    slow = int(params.get('slow_period', 26))
    signal = int(params.get('signal_period', 9))
    macd_line, signal_line, _ = ta.macd(ctx.close, fast, slow, signal)
    if ta.crossover(macd_line, signal_line) and ctx.position == 0:
        ctx.strategy.entry('long', ctx.strategy.long)
    elif ta.crossunder(macd_line, signal_line) and ctx.position == 1:
        ctx.strategy.close('long')
""",
            "params": [
                {"fast_period": fast, "slow_period": slow, "signal_period": signal}
                for fast, slow, signal in product([8, 12], [17, 26], [5, 9])
                if fast < slow
            ],
        },
    }

    summary_results: Dict = {}
    detailed_results: Dict = {}

    for strategy_name, spec in strategy_specs.items():
        strategy_fn = compile_strategy(spec["code"])
        all_rows = []

        for params in spec["params"]:
            result = engine.run(strategy_fn, params)
            perf = float(result.get("risk_management_stats", {}).get("return_percent", 0.0))

            row = {**params}
            row["performance"] = perf
            row["total_trades"] = int(result.get("total_trades", 0))
            row["win_rate"] = float(result.get("metrics", {}).get("win_rate", 0.0))
            row["max_drawdown"] = float(result.get("metrics", {}).get("max_drawdown", 0.0))
            row["sharpe_ratio"] = float(result.get("metrics", {}).get("sharpe_ratio", 0.0))
            all_rows.append(row)

        if not all_rows:
            continue

        best = max(all_rows, key=lambda x: x["performance"])
        summary_results[strategy_name] = {
            k: v for k, v in best.items() if k not in ["total_trades", "win_rate", "max_drawdown", "sharpe_ratio"]
        }

        if detailed:
            best_params = {
                k: v for k, v in best.items() if k not in ["performance", "total_trades", "win_rate", "max_drawdown", "sharpe_ratio"]
            }
            detailed_results[strategy_name] = {
                "best_performance": float(best["performance"]),
                "best_params": best_params,
                "all_results": all_rows,
            }

    return summary_results, detailed_results if detailed else None


class MultiStockBacktest:
    """複数銘柄の一括バックテスト"""

    def __init__(self, product_codes: List[str], period_days: int, duration: str, max_workers: int = 4):
        """
        Args:
            product_codes: 銘柄コードのリスト
            period_days: バックテスト期間（日数）
            duration: 時間軸
            max_workers: 並列処理の最大ワーカー数
        """
        self.product_codes = product_codes
        self.period_days = period_days
        self.duration = duration
        self.max_workers = max_workers
        self.results = {}

    def run_single_backtest(self, product_code: str, detailed: bool = False) -> Dict:
        """単一銘柄のバックテストを実行"""
        logger.info(f"action=run_single_backtest product_code={product_code} status=start")

        try:
            results, detailed_results = run_backtest_analysis(
                product_code=product_code,
                period_days=self.period_days,
                duration=self.duration,
                detailed=detailed,
            )

            if not results:
                raise RuntimeError("no_backtest_results")

            result = {
                "product_code": product_code,
                "success": True,
                "results": results,
                "detailed_results": detailed_results if detailed else None,
            }

            logger.info(f"action=run_single_backtest product_code={product_code} status=success")
            return result

        except Exception as e:
            logger.error(f"action=run_single_backtest product_code={product_code} error={str(e)}")
            return {
                "product_code": product_code,
                "success": False,
                "error": str(e),
            }

    def run_all(self, detailed: bool = False, parallel: bool = True):
        """すべての銘柄のバックテストを実行"""
        logger.info(f"action=run_all total_stocks={len(self.product_codes)} parallel={parallel}")

        if parallel:
            # 並列実行
            with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
                futures = {
                    executor.submit(self.run_single_backtest, code, detailed): code for code in self.product_codes
                }

                for future in as_completed(futures):
                    result = future.result()
                    self.results[result["product_code"]] = result

        else:
            # 順次実行
            for code in self.product_codes:
                result = self.run_single_backtest(code, detailed)
                self.results[code] = result

        logger.info("action=run_all status=complete")

    def get_ranking(self, metric: str = "total_profit", top_n: int = 10) -> pd.DataFrame:
        """指定した指標でランキングを作成"""
        rankings = []

        for code, result in self.results.items():
            if not result.get("success"):
                continue

            row = {"product_code": code}

            # 各戦略の結果を取得
            for strategy in ["ema", "bollinger_bands", "rsi", "macd", "ichimoku"]:
                if strategy in result["results"]:
                    perf = result["results"][strategy].get("performance", 0)
                    row[f"{strategy}_performance"] = perf

            rankings.append(row)

        df = pd.DataFrame(rankings)

        if df.empty:
            return df

        # 指定された指標でソート
        if metric in df.columns:
            df = df.sort_values(metric, ascending=False)

        return df.head(top_n)

    def save_results(self, filename: Optional[str] = None):
        """結果をJSONファイルに保存"""
        filename = filename or settings.multi_stock_results_file
        output = {
            "period_days": self.period_days,
            "duration": self.duration,
            "timestamp": datetime.now().isoformat(),
            "total_stocks": len(self.product_codes),
            "successful": sum(1 for r in self.results.values() if r.get("success")),
            "failed": sum(1 for r in self.results.values() if not r.get("success")),
            "results": self.results,
        }

        with open(filename, "w", encoding="utf-8") as f:
            json.dump(output, f, indent=2, ensure_ascii=False)

        logger.info(f"action=save_results file={filename}")

    def save_ranking_csv(self, output_dir: Optional[str] = None):
        """各戦略のランキングをCSVに保存"""
        output_dir = output_dir or settings.backtest_rankings_dir

        os.makedirs(output_dir, exist_ok=True)

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        strategies = ["ema", "bollinger_bands", "rsi", "macd", "ichimoku"]

        for strategy in strategies:
            rankings = []

            for code, result in self.results.items():
                if not result.get("success"):
                    continue

                if strategy in result["results"]:
                    perf = result["results"][strategy].get("performance", 0)
                    rankings.append({"product_code": code, "performance": perf})

            if rankings:
                df = pd.DataFrame(rankings)
                df = df.sort_values("performance", ascending=False)

                filename = f"{output_dir}/ranking_{strategy}_{timestamp}.csv"
                df.to_csv(filename, index=False, encoding="utf-8-sig")
                logger.info(f"action=save_ranking_csv strategy={strategy} file={filename}")

    def print_summary(self):
        """結果サマリーを表示"""
        print("\n" + "=" * 80)
        print("複数銘柄バックテスト結果サマリー")
        print("=" * 80)
        print(f"期間: {self.period_days}日")
        print(f"時間軸: {self.duration}")
        print(f"対象銘柄数: {len(self.product_codes)}")
        print(f"成功: {sum(1 for r in self.results.values() if r.get('success'))}")
        print(f"失敗: {sum(1 for r in self.results.values() if not r.get('success'))}")
        print("-" * 80)

        # 各戦略のトップ5を表示
        strategies = ["ema", "bollinger_bands", "rsi", "macd", "ichimoku"]
        strategy_names = {
            "ema": "EMA",
            "bollinger_bands": "Bollinger Bands",
            "rsi": "RSI",
            "macd": "MACD",
            "ichimoku": "Ichimoku",
        }

        for strategy in strategies:
            print(f"\n【{strategy_names[strategy]}】トップ5:")
            rankings = []

            for code, result in self.results.items():
                if not result.get("success"):
                    continue

                if strategy in result["results"]:
                    perf = result["results"][strategy].get("performance", 0)
                    rankings.append({"product_code": code, "performance": perf})

            if rankings:
                df = pd.DataFrame(rankings)
                df = df.sort_values("performance", ascending=False).head(5)

                for _, row in df.iterrows():
                    print(f"  {row['product_code']}: {row['performance']:.2f}")
            else:
                print("  データなし")

        print("\n" + "=" * 80)


def main():
    """メイン実行関数"""
    import argparse

    parser = argparse.ArgumentParser(description="複数銘柄バックテスト")
    parser.add_argument("--codes", nargs="+", required=True, help="銘柄コードのリスト")
    parser.add_argument("--period", type=int, default=settings.past_period, help="期間（日数）")
    parser.add_argument("--duration", type=str, default=settings.trade_duration, help="時間軸")
    parser.add_argument("--detailed", action="store_true", help="詳細バックテスト")
    parser.add_argument("--parallel", action="store_true", help="並列実行")
    parser.add_argument("--workers", type=int, default=4, help="並列ワーカー数")

    args = parser.parse_args()

    print("\n複数銘柄バックテスト開始")
    print(f"対象銘柄: {', '.join(args.codes)}")
    print(f"期間: {args.period}日")
    print(f"時間軸: {args.duration}")
    print(f'詳細モード: {"有効" if args.detailed else "無効"}')
    print(f'並列実行: {"有効" if args.parallel else "無効"}')
    print()

    # バックテスト実行
    multi_backtest = MultiStockBacktest(
        product_codes=args.codes, period_days=args.period, duration=args.duration, max_workers=args.workers
    )

    multi_backtest.run_all(detailed=args.detailed, parallel=args.parallel)

    # 結果表示
    multi_backtest.print_summary()

    # 結果保存
    multi_backtest.save_results()
    multi_backtest.save_ranking_csv()

    print("\nバックテスト完了！")
    print(f"結果は {settings.multi_stock_results_file} に保存されました。")
    print(f"ランキングは {settings.backtest_rankings_dir} フォルダに保存されました。")


if __name__ == "__main__":
    main()
