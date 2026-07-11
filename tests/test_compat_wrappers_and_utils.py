import importlib

from app.backtest.backtest_metrics import BacktestMetrics as AppBacktestMetrics
from app.backtest.backtest_visualizer import BacktestVisualizer as AppBacktestVisualizer
from app.backtest.trade_logger import TradeLogger as AppTradeLogger
from app.backtest.enhanced_backtest import EnhancedBacktest as AppEnhancedBacktest
from app.backtest.enhanced_backtest import RiskManagement as AppRiskManagement
from utils.utils import Serializer, bool_from_str


def test_backtest_wrapper_exports_match_app_modules():
    assert importlib.import_module("backtest_metrics").BacktestMetrics is AppBacktestMetrics
    assert importlib.import_module("backtest_visualizer").BacktestVisualizer is AppBacktestVisualizer
    assert importlib.import_module("trade_logger").TradeLogger is AppTradeLogger


def test_enhanced_backtest_wrapper_exports_match_app_module():
    module = importlib.import_module("enhanced_backtest")
    assert module.EnhancedBacktest is AppEnhancedBacktest
    assert module.RiskManagement is AppRiskManagement
    assert callable(module.main)


def test_cli_wrapper_modules_expose_main_callable():
    assert callable(importlib.import_module("run_strategy").main)
    assert callable(importlib.import_module("import_yahoo_to_db").main)
    assert callable(importlib.import_module("prepare_candle_table").main)


def test_bool_from_str_and_serializer_value():
    assert bool_from_str("TRUE") is True
    assert bool_from_str("false") is False
    assert bool_from_str("invalid") is False

    class _Obj(Serializer):
        def __init__(self):
            self.a = 1
            self.b = None

    class _Empty(Serializer):
        def __init__(self):
            self.a = None

    assert _Obj().value == {"a": 1}
    assert _Empty().value is None
