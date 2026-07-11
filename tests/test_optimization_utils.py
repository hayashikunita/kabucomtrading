"""最適化ユーティリティのテスト。"""

import pytest

from app.strategy.optimization_utils import build_param_grid, objective_info, result_signature


def test_build_param_grid_with_range_and_list():
    spec = """
# comment
fast=5:9:2
slow=20,30
"""
    grid = build_param_grid(spec, max_trials=100)

    assert len(grid) == 6
    assert grid[0] == {"fast": 5, "slow": 20}
    assert grid[-1] == {"fast": 9, "slow": 30}


def test_build_param_grid_respects_max_trials():
    spec = "a=1,2,3\nb=10,20,30"
    grid = build_param_grid(spec, max_trials=4)

    assert len(grid) == 4


def test_build_param_grid_invalid_format_raises():
    with pytest.raises(ValueError):
        build_param_grid("fast:5:20:1", max_trials=10)


def test_build_param_grid_invalid_step_raises():
    with pytest.raises(ValueError):
        build_param_grid("fast=5:20:0", max_trials=10)


def test_build_param_grid_empty_returns_empty_list():
    grid = build_param_grid("\n# no params\n", max_trials=10)
    assert grid == []


def test_objective_info_mapping():
    key, maximize = objective_info("純利益(最大化)")
    assert key == "total_profit"
    assert maximize is True

    key, maximize = objective_info("最大ドローダウン(最小化)")
    assert key == "max_drawdown"
    assert maximize is False


def test_result_signature_same_trades_same_hash():
    trial_a = {
        "trades": [
            {
                "entry_time": "2024-01-01 09:00:00",
                "exit_time": "2024-01-02 09:00:00",
                "side": "BUY",
                "profit": 123.456,
            }
        ]
    }
    trial_b = {
        "trades": [
            {
                "entry_time": "2024-01-01 09:00:00",
                "exit_time": "2024-01-02 09:00:00",
                "side": "BUY",
                "profit": 123.456,
            }
        ]
    }

    assert result_signature(trial_a) == result_signature(trial_b)


def test_result_signature_different_trades_different_hash():
    trial_a = {
        "trades": [
            {
                "entry_time": "2024-01-01 09:00:00",
                "exit_time": "2024-01-02 09:00:00",
                "side": "BUY",
                "profit": 100.0,
            }
        ]
    }
    trial_b = {
        "trades": [
            {
                "entry_time": "2024-01-01 09:00:00",
                "exit_time": "2024-01-02 09:00:00",
                "side": "BUY",
                "profit": 101.0,
            }
        ]
    }

    assert result_signature(trial_a) != result_signature(trial_b)
