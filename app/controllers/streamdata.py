import logging
from functools import partial
from threading import Lock, Thread
import time

import constants
import settings
from app.controllers.ai import AI
from app.models.candle import create_candle_with_duration
from kabucom.kabucom import Ticker  # kabusapi用に変更

logger = logging.getLogger(__name__)


class StreamData(object):
    def __init__(self):
        self.ai = AI(
            product_code=settings.product_code,
            use_percent=settings.use_percent,
            duration=settings.trade_duration,
            past_period=settings.past_period,
            stop_limit_percent=settings.stop_limit_percent,
            back_test=settings.back_test,
        )
        self.trade_lock = Lock()

    def stream_ingestion_data(self):
        """
        ストリーミングデータの取り込み
        バックテストモードの場合は何もしない
        """
        if settings.back_test:
            logger.info("action=stream_ingestion_data status=skipped reason=back_test_mode")
            return

        trade_with_ai = partial(self.trade, ai=self.ai)
        product_code = settings.product_code
        poll_interval_sec = 1.0
        max_backoff_sec = 30.0
        retry_count = 0

        logger.info("action=stream_ingestion_data status=start mode=polling")
        while True:
            try:
                ticker = self.ai.API.get_ticker(product_code)

                # 既存ロジックで product_code を参照するため補完する
                if not hasattr(ticker, "product_code"):
                    setattr(ticker, "product_code", product_code)

                trade_with_ai(ticker)
                retry_count = 0
                time.sleep(poll_interval_sec)

            except Exception as e:
                retry_count += 1
                backoff_sec = min(max_backoff_sec, 2 ** min(retry_count, 5))
                logger.error(
                    f"action=stream_ingestion_data status=retry retry_count={retry_count} backoff_sec={backoff_sec} error={e!s}"
                )
                time.sleep(backoff_sec)

    def trade(self, ticker: Ticker, ai: AI):
        logger.info(f"action=trade ticker={ticker.__dict__}")
        product_code = getattr(ticker, "product_code", getattr(ticker, "symbol", settings.product_code))
        for duration in constants.DURATIONS:
            if ticker.truncate_date_time(duration) is None:
                continue

            is_created = create_candle_with_duration(product_code, duration, ticker)
            if is_created and duration == settings.trade_duration:
                thread = Thread(target=self._trade, args=(ai,))
                thread.start()

    def _trade(self, ai: AI):
        with self.trade_lock:
            ai.trade()


# singleton
stream = StreamData()
