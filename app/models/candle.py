import logging

from sqlalchemy import Column, DateTime, Float, Integer, desc
from sqlalchemy.exc import IntegrityError

import constants
from app.models.base import Base, session_scope

logger = logging.getLogger(__name__)


class BaseCandleMixin(object):
    time = Column(DateTime, primary_key=True, nullable=False)
    open = Column(Float)
    close = Column(Float)
    high = Column(Float)
    low = Column(Float)
    volume = Column(Integer)

    @classmethod
    def create(cls, time, open, close, high, low, volume):
        candle = cls(time=time, open=open, close=close, high=high, low=low, volume=volume)
        try:
            with session_scope() as session:
                session.add(candle)
            return candle
        except IntegrityError:
            return False

    @classmethod
    def get(cls, time):
        with session_scope() as session:
            candle = session.query(cls).filter(cls.time == time).first()
        if candle is None:
            return None
        return candle

    def save(self):
        with session_scope() as session:
            session.add(self)

    @classmethod
    def get_all_candles(cls, limit=100):
        with session_scope() as session:
            candles = session.query(cls).order_by(desc(cls.time)).limit(limit).all()

        if candles is None:
            return None

        candles.reverse()
        return candles

    @property
    def value(self):
        return {
            "time": self.time,
            "open": self.open,
            "close": self.close,
            "high": self.high,
            "low": self.low,
            "volume": self.volume,
        }


# kabusapi用ETFコード（例: 1459）にテーブル名を変更
class KabusBaseCandle1H(BaseCandleMixin, Base):
    __tablename__ = "KABUS_1459_1H"


class KabusBaseCandle1M(BaseCandleMixin, Base):
    __tablename__ = "KABUS_1459_1M"


class KabusBaseCandle5S(BaseCandleMixin, Base):
    __tablename__ = "KABUS_1459_5S"


# 動的にテーブルクラスを作成するキャッシュ
_candle_class_cache = {}


def create_candle_class(product_code, duration):
    """
    任意の銘柄コード・時間足のローソク足テーブルクラスを動的に作成

    Args:
        product_code: 銘柄コード（例: '1459', '1459.T', 'AAPL'）
        duration: 時間足（constants.DURATION_1M等）

    Returns:
        ローソク足テーブルクラス
    """
    # 銘柄コードをテーブル名に使える形式に変換（記号を_に置換）
    safe_code = product_code.replace(".", "_").replace("-", "_").upper()
    duration_suffix = duration.upper()
    cache_key = f"{safe_code}_{duration_suffix}"

    # キャッシュにあればそれを返す
    if cache_key in _candle_class_cache:
        return _candle_class_cache[cache_key]

    # 新規作成
    class_name = f"Candle_{cache_key}"
    table_name = f"CANDLE_{cache_key}"

    new_class = type(class_name, (BaseCandleMixin, Base), {"__tablename__": table_name})

    _candle_class_cache[cache_key] = new_class
    return new_class


def factory_candle_class(product_code, duration):
    # 既存の1459用クラスとの互換性を保つ
    if product_code == constants.PRODUCT_CODE_USD_JPY:
        if duration == constants.DURATION_5S:
            return KabusBaseCandle5S
        if duration == constants.DURATION_1M:
            return KabusBaseCandle1M
        if duration == constants.DURATION_1H:
            return KabusBaseCandle1H

    # 新規銘柄コードは動的にクラスを作成
    return create_candle_class(product_code, duration)


def create_candle_with_duration(product_code, duration, ticker):
    cls = factory_candle_class(product_code, duration)
    ticker_time = ticker.truncate_date_time(duration)
    current_candle = cls.get(ticker_time)
    price = ticker.mid_price
    if current_candle is None:
        cls.create(ticker_time, price, price, price, price, ticker.volume)
        return True

    if current_candle.high <= price:
        current_candle.high = price
    elif current_candle.low >= price:
        current_candle.low = price
    current_candle.volume += ticker.volume
    current_candle.close = price
    current_candle.save()
    return False
