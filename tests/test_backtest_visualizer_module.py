from datetime import datetime, timedelta

from app.backtest.backtest_visualizer import BacktestVisualizer


def _trades():
    t0 = datetime(2024, 1, 1)
    return [
        {"profit": 100.0, "exit_time": t0 + timedelta(days=10)},
        {"profit": -50.0, "exit_time": t0 + timedelta(days=40)},
        {"profit": 120.0, "exit_time": t0 + timedelta(days=70)},
    ]


def test_plot_methods_create_files(tmp_path):
    v = BacktestVisualizer(_trades(), figsize=(6, 4))

    p1 = tmp_path / "equity.png"
    p2 = tmp_path / "drawdown.png"
    p3 = tmp_path / "dist.png"
    p4 = tmp_path / "monthly.png"
    p5 = tmp_path / "heatmap.png"

    v.plot_equity_curve(save_path=str(p1))
    v.plot_drawdown(save_path=str(p2))
    v.plot_profit_distribution(save_path=str(p3))
    v.plot_monthly_returns(save_path=str(p4))
    v.plot_parameter_heatmap(
        [
            {"n": 10, "k": 1.5, "performance": 100.0},
            {"n": 10, "k": 2.0, "performance": 120.0},
            {"n": 20, "k": 1.5, "performance": 130.0},
            {"n": 20, "k": 2.0, "performance": 90.0},
        ],
        "n",
        "k",
        save_path=str(p5),
    )

    assert p1.exists()
    assert p2.exists()
    assert p3.exists()
    assert p4.exists()
    assert p5.exists()


def test_create_comprehensive_report_outputs_all_files(tmp_path):
    v = BacktestVisualizer(_trades(), figsize=(6, 4))
    v.create_comprehensive_report(str(tmp_path), prefix="sample")

    assert (tmp_path / "sample_equity_curve.png").exists()
    assert (tmp_path / "sample_drawdown.png").exists()
    assert (tmp_path / "sample_profit_distribution.png").exists()
    assert (tmp_path / "sample_monthly_returns.png").exists()


def test_empty_trades_are_handled_gracefully(capsys):
    v = BacktestVisualizer([])
    v.plot_equity_curve()
    v.plot_drawdown()
    v.plot_profit_distribution()
    v.plot_monthly_returns()
    v.plot_parameter_heatmap([], "a", "b")
    out = capsys.readouterr().out
    assert "取引記録がありません" in out
    assert "結果データがありません" in out
