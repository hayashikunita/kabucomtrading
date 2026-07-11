import json
from datetime import datetime, timedelta

from app.backtest.trade_logger import TradeLogger


def test_open_and_close_buy_position_records_trade():
    logger = TradeLogger()
    t0 = datetime(2024, 1, 1, 9, 0, 0)
    t1 = t0 + timedelta(hours=2)

    logger.open_position(t0, price=100.0, side="BUY", quantity=2, strategy="ema", indicator_values={"ema": 1.2})
    logger.close_position(t1, price=110.0, indicator_values={"ema": 1.5})

    trades = logger.get_trades()
    assert len(trades) == 1
    trade = trades[0]
    assert trade["profit"] == 20.0
    assert trade["profit_percent"] == 10.0
    assert trade["duration"] == 2.0
    assert trade["strategy"] == "ema"
    assert trade["indicator_values_entry"] == {"ema": 1.2}
    assert trade["indicator_values_exit"] == {"ema": 1.5}


def test_close_without_open_is_noop():
    logger = TradeLogger()
    logger.close_position(datetime(2024, 1, 1), price=100.0)
    assert logger.get_trades() == []


def test_sell_side_profit_and_override():
    logger = TradeLogger()
    t0 = datetime(2024, 1, 1, 9, 0, 0)
    t1 = t0 + timedelta(hours=1)

    logger.open_position(t0, price=120.0, side="SELL", quantity=1)
    logger.close_position(t1, price=100.0, profit_override=7.5, extra_fields={"memo": "forced"})

    trade = logger.get_trades()[0]
    assert trade["profit"] == 7.5
    assert trade["memo"] == "forced"


def test_summary_and_clear():
    logger = TradeLogger()
    t0 = datetime(2024, 1, 1, 9, 0, 0)

    logger.open_position(t0, 100.0, "BUY")
    logger.close_position(t0 + timedelta(hours=1), 110.0)
    logger.open_position(t0 + timedelta(hours=2), 100.0, "BUY")
    logger.close_position(t0 + timedelta(hours=3), 90.0)

    stats = logger.get_summary_stats()
    assert stats["total_trades"] == 2
    assert stats["winning_trades"] == 1
    assert stats["losing_trades"] == 1
    assert stats["total_profit"] == 0.0

    logger.clear()
    assert logger.get_trades() == []
    assert logger.current_position is None


def test_save_to_csv_and_json(tmp_path):
    logger = TradeLogger()
    t0 = datetime(2024, 1, 1, 9, 0, 0)
    logger.open_position(t0, 100.0, "BUY", indicator_values={"k": 1})
    logger.close_position(t0 + timedelta(hours=1), 105.0, indicator_values={"k": 2})

    csv_path = tmp_path / "trades.csv"
    json_path = tmp_path / "trades.json"
    logger.save_to_csv(str(csv_path))
    logger.save_to_json(str(json_path))

    assert csv_path.exists()
    assert json_path.exists()

    content = json.loads(json_path.read_text(encoding="utf-8"))
    assert content[0]["entry_time"].startswith("2024-01-01T09:00:00")
    assert content[0]["indicator_values_entry"] == {"k": 1}


def test_print_summary_empty_and_non_empty(capsys):
    logger = TradeLogger()
    logger.print_summary()
    assert "取引記録がありません" in capsys.readouterr().out

    t0 = datetime(2024, 1, 1, 9, 0, 0)
    logger.open_position(t0, 100.0, "BUY")
    logger.close_position(t0 + timedelta(hours=1), 102.0)
    logger.print_summary()
    out = capsys.readouterr().out
    assert "取引ログサマリー" in out
    assert "総取引数" in out
