import logging
from datetime import datetime, timedelta
from typing import List, Optional

import pandas as pd
import yfinance as yf

from app.models.candle import factory_candle_class

logger = logging.getLogger(__name__)


class YahooFinanceCandle:
    """Yahoo Financeから取得したローソク足データを表すクラス"""

    def __init__(self, time, open, high, low, close, volume):
        self.time = time
        self.open = open
        self.high = high
        self.low = low
        self.close = close
        self.volume = volume

    @property
    def value(self):
        return {
            "time": self.time,
            "open": self.open,
            "high": self.high,
            "low": self.low,
            "close": self.close,
            "volume": self.volume,
        }


class YahooFinanceClient:
    """Yahoo Financeからデータを取得するクライアントクラス"""

    @staticmethod
    def get_historical_data(ticker: str, period_days: int = 365, interval: str = "1d") -> List[YahooFinanceCandle]:
        """
        Yahoo Financeから過去データを取得

        Args:
            ticker: ティッカーシンボル(例: '1459.T' for 日本市場)
            period_days: 取得する過去日数(デフォルト: 365日)
            interval: データ間隔
                - '1m': 1分足(最大7日間)
                - '5m': 5分足(最大60日間)
                - '15m': 15分足
                - '30m': 30分足
                - '1h': 1時間足
                - '1d': 日足(デフォルト)
                - '1wk': 週足
                - '1mo': 月足

        Returns:
            YahooFinanceCandle のリスト
        """
        logger.info(f"action=get_historical_data ticker={ticker} period_days={period_days} interval={interval}")

        try:
            # Yahoo Financeのティッカーオブジェクトを作成
            stock = yf.Ticker(ticker)

            # 終了日は今日、開始日はperiod_days日前
            end_date = datetime.now()
            start_date = end_date - timedelta(days=period_days)

            # データ取得の制限に対応
            if interval == "1m" and period_days > 7:
                logger.warning(f"action=get_historical_data warning=1m_interval_max_7days adjusting_to_7days")
                start_date = end_date - timedelta(days=7)
            elif interval == "5m" and period_days > 60:
                logger.warning(f"action=get_historical_data warning=5m_interval_max_60days adjusting_to_60days")
                start_date = end_date - timedelta(days=60)

            # データ取得
            df = stock.history(
                start=start_date.strftime("%Y-%m-%d"), end=end_date.strftime("%Y-%m-%d"), interval=interval
            )

            if df.empty:
                logger.error(f"action=get_historical_data error=no_data_returned ticker={ticker}")
                return []

            # YahooFinanceCandleのリストに変換
            candles = []
            for index, row in df.iterrows():
                candle = YahooFinanceCandle(
                    time=index.to_pydatetime(),
                    open=float(row["Open"]),
                    high=float(row["High"]),
                    low=float(row["Low"]),
                    close=float(row["Close"]),
                    volume=int(row["Volume"]),
                )
                candles.append(candle)

            logger.info(f"action=get_historical_data success=true count={len(candles)}")
            return candles

        except Exception as e:
            logger.error(f"action=get_historical_data error={e!s} ticker={ticker}")
            return []

    @staticmethod
    def ticker_from_product_code(product_code: str, market: str = "T") -> str:
        """
        日本の銘柄コードからYahoo Financeのティッカーシンボルに変換

        Args:
            product_code: 銘柄コード(例: '1459')
            market: 市場コード(デフォルト: 'T' = 東証)

        Returns:
            Yahoo Financeティッカー(例: '1459.T')
        """
        return f"{product_code}.{market}"

    @staticmethod
    def convert_duration_to_interval(duration: str) -> str:
        """
        アプリの時間軸をYahoo Financeのintervalに変換

        Args:
            duration: アプリの時間軸('5s', '1m', '1h', '1d')

        Returns:
            Yahoo Financeのinterval文字列
        """
        mapping = {
            "5s": "1m",  # 5秒足はYahooにないため1分足で代用
            "1m": "1m",
            "1h": "1h",
            "1d": "1d",  # 日足
        }
        return mapping.get(duration, "1d")


def fetch_yahoo_data(
    product_code: str, period_days: int = 365, duration: str = "1d", market: str = "T"
) -> List[YahooFinanceCandle]:
    """
    Yahoo Financeからデータを取得する便利関数

    Args:
        product_code: 銘柄コード(例: '1459')
        period_days: 取得する過去日数
        duration: 時間軸('5s', '1m', '1h'など)
        market: 市場コード(デフォルト: 'T' = 東証)

    Returns:
        YahooFinanceCandleのリスト
    """
    client = YahooFinanceClient()
    ticker = client.ticker_from_product_code(product_code, market)
    interval = client.convert_duration_to_interval(duration)
    return client.get_historical_data(ticker, period_days, interval)


def save_yahoo_data_to_db(product_code: str, period_days: int = 365, duration: str = "1d", market: str = "T") -> int:
    """
    Yahoo Financeからデータを取得してデータベースに保存

    Args:
        product_code: 銘柄コード(例: '1459')
        period_days: 取得する過去日数
        duration: 時間軸('5s', '1m', '1h'など)
        market: 市場コード(デフォルト: 'T' = 東証)

    Returns:
        保存した件数
    """
    logger.info(f"action=save_yahoo_data_to_db product_code={product_code} duration={duration}")

    # Yahoo Financeからデータ取得
    candles = fetch_yahoo_data(product_code, period_days, duration, market)

    if not candles:
        logger.warning("action=save_yahoo_data_to_db warning=no_data")
        return 0

    # データベースに保存
    candle_cls = factory_candle_class(product_code, duration)
    if candle_cls is None:
        logger.error(f"action=save_yahoo_data_to_db error=unknown_duration duration={duration}")
        return 0

    saved_count = 0
    for candle in candles:
        result = candle_cls.create(
            time=candle.time,
            open=candle.open,
            close=candle.close,
            high=candle.high,
            low=candle.low,
            volume=candle.volume,
        )
        if result:
            saved_count += 1

    logger.info(f"action=save_yahoo_data_to_db success=true saved={saved_count}/{len(candles)}")
    return saved_count
