"""互換レイヤー: 実体は app.backtest.enhanced_backtest。"""

from app.backtest.enhanced_backtest import EnhancedBacktest, RiskManagement, main

__all__ = ["EnhancedBacktest", "RiskManagement", "main"]


if __name__ == "__main__":
    main()
