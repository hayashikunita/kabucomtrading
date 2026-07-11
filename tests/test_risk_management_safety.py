"""RiskManagement の安全ガード検証。"""

from datetime import datetime, timedelta

from enhanced_backtest import EnhancedBacktest, RiskManagement


class _Candle:
    def __init__(self, time, close):
        self.time = time
        self.open = close
        self.high = close + 1
        self.low = max(0.0, close - 1)
        self.close = close
        self.volume = 1000


def _candles(closes):
    start = datetime(2024, 1, 1)
    return [_Candle(start + timedelta(days=i), c) for i, c in enumerate(closes)]


def test_position_size_returns_zero_for_invalid_price():
    rm = RiskManagement(initial_capital=1_000_000)

    assert rm.calculate_position_size(0.0) == 0
    assert rm.calculate_position_size(-1.0) == 0


def test_position_size_is_capped_by_max_quantity():
    rm = RiskManagement(initial_capital=1_000_000, max_position_quantity=10)

    qty = rm.calculate_position_size(1.0)
    assert qty == 10


def test_backtest_skips_open_when_signal_price_invalid():
    rm = RiskManagement(initial_capital=1_000_000)
    bt = EnhancedBacktest(product_code="TEST", candles=_candles([100, 101]), risk_management=rm)

    # 価格0は無効なのでポジションを開かない
    results = bt.execute_backtest(
        [{"time": datetime(2024, 1, 1), "type": "BUY", "price": 0.0, "indicators": {}}]
    )

    assert results["total_trades"] == 0
    assert rm.current_capital == 1_000_000


def test_backtest_uses_fixed_stop_loss_price_from_signal_risk():
    rm = RiskManagement(initial_capital=1_000_000, stop_loss_percent=None, take_profit_percent=None)
    bt = EnhancedBacktest(product_code="TEST", candles=_candles([100, 94]), risk_management=rm)

    results = bt.execute_backtest(
        [
            {
                "time": datetime(2024, 1, 1),
                "type": "BUY",
                "price": 100.0,
                "indicators": {},
                "risk": {"stop_loss": 95.0},
            },
        ]
    )

    assert results["total_trades"] == 1
    assert results["trades"][0]["close_reason"] == "STOP_LOSS"


def test_backtest_uses_take_profit_percent_from_signal_risk():
    rm = RiskManagement(initial_capital=1_000_000, stop_loss_percent=None, take_profit_percent=None)
    bt = EnhancedBacktest(product_code="TEST", candles=_candles([100, 106]), risk_management=rm)

    results = bt.execute_backtest(
        [
            {
                "time": datetime(2024, 1, 1),
                "type": "BUY",
                "price": 100.0,
                "indicators": {},
                "risk": {"take_profit_pct": 5.0},
            },
        ]
    )

    assert results["total_trades"] == 1
    assert results["trades"][0]["close_reason"] == "TAKE_PROFIT"


def test_backtest_uses_break_even_trigger_percent_from_signal_risk():
    rm = RiskManagement(initial_capital=1_000_000, stop_loss_percent=None, take_profit_percent=None)
    bt = EnhancedBacktest(product_code="TEST", candles=_candles([100, 105, 99]), risk_management=rm)

    results = bt.execute_backtest(
        [
            {
                "time": datetime(2024, 1, 1),
                "type": "BUY",
                "price": 100.0,
                "indicators": {},
                "risk": {"break_even_trigger_pct": 5.0},
            }
        ]
    )

    assert results["total_trades"] == 1
    assert results["trades"][0]["close_reason"] == "STOP_LOSS"
    assert results["trades"][0]["exit_price"] >= 99.9


def test_backtest_uses_trailing_stop_percent_from_signal_risk():
    rm = RiskManagement(initial_capital=1_000_000, stop_loss_percent=None, take_profit_percent=None)
    bt = EnhancedBacktest(product_code="TEST", candles=_candles([100, 110, 103]), risk_management=rm)

    results = bt.execute_backtest(
        [
            {
                "time": datetime(2024, 1, 1),
                "type": "BUY",
                "price": 100.0,
                "indicators": {},
                "risk": {"trailing_stop_pct": 5.0},
            }
        ]
    )

    assert results["total_trades"] == 1
    assert results["trades"][0]["close_reason"] == "STOP_LOSS"
    assert results["trades"][0]["profit"] > 0


def test_backtest_uses_max_bars_hold_from_signal_risk():
    rm = RiskManagement(initial_capital=1_000_000, stop_loss_percent=None, take_profit_percent=None)
    bt = EnhancedBacktest(product_code="TEST", candles=_candles([100, 101, 102]), risk_management=rm)

    results = bt.execute_backtest(
        [
            {
                "time": datetime(2024, 1, 1),
                "type": "BUY",
                "price": 100.0,
                "indicators": {},
                "risk": {"max_bars_hold": 2},
            }
        ]
    )

    assert results["total_trades"] == 1
    assert results["trades"][0]["close_reason"] == "TIME_STOP"


def test_backtest_uses_atr_stop_multiple_from_signal_risk():
    rm = RiskManagement(initial_capital=1_000_000, stop_loss_percent=None, take_profit_percent=None)
    bt = EnhancedBacktest(product_code="TEST", candles=_candles([100, 95]), risk_management=rm)

    results = bt.execute_backtest(
        [
            {
                "time": datetime(2024, 1, 1),
                "type": "BUY",
                "price": 100.0,
                "indicators": {},
                "risk": {"atr_stop_multiple": 2.0, "atr_value": 2.0},
            }
        ]
    )

    assert results["total_trades"] == 1
    assert results["trades"][0]["close_reason"] == "STOP_LOSS"
