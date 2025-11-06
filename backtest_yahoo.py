"""
Yahoo Financeから取得したデータでバックテストを実行するスクリプト
"""
import json
import logging
import sys
from datetime import datetime

from app.data.yahoo import fetch_yahoo_data
from app.models.dfcandle import DataFrameCandle
import settings

logging.basicConfig(level=logging.INFO, stream=sys.stdout)
logger = logging.getLogger(__name__)


class YahooBacktest:
    """Yahoo Financeデータを使ったバックテスト実行クラス"""
    
    def __init__(self, product_code, period_days, duration):
        self.product_code = product_code
        self.period_days = period_days
        self.duration = duration
        self.results = {}
    
    def fetch_data(self):
        """Yahoo Financeからデータ取得"""
        logger.info(f'action=fetch_data product_code={self.product_code} period_days={self.period_days} duration={self.duration}')
        
        candles = fetch_yahoo_data(
            product_code=self.product_code,
            period_days=self.period_days,
            duration=self.duration,
            market='T'  # 東証
        )
        
        if not candles:
            logger.error('action=fetch_data error=no_data_fetched')
            return []
        
        logger.info(f'action=fetch_data success=true count={len(candles)}')
        return candles
    
    def run_backtest(self):
        """バックテストを実行"""
        logger.info('action=run_backtest status=start')
        
        # データ取得
        yahoo_candles = self.fetch_data()
        if not yahoo_candles:
            logger.error('action=run_backtest error=no_data')
            return
        
        # DataFrameCandleオブジェクトを作成
        df = DataFrameCandle(self.product_code, self.duration)
        
        # Yahoo Financeのデータを手動でローソク足リストに変換
        # （既存のcandle.pyのクラスと互換性を持たせる）
        class SimpleCandle:
            def __init__(self, candle_data):
                self.time = candle_data.time
                self.open = candle_data.open
                self.high = candle_data.high
                self.low = candle_data.low
                self.close = candle_data.close
                self.volume = candle_data.volume
            
            @property
            def value(self):
                return {
                    'time': self.time,
                    'open': self.open,
                    'high': self.high,
                    'low': self.low,
                    'close': self.close,
                    'volume': self.volume,
                }
        
        # ローソク足リストを設定
        df.candles = [SimpleCandle(c) for c in yahoo_candles]
        
        logger.info(f'action=run_backtest candles_loaded={len(df.candles)}')
        
        # パラメータ最適化
        logger.info('action=optimize_params status=start')
        optimized_params = df.optimize_params()
        
        if optimized_params is None:
            logger.warning('action=optimize_params result=no_profitable_params')
            self.results['optimized_params'] = None
        else:
            logger.info(f'action=optimize_params success=true')
            self.results['optimized_params'] = optimized_params.__dict__
        
        # 各テクニカル指標のバックテスト結果
        logger.info('action=backtest_indicators status=start')
        
        # EMAバックテスト
        ema_performance, ema_p1, ema_p2 = df.optimize_ema()
        self.results['ema'] = {
            'performance': ema_performance,
            'period_1': ema_p1,
            'period_2': ema_p2
        }
        logger.info(f'EMA: performance={ema_performance}, period_1={ema_p1}, period_2={ema_p2}')
        
        # Bollinger Bandsバックテスト
        bb_performance, bb_n, bb_k = df.optimize_bb()
        self.results['bollinger_bands'] = {
            'performance': bb_performance,
            'n': bb_n,
            'k': bb_k
        }
        logger.info(f'Bollinger Bands: performance={bb_performance}, n={bb_n}, k={bb_k}')
        
        # Ichimokuバックテスト
        ichimoku_performance = df.optimize_ichimoku()
        self.results['ichimoku'] = {
            'performance': ichimoku_performance
        }
        logger.info(f'Ichimoku: performance={ichimoku_performance}')
        
        # RSIバックテスト
        rsi_performance, rsi_period, rsi_buy, rsi_sell = df.optimize_rsi()
        self.results['rsi'] = {
            'performance': rsi_performance,
            'period': rsi_period,
            'buy_thread': rsi_buy,
            'sell_thread': rsi_sell
        }
        logger.info(f'RSI: performance={rsi_performance}, period={rsi_period}, buy={rsi_buy}, sell={rsi_sell}')
        
        # MACDバックテスト
        macd_performance, macd_fast, macd_slow, macd_signal = df.optimize_macd()
        self.results['macd'] = {
            'performance': macd_performance,
            'fast_period': macd_fast,
            'slow_period': macd_slow,
            'signal_period': macd_signal
        }
        logger.info(f'MACD: performance={macd_performance}, fast={macd_fast}, slow={macd_slow}, signal={macd_signal}')
        
        logger.info('action=run_backtest status=complete')
    
    def save_results(self, filename='backtest_results.json'):
        """結果をJSONファイルに保存"""
        output = {
            'product_code': self.product_code,
            'period_days': self.period_days,
            'duration': self.duration,
            'timestamp': datetime.now().isoformat(),
            'results': self.results
        }
        
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(output, f, indent=2, ensure_ascii=False)
        
        logger.info(f'action=save_results file={filename}')
    
    def print_summary(self):
        """結果サマリーを表示"""
        print('\n' + '='*60)
        print('バックテスト結果サマリー')
        print('='*60)
        print(f'銘柄コード: {self.product_code}')
        print(f'期間: {self.period_days}日')
        print(f'時間軸: {self.duration}')
        print('-'*60)
        
        if 'ema' in self.results:
            print(f"\nEMA:")
            print(f"  パフォーマンス: {self.results['ema']['performance']:.2f}")
            print(f"  期間1: {self.results['ema']['period_1']}")
            print(f"  期間2: {self.results['ema']['period_2']}")
        
        if 'bollinger_bands' in self.results:
            print(f"\nBollinger Bands:")
            print(f"  パフォーマンス: {self.results['bollinger_bands']['performance']:.2f}")
            print(f"  N: {self.results['bollinger_bands']['n']}")
            print(f"  K: {self.results['bollinger_bands']['k']:.2f}")
        
        if 'ichimoku' in self.results:
            print(f"\nIchimoku Cloud:")
            print(f"  パフォーマンス: {self.results['ichimoku']['performance']:.2f}")
        
        if 'rsi' in self.results:
            print(f"\nRSI:")
            print(f"  パフォーマンス: {self.results['rsi']['performance']:.2f}")
            print(f"  期間: {self.results['rsi']['period']}")
            print(f"  買いスレッド: {self.results['rsi']['buy_thread']:.2f}")
            print(f"  売りスレッド: {self.results['rsi']['sell_thread']:.2f}")
        
        if 'macd' in self.results:
            print(f"\nMACD:")
            print(f"  パフォーマンス: {self.results['macd']['performance']:.2f}")
            print(f"  Fast期間: {self.results['macd']['fast_period']}")
            print(f"  Slow期間: {self.results['macd']['slow_period']}")
            print(f"  Signal期間: {self.results['macd']['signal_period']}")
        
        print('\n' + '='*60)
        
        if self.results.get('optimized_params'):
            print('\n最適化されたパラメータ:')
            print('-'*60)
            params = self.results['optimized_params']
            for key, value in params.items():
                print(f"  {key}: {value}")
            print('='*60)


def main():
    """メイン実行関数"""
    # settings.iniから設定を取得
    product_code = settings.product_code
    period_days = settings.past_period
    duration = settings.trade_duration
    
    print(f'\nYahoo Finance バックテスト開始')
    print(f'銘柄コード: {product_code}')
    print(f'期間: {period_days}日')
    print(f'時間軸: {duration}\n')
    
    # バックテスト実行
    backtest = YahooBacktest(product_code, period_days, duration)
    backtest.run_backtest()
    
    # 結果表示
    backtest.print_summary()
    
    # 結果保存
    backtest.save_results('backtest_results.json')
    
    print('\nバックテスト完了！結果は backtest_results.json に保存されました。')


if __name__ == "__main__":
    main()
