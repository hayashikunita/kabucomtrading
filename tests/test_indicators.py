"""テクニカル指標のテスト。"""

import numpy as np

from app.strategy import indicators


def test_sma_constant_series():
    values = [5.0] * 10
    result = indicators.sma(values, period=3)
    # 期間到達後は定数と一致
    assert np.isclose(result[-1], 5.0)
    # 先頭は計算不能でNaN
    assert np.isnan(result[0])


def test_ema_matches_length():
    values = list(range(1, 21))
    result = indicators.ema(values, period=5)
    assert len(result) == len(values)


def test_rsi_bounds():
    values = list(range(1, 40))
    result = indicators.rsi(values, period=14)
    finite = result[~np.isnan(result)]
    assert np.all(finite >= 0)
    assert np.all(finite <= 100)


def test_crossover_detects_upward_cross():
    a = [1.0, 1.0, 3.0]
    b = [2.0, 2.0, 2.0]
    # index=2 で a が b を上抜け
    assert indicators.crossover(a, b, index=2) is True
    assert indicators.crossover(a, b, index=1) is False


def test_crossunder_detects_downward_cross():
    a = [3.0, 3.0, 1.0]
    b = [2.0, 2.0, 2.0]
    assert indicators.crossunder(a, b, index=2) is True


def test_crossover_handles_nan():
    a = [np.nan, np.nan, 3.0]
    b = [2.0, 2.0, 2.0]
    # 直前がNaNならクロス扱いにしない
    assert indicators.crossover(a, b, index=2) is False


def test_crossover_first_index_is_false():
    assert indicators.crossover([1.0], [0.0], index=0) is False
