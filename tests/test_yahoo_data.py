from datetime import datetime

import pandas as pd

from app.data import yahoo


class _FixedDateTime:
    @staticmethod
    def now():
        return datetime(2024, 1, 10)


def test_ticker_from_product_code_variants():
    client = yahoo.YahooFinanceClient()
    assert client.ticker_from_product_code(" 1459 ") == "1459.T"
    assert client.ticker_from_product_code("^N225") == "^N225"
    assert client.ticker_from_product_code("7203.T") == "7203.T"
    assert client.ticker_from_product_code("AAPL", market="") == "AAPL"


def test_convert_duration_to_interval_default():
    client = yahoo.YahooFinanceClient()
    assert client.convert_duration_to_interval("5s") == "1m"
    assert client.convert_duration_to_interval("1m") == "1m"
    assert client.convert_duration_to_interval("1h") == "1h"
    assert client.convert_duration_to_interval("1d") == "1d"
    assert client.convert_duration_to_interval("unknown") == "1d"


def test_get_historical_data_builds_candles_and_applies_1m_limit(monkeypatch):
    calls = {}

    class _FakeTicker:
        def history(self, start, end, interval):
            calls["start"] = start
            calls["end"] = end
            calls["interval"] = interval
            idx = pd.to_datetime(["2024-01-08", "2024-01-09"])
            return pd.DataFrame(
                {
                    "Open": [100, 101],
                    "High": [102, 103],
                    "Low": [99, 100],
                    "Close": [101, 102],
                    "Volume": [1000, 1200],
                },
                index=idx,
            )

    monkeypatch.setattr(yahoo, "datetime", _FixedDateTime)
    monkeypatch.setattr(yahoo.yf, "Ticker", lambda _: _FakeTicker())

    candles = yahoo.YahooFinanceClient.get_historical_data("1459.T", period_days=30, interval="1m")

    assert len(candles) == 2
    assert candles[0].value["open"] == 100.0
    assert candles[1].value["close"] == 102.0
    assert calls["interval"] == "1m"
    # 1mは最大7日制限が適用される
    assert calls["start"] == "2024-01-03"
    assert calls["end"] == "2024-01-10"


def test_get_historical_data_returns_empty_on_exception(monkeypatch):
    def _raise(_):
        raise RuntimeError("boom")

    monkeypatch.setattr(yahoo.yf, "Ticker", _raise)
    candles = yahoo.YahooFinanceClient.get_historical_data("1459.T")
    assert candles == []


def test_fetch_yahoo_data_calls_client_methods(monkeypatch):
    called = {}

    class _FakeClient:
        def ticker_from_product_code(self, product_code, market):
            called["ticker"] = (product_code, market)
            return "7203.T"

        def convert_duration_to_interval(self, duration):
            called["duration"] = duration
            return "1d"

        def get_historical_data(self, ticker, period_days, interval):
            called["history"] = (ticker, period_days, interval)
            return ["ok"]

    monkeypatch.setattr(yahoo, "YahooFinanceClient", _FakeClient)

    out = yahoo.fetch_yahoo_data("7203", period_days=365, duration="1d", market="T")
    assert out == ["ok"]
    assert called["ticker"] == ("7203", "T")
    assert called["duration"] == "1d"
    assert called["history"] == ("7203.T", 365, "1d")


def test_save_yahoo_data_to_db_returns_zero_when_no_candles(monkeypatch):
    monkeypatch.setattr(yahoo, "fetch_yahoo_data", lambda *args, **kwargs: [])
    assert yahoo.save_yahoo_data_to_db("1459") == 0


def test_save_yahoo_data_to_db_returns_zero_when_class_not_found(monkeypatch):
    candle = yahoo.YahooFinanceCandle(datetime(2024, 1, 1), 100, 101, 99, 100, 1000)
    monkeypatch.setattr(yahoo, "fetch_yahoo_data", lambda *args, **kwargs: [candle])
    monkeypatch.setattr(yahoo, "factory_candle_class", lambda *args, **kwargs: None)
    assert yahoo.save_yahoo_data_to_db("1459", duration="unknown") == 0


def test_save_yahoo_data_to_db_counts_only_success(monkeypatch):
    candles = [
        yahoo.YahooFinanceCandle(datetime(2024, 1, 1), 100, 101, 99, 100, 1000),
        yahoo.YahooFinanceCandle(datetime(2024, 1, 2), 101, 102, 100, 101, 1200),
    ]
    monkeypatch.setattr(yahoo, "fetch_yahoo_data", lambda *args, **kwargs: candles)

    class _FakeCandleCls:
        calls = 0

        @classmethod
        def create(cls, **kwargs):
            cls.calls += 1
            return cls.calls == 1

    monkeypatch.setattr(yahoo, "factory_candle_class", lambda *args, **kwargs: _FakeCandleCls)

    saved = yahoo.save_yahoo_data_to_db("1459", duration="1d")
    assert saved == 1
