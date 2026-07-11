"""TA-Lib 導入確認テスト。"""

import numpy as np
import talib


def test_talib_import_and_version():
    """TA-Lib が import でき、バージョン情報を持つことを確認。"""
    assert hasattr(talib, "__version__")
    assert isinstance(talib.__version__, str)
    assert len(talib.__version__) > 0


def test_talib_sma_smoke():
    """SMA が最小限の入力で計算できることを確認。"""
    src = np.asarray([1, 2, 3, 4, 5, 6, 7, 8, 9, 10], dtype=float)
    out = talib.SMA(src, timeperiod=3)

    assert len(out) == len(src)
    assert np.isnan(out[0])
    assert np.isnan(out[1])
    assert np.isclose(out[-1], 9.0)
