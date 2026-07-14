"""BacktestMetrics のテスト。"""

import numpy as np

from backtest_metrics import BacktestMetrics


def _trade(profit):
    return {
        "entry_price": 1000,
        "exit_price": 1000 + profit,
        "profit": profit,
        "side": "BUY",
    }


def test_total_and_win_rate():
    m = BacktestMetrics([_trade(100), _trade(-50), _trade(200)])
    assert m.total_profit() == 250
    assert m.total_trades() == 3
    assert m.winning_trades() == 2
    assert np.isclose(m.win_rate(), 2 / 3 * 100)


def test_profit_factor():
    m = BacktestMetrics([_trade(100), _trade(-50)])
    # gross_profit=100, gross_loss=50
    assert np.isclose(m.profit_factor(), 2.0)


def test_profit_factor_no_loss_is_inf():
    m = BacktestMetrics([_trade(100), _trade(50)])
    assert m.profit_factor() == float("inf")


def test_max_drawdown():
    # 累積: 100, 50, 150 → 最大DD=50
    m = BacktestMetrics([_trade(100), _trade(-50), _trade(100)])
    assert np.isclose(m.max_drawdown(), 50)


def test_empty_metrics_are_safe():
    m = BacktestMetrics([])
    assert m.total_profit() == 0
    assert m.win_rate() == 0.0
    assert m.max_drawdown() == 0.0
    assert m.robust_score() == 0.0


def test_robust_score_bounds():
    m = BacktestMetrics([_trade(100), _trade(-50), _trade(200)])
    score = m.robust_score(initial_capital=1_000_000)
    assert 0.0 <= score <= 100.0


def test_get_all_metrics_contains_robust_score():
    m = BacktestMetrics([_trade(100), _trade(-50)])
    metrics = m.get_all_metrics(initial_capital=1_000_000, years=1.0)
    assert "robust_score" in metrics
    assert "sharpe_ratio" in metrics
    assert "max_drawdown" in metrics


def test_equity_growth_metrics_reward_monotonic_stable_curve():
    m = BacktestMetrics([_trade(100), _trade(120), _trade(140), _trade(160)])
    metrics = m.equity_growth_metrics(initial_capital=1_000_000)

    assert metrics["equity_monotonicity_rate"] == 100.0
    assert metrics["equity_slope_per_trade"] > 0
    assert metrics["equity_residual_std"] >= 0
    assert metrics["equity_growth_score"] > 0


def test_equity_growth_metrics_penalize_volatile_curve():
    stable = BacktestMetrics([_trade(100), _trade(100), _trade(100), _trade(100)])
    volatile = BacktestMetrics([_trade(400), _trade(-300), _trade(400), _trade(-300)])

    stable_score = stable.equity_growth_metrics(initial_capital=1_000_000)["equity_growth_score"]
    volatile_score = volatile.equity_growth_metrics(initial_capital=1_000_000)["equity_growth_score"]

    assert stable_score > volatile_score
