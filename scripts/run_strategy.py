"""コードベースのストラテジーをバックテスト実行するCLI。

例:
  uv run python run_strategy.py --file strategies/ema_cross.py --code 7203 --days 365 --duration 1d
  uv run python run_strategy.py --file strategies/rsi_reversal.py --code ^N225 --days 365 --duration 1d --market ""
"""

import argparse
import json

from app.strategy import run_strategy_file
from enhanced_backtest import RiskManagement


def main():
    parser = argparse.ArgumentParser(description="コードベース・ストラテジーのバックテスト")
    parser.add_argument("--file", required=True, help="ストラテジーファイル (strategy(ctx) を含む)")
    parser.add_argument("--code", required=True, help="銘柄コード (例: 7203, ^N225)")
    parser.add_argument("--days", type=int, default=365, help="取得日数")
    parser.add_argument("--duration", default="1d", choices=["5s", "1m", "1h", "1d"], help="時間軸")
    parser.add_argument("--market", default="T", help="市場サフィックス (指数は空文字)")
    parser.add_argument("--capital", type=float, default=1_000_000, help="初期資金")
    parser.add_argument("--cost", type=float, default=0.1, help="片道取引コスト(％)")
    parser.add_argument("--slippage", type=float, default=0.02, help="スリッページ(％)")

    args = parser.parse_args()

    risk = RiskManagement(
        initial_capital=args.capital,
        transaction_cost_percent=args.cost,
        slippage_percent=args.slippage,
    )

    results = run_strategy_file(
        path=args.file,
        product_code=args.code,
        period_days=args.days,
        duration=args.duration,
        market=args.market,
        risk_management=risk,
    )

    metrics = results.get("metrics", {})
    print("=" * 60)
    print(f"銘柄: {args.code}  戦略: {args.file}")
    print(f"総取引数: {results.get('total_trades', 0)}")
    print(f"総損益: {metrics.get('total_profit', 0):,.2f}")
    print(f"勝率: {metrics.get('win_rate', 0):.2f}%")
    print(f"最大ドローダウン: {metrics.get('max_drawdown', 0):,.2f}")
    print(f"シャープレシオ: {metrics.get('sharpe_ratio', 0):.3f}")
    print(f"ロバストスコア: {metrics.get('robust_score', 0):.2f}")
    print("=" * 60)

    print(json.dumps(metrics, ensure_ascii=False, indent=2, default=str))


if __name__ == "__main__":
    main()
