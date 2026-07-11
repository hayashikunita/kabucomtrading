"""StrategyEngine のテスト（ネットワーク非依存）。"""

from app.strategy.engine import StrategyEngine, compile_strategy


def test_compile_strategy_returns_callable():
    fn = compile_strategy("def strategy(ctx):\n    pass\n")
    assert callable(fn)


def test_compile_strategy_missing_function_raises():
    import pytest

    with pytest.raises(ValueError):
        compile_strategy("x = 1\n")


def test_compile_strategy_blocks_import():
    import pytest

    # 制限ビルトインで import は使えない
    with pytest.raises(Exception):
        fn = compile_strategy("def strategy(ctx):\n    import os\n")
        fn(_DummyCtx())


class _DummyCtx:
    index = 0
    position = 0


def test_engine_runs_ema_cross(uptrend_candles):
    engine = StrategyEngine(product_code="TEST", candles=uptrend_candles)

    def strategy(ctx):
        fast = ctx.ta.ema(ctx.close, 5)
        slow = ctx.ta.ema(ctx.close, 20)
        ctx.plot(fast, title="fast")
        if ctx.ta.crossover(fast, slow):
            ctx.strategy.entry("long", ctx.strategy.long)
        elif ctx.ta.crossunder(fast, slow):
            ctx.strategy.close("long")

    results = engine.run(strategy)

    assert "metrics" in results
    assert "signals" in results
    assert "plots" in results
    assert "fast" in results["plots"]
    assert results["ohlcv"]["close"][0] == uptrend_candles[0].close
    # V字なので少なくとも1回はエントリーが発生する
    assert results["total_trades"] >= 1


def test_engine_empty_candles_returns_error():
    engine = StrategyEngine(product_code="TEST", candles=[])
    results = engine.run(lambda ctx: None)
    assert results.get("error") == "no_candles"


def test_engine_run_is_stateless_across_multiple_runs(uptrend_candles):
    engine = StrategyEngine(product_code="TEST", candles=uptrend_candles)

    def strategy(ctx):
        fast = ctx.ta.ema(ctx.close, 5)
        slow = ctx.ta.ema(ctx.close, 20)
        if ctx.ta.crossover(fast, slow):
            ctx.strategy.entry("long", ctx.strategy.long)
        elif ctx.ta.crossunder(fast, slow):
            ctx.strategy.close("long")

    first = engine.run(strategy)
    second = engine.run(strategy)

    assert first["total_trades"] == second["total_trades"]
    assert first["metrics"].get("total_profit", 0) == second["metrics"].get("total_profit", 0)


def test_engine_passes_advanced_exit_settings_to_backtest(uptrend_candles):
    engine = StrategyEngine(product_code="TEST", candles=uptrend_candles)

    def strategy(ctx, params):
        atr = ctx.ta.atr(14)
        if ctx.index == 0:
            return
        if ctx.index == 1 and ctx.position == 0:
            ctx.strategy.entry(
                "long",
                ctx.strategy.long,
                trailing_stop_pct=float(params.get("trail", 5.0)),
                break_even_trigger_pct=float(params.get("breakeven", 3.0)),
                max_bars_hold=int(params.get("max_bars", 5)),
                atr_stop_multiple=float(params.get("atr_mult", 1.5)),
                atr_value=float(atr[ctx.index]),
            )

    results = engine.run(
        strategy,
        params={"trail": 4.0, "breakeven": 2.0, "max_bars": 3, "atr_mult": 1.2},
    )

    assert results["signals"]
    first_signal = results["signals"][0]
    assert first_signal["risk"]["trailing_stop_pct"] == 4.0
    assert first_signal["risk"]["break_even_trigger_pct"] == 2.0
    assert first_signal["risk"]["max_bars_hold"] == 3
    assert first_signal["risk"]["atr_stop_multiple"] == 1.2
