"""
Yahoo Financeから取得したデータでバックテストを実行するスクリプト
全パラメータ組み合わせの詳細な結果を出力
"""

import json
import logging
import sys
from datetime import datetime

import pandas as pd

import settings
from app.data.yahoo import fetch_yahoo_data
from app.models.dfcandle import DataFrameCandle

logging.basicConfig(level=logging.INFO, stream=sys.stdout)
logger = logging.getLogger(__name__)


class YahooBacktest:
    """Yahoo Financeデータを使ったバックテスト実行クラス"""

    def __init__(self, product_code, period_days, duration):
        self.product_code = product_code
        self.period_days = period_days
        self.duration = duration
        self.results = {}
        self.detailed_results = {}  # 全パラメータの詳細結果

    def fetch_data(self):
        """Yahoo Financeからデータ取得"""
        logger.info(
            f"action=fetch_data product_code={self.product_code} period_days={self.period_days} duration={self.duration}"
        )

        candles = fetch_yahoo_data(
            product_code=self.product_code,
            period_days=self.period_days,
            duration=self.duration,
            market="T",  # 東証
        )

        if not candles:
            logger.error("action=fetch_data error=no_data_fetched")
            return []

        logger.info(f"action=fetch_data success=true count={len(candles)}")
        return candles

    def backtest_all_ema_params(self, df):
        """すべてのEMAパラメータ組み合わせをテスト"""
        logger.info("action=backtest_all_ema_params status=start")

        period1_range = range(5, 30, 1)  # 5-29
        period2_range = range(10, 50, 2)  # 10-48

        all_results = []
        best_performance = 0
        best_params = None

        total_combinations = len(list(period1_range)) * len(list(period2_range))
        current = 0

        for period1 in period1_range:
            for period2 in period2_range:
                if period1 >= period2:
                    continue

                current += 1
                if current % 50 == 0:
                    logger.info(f"EMA progress: {current}/{total_combinations}")

                # バックテスト実行
                df.add_ema(period1)
                df.add_ema(period2)
                signal_events = df.back_test_ema(period1, period2)
                performance = signal_events.profit if signal_events and signal_events.profit else 0

                result = {"period1": period1, "period2": period2, "performance": performance}
                all_results.append(result)

                if performance and performance > best_performance:
                    best_performance = performance
                    best_params = (period1, period2)

        logger.info(f"action=backtest_all_ema_params complete total={len(all_results)}")

        return all_results, best_performance, best_params

    def backtest_all_bb_params(self, df):
        """すべてのBollinger Bandsパラメータ組み合わせをテスト"""
        logger.info("action=backtest_all_bb_params status=start")

        n_range = range(10, 50, 5)  # 10, 15, 20, ..., 45
        k_range = [1.0, 1.5, 2.0, 2.5, 3.0]

        all_results = []
        best_performance = 0
        best_params = None

        total_combinations = len(list(n_range)) * len(k_range)
        current = 0

        for n in n_range:
            for k in k_range:
                current += 1
                if current % 10 == 0:
                    logger.info(f"BB progress: {current}/{total_combinations}")

                # バックテスト実行
                df.add_bbands(n, k)
                signal_events = df.back_test_bb(n, k)
                performance = signal_events.profit if signal_events and signal_events.profit else 0

                result = {"n": n, "k": k, "performance": performance}
                all_results.append(result)

                if performance and performance > best_performance:
                    best_performance = performance
                    best_params = (n, k)

        logger.info(f"action=backtest_all_bb_params complete total={len(all_results)}")

        return all_results, best_performance, best_params

    def backtest_all_rsi_params(self, df):
        """すべてのRSIパラメータ組み合わせをテスト"""
        logger.info("action=backtest_all_rsi_params status=start")

        period_range = range(7, 30, 1)  # 7-29
        buy_threshold_range = range(20, 40, 5)  # 20, 25, 30, 35
        sell_threshold_range = range(60, 85, 5)  # 60, 65, 70, 75, 80

        all_results = []
        best_performance = 0
        best_params = None

        total_combinations = len(list(period_range)) * len(list(buy_threshold_range)) * len(list(sell_threshold_range))
        current = 0

        for period in period_range:
            for buy_threshold in buy_threshold_range:
                for sell_threshold in sell_threshold_range:
                    if buy_threshold >= sell_threshold:
                        continue

                    current += 1
                    if current % 100 == 0:
                        logger.info(f"RSI progress: {current}/{total_combinations}")

                    # バックテスト実行
                    df.add_rsi(period)
                    signal_events = df.back_test_rsi(period, buy_threshold, sell_threshold)
                    performance = signal_events.profit if signal_events and signal_events.profit else 0

                    result = {
                        "period": period,
                        "buy_threshold": buy_threshold,
                        "sell_threshold": sell_threshold,
                        "performance": performance,
                    }
                    all_results.append(result)

                    if performance and performance > best_performance:
                        best_performance = performance
                        best_params = (period, buy_threshold, sell_threshold)

        logger.info(f"action=backtest_all_rsi_params complete total={len(all_results)}")

        return all_results, best_performance, best_params

    def backtest_all_macd_params(self, df):
        """すべてのMACDパラメータ組み合わせをテスト"""
        logger.info("action=backtest_all_macd_params status=start")

        fast_range = range(8, 16, 2)  # 8, 10, 12, 14
        slow_range = range(20, 32, 2)  # 20, 22, 24, 26, 28, 30
        signal_range = range(5, 12, 2)  # 5, 7, 9, 11

        all_results = []
        best_performance = 0
        best_params = None

        total_combinations = len(list(fast_range)) * len(list(slow_range)) * len(list(signal_range))
        current = 0

        for fast in fast_range:
            for slow in slow_range:
                if fast >= slow:
                    continue
                for signal in signal_range:
                    current += 1
                    if current % 20 == 0:
                        logger.info(f"MACD progress: {current}/{total_combinations}")

                    # バックテスト実行
                    df.add_macd(fast, slow, signal)
                    signal_events = df.back_test_macd(fast, slow, signal)
                    performance = signal_events.profit if signal_events and signal_events.profit else 0

                    result = {
                        "fast_period": fast,
                        "slow_period": slow,
                        "signal_period": signal,
                        "performance": performance,
                    }
                    all_results.append(result)

                    if performance and performance > best_performance:
                        best_performance = performance
                        best_params = (fast, slow, signal)

        logger.info(f"action=backtest_all_macd_params complete total={len(all_results)}")

        return all_results, best_performance, best_params

    def run_backtest(self, detailed=True):
        """バックテストを実行"""
        logger.info("action=run_backtest status=start")

        # データ取得
        yahoo_candles = self.fetch_data()
        if not yahoo_candles:
            logger.error("action=run_backtest error=no_data")
            return

        # DataFrameCandleオブジェクトを作成
        df = DataFrameCandle(self.product_code, self.duration)

        # Yahoo Financeのデータを手動でローソク足リストに変換
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
                    "time": self.time,
                    "open": self.open,
                    "high": self.high,
                    "low": self.low,
                    "close": self.close,
                    "volume": self.volume,
                }

        # ローソク足リストを設定
        df.candles = [SimpleCandle(c) for c in yahoo_candles]

        logger.info(f"action=run_backtest candles_loaded={len(df.candles)}")

        if detailed:
            # 全パラメータの詳細バックテスト
            logger.info("action=detailed_backtest status=start")

            # EMA詳細バックテスト
            ema_all, ema_perf, ema_params = self.backtest_all_ema_params(df)
            self.detailed_results["ema"] = {
                "all_results": ema_all,
                "best_performance": ema_perf,
                "best_params": {
                    "period1": ema_params[0] if ema_params else None,
                    "period2": ema_params[1] if ema_params else None,
                },
            }

            # Bollinger Bands詳細バックテスト
            bb_all, bb_perf, bb_params = self.backtest_all_bb_params(df)
            self.detailed_results["bollinger_bands"] = {
                "all_results": bb_all,
                "best_performance": bb_perf,
                "best_params": {"n": bb_params[0] if bb_params else None, "k": bb_params[1] if bb_params else None},
            }

            # RSI詳細バックテスト
            rsi_all, rsi_perf, rsi_params = self.backtest_all_rsi_params(df)
            self.detailed_results["rsi"] = {
                "all_results": rsi_all,
                "best_performance": rsi_perf,
                "best_params": {
                    "period": rsi_params[0] if rsi_params else None,
                    "buy_threshold": rsi_params[1] if rsi_params else None,
                    "sell_threshold": rsi_params[2] if rsi_params else None,
                },
            }

            # MACD詳細バックテスト
            macd_all, macd_perf, macd_params = self.backtest_all_macd_params(df)
            self.detailed_results["macd"] = {
                "all_results": macd_all,
                "best_performance": macd_perf,
                "best_params": {
                    "fast_period": macd_params[0] if macd_params else None,
                    "slow_period": macd_params[1] if macd_params else None,
                    "signal_period": macd_params[2] if macd_params else None,
                },
            }

            # Ichimokuバックテスト（パラメータ固定）
            df.add_ichimoku()
            signal_events = df.back_test_ichimoku()
            ichimoku_performance = signal_events.profit if signal_events and signal_events.profit else 0
            self.detailed_results["ichimoku"] = {"performance": ichimoku_performance}

            # 簡易結果も保存
            self.results = {
                "ema": self.detailed_results["ema"]["best_params"] if "ema" in self.detailed_results else {},
                "bollinger_bands": self.detailed_results["bollinger_bands"]["best_params"]
                if "bollinger_bands" in self.detailed_results
                else {},
                "rsi": self.detailed_results["rsi"]["best_params"] if "rsi" in self.detailed_results else {},
                "macd": self.detailed_results["macd"]["best_params"] if "macd" in self.detailed_results else {},
                "ichimoku": {"performance": ichimoku_performance},
            }

            # パフォーマンスを追加
            for key in ["ema", "bollinger_bands", "rsi", "macd"]:
                if key in self.detailed_results:
                    self.results[key]["performance"] = self.detailed_results[key]["best_performance"]

        else:
            # 従来の最適化（高速版）
            logger.info("action=optimize_params status=start")
            optimized_params = df.optimize_params()

            if optimized_params is None:
                logger.warning("action=optimize_params result=no_profitable_params")
                self.results["optimized_params"] = None
            else:
                logger.info(f"action=optimize_params success=true")
                self.results["optimized_params"] = optimized_params.__dict__

            # 各テクニカル指標のバックテスト結果
            ema_performance, ema_p1, ema_p2 = df.optimize_ema()
            self.results["ema"] = {"performance": ema_performance, "period_1": ema_p1, "period_2": ema_p2}

            bb_performance, bb_n, bb_k = df.optimize_bb()
            self.results["bollinger_bands"] = {"performance": bb_performance, "n": bb_n, "k": bb_k}

            ichimoku_performance = df.optimize_ichimoku()
            self.results["ichimoku"] = {"performance": ichimoku_performance}

            rsi_performance, rsi_period, rsi_buy, rsi_sell = df.optimize_rsi()
            self.results["rsi"] = {
                "performance": rsi_performance,
                "period": rsi_period,
                "buy_thread": rsi_buy,
                "sell_thread": rsi_sell,
            }

            macd_performance, macd_fast, macd_slow, macd_signal = df.optimize_macd()
            self.results["macd"] = {
                "performance": macd_performance,
                "fast_period": macd_fast,
                "slow_period": macd_slow,
                "signal_period": macd_signal,
            }

        logger.info("action=run_backtest status=complete")

    def save_results(self, filename="backtest_results.json"):
        """結果をJSONファイルに保存"""
        output = {
            "product_code": self.product_code,
            "period_days": self.period_days,
            "duration": self.duration,
            "timestamp": datetime.now().isoformat(),
            "results": self.results,
            "detailed_results": self.detailed_results if self.detailed_results else None,
        }

        with open(filename, "w", encoding="utf-8") as f:
            json.dump(output, f, indent=2, ensure_ascii=False)

        logger.info(f"action=save_results file={filename}")

    def save_detailed_csv(self, output_dir="backtest_details"):
        """詳細結果をCSVファイルに保存"""
        import os

        os.makedirs(output_dir, exist_ok=True)

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        for indicator, data in self.detailed_results.items():
            if "all_results" in data:
                df = pd.DataFrame(data["all_results"])
                df = df.sort_values("performance", ascending=False)

                filename = f"{output_dir}/{self.product_code}_{indicator}_{timestamp}.csv"
                df.to_csv(filename, index=False, encoding="utf-8-sig")
                logger.info(f"action=save_detailed_csv indicator={indicator} file={filename} rows={len(df)}")

    def print_summary(self):
        """結果サマリーを表示"""
        print("\n" + "=" * 60)
        print("バックテスト結果サマリー")
        print("=" * 60)
        print(f"銘柄コード: {self.product_code}")
        print(f"期間: {self.period_days}日")
        print(f"時間軸: {self.duration}")
        print("-" * 60)

        if "ema" in self.results:
            print(f"\nEMA:")
            print(f"  パフォーマンス: {self.results['ema'].get('performance', 0):.2f}")
            if "period1" in self.results["ema"] and self.results["ema"]["period1"] is not None:
                print(f"  期間1: {self.results['ema']['period1']}")
                print(f"  期間2: {self.results['ema']['period2']}")
            if "ema" in self.detailed_results:
                print(f"  テスト済み組み合わせ数: {len(self.detailed_results['ema']['all_results'])}")

        if "bollinger_bands" in self.results:
            print(f"\nBollinger Bands:")
            print(f"  パフォーマンス: {self.results['bollinger_bands'].get('performance', 0):.2f}")
            if "n" in self.results["bollinger_bands"] and self.results["bollinger_bands"]["n"] is not None:
                print(f"  N: {self.results['bollinger_bands']['n']}")
                print(f"  K: {self.results['bollinger_bands']['k']:.2f}")
            if "bollinger_bands" in self.detailed_results:
                print(f"  テスト済み組み合わせ数: {len(self.detailed_results['bollinger_bands']['all_results'])}")

        if "ichimoku" in self.results:
            print(f"\nIchimoku Cloud:")
            print(f"  パフォーマンス: {self.results['ichimoku'].get('performance', 0):.2f}")

        if "rsi" in self.results:
            print(f"\nRSI:")
            print(f"  パフォーマンス: {self.results['rsi'].get('performance', 0):.2f}")
            if "period" in self.results["rsi"] and self.results["rsi"]["period"] is not None:
                print(f"  期間: {self.results['rsi']['period']}")
                buy_th = self.results["rsi"].get("buy_threshold", self.results["rsi"].get("buy_thread", 0))
                sell_th = self.results["rsi"].get("sell_threshold", self.results["rsi"].get("sell_thread", 0))
                if buy_th is not None and sell_th is not None:
                    print(f"  買いスレッド: {buy_th:.2f}")
                    print(f"  売りスレッド: {sell_th:.2f}")
            if "rsi" in self.detailed_results:
                print(f"  テスト済み組み合わせ数: {len(self.detailed_results['rsi']['all_results'])}")

        if "macd" in self.results:
            print(f"\nMACD:")
            print(f"  パフォーマンス: {self.results['macd'].get('performance', 0):.2f}")
            if "fast_period" in self.results["macd"] and self.results["macd"]["fast_period"] is not None:
                print(f"  Fast期間: {self.results['macd']['fast_period']}")
                print(f"  Slow期間: {self.results['macd']['slow_period']}")
                print(f"  Signal期間: {self.results['macd']['signal_period']}")
            if "macd" in self.detailed_results:
                print(f"  テスト済み組み合わせ数: {len(self.detailed_results['macd']['all_results'])}")

        print("\n" + "=" * 60)


def main():
    """メイン実行関数"""
    import argparse

    parser = argparse.ArgumentParser(description="Yahoo Finance バックテスト")
    parser.add_argument("--detailed", action="store_true", help="全パラメータの詳細バックテストを実行")
    parser.add_argument("--product-code", type=str, default=settings.product_code, help="銘柄コード")
    parser.add_argument("--period", type=int, default=settings.past_period, help="期間（日数）")
    parser.add_argument("--duration", type=str, default=settings.trade_duration, help="時間軸")

    args = parser.parse_args()

    print(f"\nYahoo Finance バックテスト開始")
    print(f"銘柄コード: {args.product_code}")
    print(f"期間: {args.period}日")
    print(f"時間軸: {args.duration}")
    print(f'詳細モード: {"有効" if args.detailed else "無効"}')
    print()

    # バックテスト実行
    backtest = YahooBacktest(args.product_code, args.period, args.duration)
    backtest.run_backtest(detailed=args.detailed)

    # 結果表示
    backtest.print_summary()

    # 結果保存
    backtest.save_results("backtest_results.json")

    if args.detailed:
        backtest.save_detailed_csv()
        print("\n詳細結果は backtest_details/ フォルダに保存されました。")

    print("\nバックテスト完了！結果は backtest_results.json に保存されました。")


if __name__ == "__main__":
    main()

    """Yahoo Financeデータを使ったバックテスト実行クラス"""

    def __init__(self, product_code, period_days, duration):
        self.product_code = product_code
        self.period_days = period_days
        self.duration = duration
        self.results = {}

    def fetch_data(self):
        """Yahoo Financeからデータ取得"""
        logger.info(
            f"action=fetch_data product_code={self.product_code} period_days={self.period_days} duration={self.duration}"
        )

        candles = fetch_yahoo_data(
            product_code=self.product_code,
            period_days=self.period_days,
            duration=self.duration,
            market="T",  # 東証
        )

        if not candles:
            logger.error("action=fetch_data error=no_data_fetched")
            return []

        logger.info(f"action=fetch_data success=true count={len(candles)}")
        return candles

    def run_backtest(self):
        """バックテストを実行"""
        logger.info("action=run_backtest status=start")

        # データ取得
        yahoo_candles = self.fetch_data()
        if not yahoo_candles:
            logger.error("action=run_backtest error=no_data")
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
                    "time": self.time,
                    "open": self.open,
                    "high": self.high,
                    "low": self.low,
                    "close": self.close,
                    "volume": self.volume,
                }

        # ローソク足リストを設定
        df.candles = [SimpleCandle(c) for c in yahoo_candles]

        logger.info(f"action=run_backtest candles_loaded={len(df.candles)}")

        # パラメータ最適化
        logger.info("action=optimize_params status=start")
        optimized_params = df.optimize_params()

        if optimized_params is None:
            logger.warning("action=optimize_params result=no_profitable_params")
            self.results["optimized_params"] = None
        else:
            logger.info(f"action=optimize_params success=true")
            self.results["optimized_params"] = optimized_params.__dict__

        # 各テクニカル指標のバックテスト結果
        logger.info("action=backtest_indicators status=start")

        # EMAバックテスト
        ema_performance, ema_p1, ema_p2 = df.optimize_ema()
        self.results["ema"] = {"performance": ema_performance, "period_1": ema_p1, "period_2": ema_p2}
        logger.info(f"EMA: performance={ema_performance}, period_1={ema_p1}, period_2={ema_p2}")

        # Bollinger Bandsバックテスト
        bb_performance, bb_n, bb_k = df.optimize_bb()
        self.results["bollinger_bands"] = {"performance": bb_performance, "n": bb_n, "k": bb_k}
        logger.info(f"Bollinger Bands: performance={bb_performance}, n={bb_n}, k={bb_k}")

        # Ichimokuバックテスト
        ichimoku_performance = df.optimize_ichimoku()
        self.results["ichimoku"] = {"performance": ichimoku_performance}
        logger.info(f"Ichimoku: performance={ichimoku_performance}")

        # RSIバックテスト
        rsi_performance, rsi_period, rsi_buy, rsi_sell = df.optimize_rsi()
        self.results["rsi"] = {
            "performance": rsi_performance,
            "period": rsi_period,
            "buy_thread": rsi_buy,
            "sell_thread": rsi_sell,
        }
        logger.info(f"RSI: performance={rsi_performance}, period={rsi_period}, buy={rsi_buy}, sell={rsi_sell}")

        # MACDバックテスト
        macd_performance, macd_fast, macd_slow, macd_signal = df.optimize_macd()
        self.results["macd"] = {
            "performance": macd_performance,
            "fast_period": macd_fast,
            "slow_period": macd_slow,
            "signal_period": macd_signal,
        }
        logger.info(f"MACD: performance={macd_performance}, fast={macd_fast}, slow={macd_slow}, signal={macd_signal}")

        logger.info("action=run_backtest status=complete")

    def save_results(self, filename="backtest_results.json"):
        """結果をJSONファイルに保存"""
        output = {
            "product_code": self.product_code,
            "period_days": self.period_days,
            "duration": self.duration,
            "timestamp": datetime.now().isoformat(),
            "results": self.results,
        }

        with open(filename, "w", encoding="utf-8") as f:
            json.dump(output, f, indent=2, ensure_ascii=False)

        logger.info(f"action=save_results file={filename}")

    def print_summary(self):
        """結果サマリーを表示"""
        print("\n" + "=" * 60)
        print("バックテスト結果サマリー")
        print("=" * 60)
        print(f"銘柄コード: {self.product_code}")
        print(f"期間: {self.period_days}日")
        print(f"時間軸: {self.duration}")
        print("-" * 60)

        if "ema" in self.results:
            print(f"\nEMA:")
            print(f"  パフォーマンス: {self.results['ema']['performance']:.2f}")
            print(f"  期間1: {self.results['ema']['period_1']}")
            print(f"  期間2: {self.results['ema']['period_2']}")

        if "bollinger_bands" in self.results:
            print(f"\nBollinger Bands:")
            print(f"  パフォーマンス: {self.results['bollinger_bands']['performance']:.2f}")
            print(f"  N: {self.results['bollinger_bands']['n']}")
            print(f"  K: {self.results['bollinger_bands']['k']:.2f}")

        if "ichimoku" in self.results:
            print(f"\nIchimoku Cloud:")
            print(f"  パフォーマンス: {self.results['ichimoku']['performance']:.2f}")

        if "rsi" in self.results:
            print(f"\nRSI:")
            print(f"  パフォーマンス: {self.results['rsi']['performance']:.2f}")
            print(f"  期間: {self.results['rsi']['period']}")
            print(f"  買いスレッド: {self.results['rsi']['buy_thread']:.2f}")
            print(f"  売りスレッド: {self.results['rsi']['sell_thread']:.2f}")

        if "macd" in self.results:
            print(f"\nMACD:")
            print(f"  パフォーマンス: {self.results['macd']['performance']:.2f}")
            print(f"  Fast期間: {self.results['macd']['fast_period']}")
            print(f"  Slow期間: {self.results['macd']['slow_period']}")
            print(f"  Signal期間: {self.results['macd']['signal_period']}")

        print("\n" + "=" * 60)

        if self.results.get("optimized_params"):
            print("\n最適化されたパラメータ:")
            print("-" * 60)
            params = self.results["optimized_params"]
            for key, value in params.items():
                print(f"  {key}: {value}")
            print("=" * 60)


def main():
    """メイン実行関数"""
    # settings.iniから設定を取得
    product_code = settings.product_code
    period_days = settings.past_period
    duration = settings.trade_duration

    print(f"\nYahoo Finance バックテスト開始")
    print(f"銘柄コード: {product_code}")
    print(f"期間: {period_days}日")
    print(f"時間軸: {duration}\n")

    # バックテスト実行
    backtest = YahooBacktest(product_code, period_days, duration)
    backtest.run_backtest()

    # 結果表示
    backtest.print_summary()

    # 結果保存
    backtest.save_results("backtest_results.json")

    print("\nバックテスト完了！結果は backtest_results.json に保存されました。")


if __name__ == "__main__":
    main()
