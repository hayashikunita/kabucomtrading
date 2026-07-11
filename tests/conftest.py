"""共有テストフィクスチャ。"""

from datetime import datetime, timedelta

import pytest


class Candle:
    """テスト用の軽量ローソク足。"""

    def __init__(self, time, open_, high, low, close, volume=1000):
        self.time = time
        self.open = open_
        self.high = high
        self.low = low
        self.close = close
        self.volume = volume


def make_candles(closes, start=None):
    """終値リストからローソク足リストを生成する。"""
    start = start or datetime(2024, 1, 1)
    candles = []
    for i, close in enumerate(closes):
        t = start + timedelta(days=i)
        candles.append(Candle(time=t, open_=close, high=close + 1, low=close - 1, close=close))
    return candles


@pytest.fixture
def uptrend_candles():
    """EMAクロスが発生するV字（下降→上昇）系列。"""
    closes = [100 - i for i in range(30)] + [70 + i * 2 for i in range(30)]
    return make_candles(closes)
