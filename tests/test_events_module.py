from datetime import datetime, timedelta

import constants
from app.models.events import SignalEvent, SignalEvents


def test_signal_event_value_omits_none_fields():
    evt = SignalEvent(time=datetime(2024, 1, 1), product_code="1459", side=constants.BUY, price=None, units=None)
    value = evt.value
    assert "time" in value
    assert "product_code" in value
    assert "side" in value
    assert "price" not in value
    assert "units" not in value


def test_signal_events_buy_sell_sequence_without_save():
    s = SignalEvents()
    t0 = datetime(2024, 1, 1, 9, 0, 0)
    t1 = t0 + timedelta(hours=1)

    assert s.can_buy(t0) is True
    assert s.buy("1459", t0, 100.0, 1, save=False) is True
    assert s.can_buy(t1) is False
    assert s.sell("1459", t1, 110.0, 1, save=False) is True
    assert s.can_sell(t1 + timedelta(hours=1)) is False


def test_signal_events_save_flag_calls_signal_event_save(monkeypatch):
    called = {"save": 0}

    def _fake_save(self):
        called["save"] += 1

    monkeypatch.setattr(SignalEvent, "save", _fake_save)

    s = SignalEvents()
    t0 = datetime(2024, 1, 1, 9, 0, 0)
    t1 = t0 + timedelta(hours=1)

    assert s.buy("1459", t0, 100.0, 1, save=True)
    assert s.sell("1459", t1, 105.0, 1, save=True)
    assert called["save"] == 2


def test_profit_returns_last_closed_total_when_still_holding():
    t0 = datetime(2024, 1, 1, 9, 0, 0)
    t1 = t0 + timedelta(hours=1)
    t2 = t1 + timedelta(hours=1)

    s = SignalEvents()
    s.buy("1459", t0, 100.0, 1, save=False)
    s.sell("1459", t1, 120.0, 1, save=False)
    s.buy("1459", t2, 90.0, 1, save=False)

    # 最後が未決済なので、直近の決済確定値(20)を返す
    assert s.profit == 20.0


def test_value_empty_and_non_empty():
    empty = SignalEvents()
    assert empty.value == {"signals": None, "profit": None}

    s = SignalEvents()
    t0 = datetime(2024, 1, 1, 9, 0, 0)
    t1 = t0 + timedelta(hours=1)
    s.buy("1459", t0, 100.0, 1, save=False)
    s.sell("1459", t1, 110.0, 1, save=False)

    value = s.value
    assert isinstance(value["signals"], list)
    assert value["profit"] == 10.0


def test_static_fetch_wrappers(monkeypatch):
    t0 = datetime(2024, 1, 1, 9, 0, 0)
    sample = [SignalEvent(time=t0, product_code="1459", side=constants.BUY, price=100.0, units=1)]

    monkeypatch.setattr(SignalEvent, "get_signal_events_by_count", classmethod(lambda cls, count: sample))
    monkeypatch.setattr(SignalEvent, "get_signal_events_after_time", classmethod(lambda cls, time: sample))

    by_count = SignalEvents.get_signal_events_by_count(10)
    after_time = SignalEvents.get_signal_events_after_time(t0)

    assert isinstance(by_count, SignalEvents)
    assert isinstance(after_time, SignalEvents)
    assert len(by_count.signals) == 1
    assert len(after_time.signals) == 1
