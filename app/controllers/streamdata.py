from functools import partial
import logging
from threading import Lock
from threading import Thread

from app.controllers.ai import AI
from app.models.candle import create_candle_with_duration
from kabucom.kabucom import Ticker  # kabusapi用に変更

import constants
import settings

logger = logging.getLogger(__name__)


class StreamData(object):

    def __init__(self):
        self.ai = AI(
            product_code=settings.product_code,
            use_percent=settings.use_percent,
            duration=settings.trade_duration,
            past_period=settings.past_period,
            stop_limit_percent=settings.stop_limit_percent,
            back_test=settings.back_test)
        self.trade_lock = Lock()

    def stream_ingestion_data(self):
        """
        ストリーミングデータの取り込み
        バックテストモードの場合は何もしない
        """
        if settings.back_test:
            logger.info('action=stream_ingestion_data status=skipped reason=back_test_mode')
            return
        
        # リアルタイムモードの場合
        logger.warning('action=stream_ingestion_data status=not_implemented')
        logger.warning('リアルタイムティッカー取得機能は未実装です。バックテストモードをご利用ください。')
        # TODO: kabusapiのWebSocket APIを使ってリアルタイムティッカーを取得する実装
        # trade_with_ai = partial(self.trade, ai=self.ai)
        # self.ai.API.get_realtime_ticker(callback=trade_with_ai)

    def trade(self, ticker: Ticker, ai: AI):
        logger.info(f'action=trade ticker={ticker.__dict__}')
        for duration in constants.DURATIONS:
            is_created = create_candle_with_duration(ticker.product_code, duration, ticker)
            if is_created and duration == settings.trade_duration:
                thread = Thread(target=self._trade, args=(ai,))
                thread.start()

    def _trade(self, ai: AI):
        with self.trade_lock:
            ai.trade()

# singleton
stream = StreamData()