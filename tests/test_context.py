"""StrategyContext のテスト。"""

from datetime import datetime

import numpy as np

from app.strategy.context import StrategyContext


def build_context(closes):
    n = len(closes)
    times = [datetime(2024, 1, 1 + i) for i in range(n)]
    return StrategyContext(
        times=times,
        opens=closes,
        highs=[c + 1 for c in closes],
        lows=[c - 1 for c in closes],
        closes=closes,
        volumes=[1000] * n,
    )


def test_entry_records_buy_order_and_position():
    ctx = build_context([100, 101, 102])
    ctx.index = 1
    ctx.entry("long")
    orders = ctx.get_orders()
    assert len(orders) == 1
    assert orders[0]["type"] == "BUY"
    assert ctx.position == 1


def test_entry_records_stop_loss_and_take_profit_settings():
    ctx = build_context([100, 101, 102])
    ctx.index = 1
    ctx.strategy.entry(
        "id",
        ctx.strategy.long,
        stop_loss=95.0,
        take_profit=110.0,
        stop_loss_pct=3.0,
        take_profit_pct=5.0,
    )

    order = ctx.get_orders()[0]
    assert order["risk"] == {
        "stop_loss": 95.0,
        "take_profit": 110.0,
        "stop_loss_pct": 3.0,
        "take_profit_pct": 5.0,
        "trailing_stop_pct": None,
        "break_even_trigger_pct": None,
        "max_bars_hold": None,
        "atr_stop_multiple": None,
        "atr_value": None,
    }


def test_entry_records_advanced_exit_settings():
    ctx = build_context([100, 101, 102])
    ctx.index = 1
    atr = ctx.ta.atr(2)
    ctx.strategy.entry(
        "id",
        ctx.strategy.long,
        trailing_stop_pct=4.0,
        break_even_trigger_pct=2.0,
        max_bars_hold=5,
        atr_stop_multiple=1.5,
        atr_value=float(atr[ctx.index]),
    )

    risk = ctx.get_orders()[0]["risk"]
    assert risk["trailing_stop_pct"] == 4.0
    assert risk["break_even_trigger_pct"] == 2.0
    assert risk["max_bars_hold"] == 5
    assert risk["atr_stop_multiple"] == 1.5


def test_exit_records_sell_and_resets_position():
    ctx = build_context([100, 101, 102])
    ctx.index = 1
    ctx.entry("long")
    ctx.index = 2
    ctx.exit()
    orders = ctx.get_orders()
    assert len(orders) == 2
    assert orders[1]["type"] == "SELL"
    assert ctx.position == 0


def test_entry_reverse_closes_then_opens():
    ctx = build_context([100, 101, 102])
    ctx.index = 1
    ctx.entry("long")
    ctx.index = 2
    ctx.entry("short")  # ドテン
    orders = ctx.get_orders()
    # long決済(SELL) + short新規(SELL)
    assert len(orders) == 3
    assert ctx.position == -1


def test_double_entry_same_direction_is_noop():
    ctx = build_context([100, 101, 102])
    ctx.index = 0
    ctx.entry("long")
    ctx.index = 1
    ctx.entry("long")
    assert len(ctx.get_orders()) == 1


def test_plot_is_captured():
    ctx = build_context([100, 101, 102])
    ctx.plot([1, 2, 3], title="EMA")
    plots = ctx.get_plots()
    assert "EMA" in plots
    assert np.array_equal(plots["EMA"]["values"], np.array([1.0, 2.0, 3.0]))


def test_pine_namespaces_available():
    ctx = build_context([100, 101, 102, 103])
    assert callable(ctx.ta.ema)
    assert ctx.strategy.long == "long"
    ctx.index = 1
    ctx.strategy.entry("id", ctx.strategy.long)
    assert ctx.position == 1


def test_ta_namespace_exposes_all_talib_functions_dynamically():
    ctx = build_context([100, 101, 102, 103, 104, 105, 106, 107, 108, 109])

    # 明示ラッパー以外の TA-Lib 関数へアクセスできる
    ema_upper = ctx.ta.EMA(ctx.close, timeperiod=3)
    assert len(ema_upper) == len(ctx.close)

    funcs = ctx.ta.functions()
    assert "EMA" in funcs
    assert "RSI" in funcs


def test_ta_indicator_results_are_cached_for_same_arguments():
    ctx = build_context([100, 101, 102, 103, 104, 105, 106, 107, 108, 109])

    ema1 = ctx.ta.ema(ctx.close, 5)
    ema2 = ctx.ta.ema(ctx.close, 5)
    assert ema1 is ema2

    # 動的公開された TA-Lib 関数側でも同じキャッシュが効く
    upper1 = ctx.ta.EMA(ctx.close, timeperiod=5)
    upper2 = ctx.ta.EMA(ctx.close, timeperiod=5)
    assert upper1 is upper2
