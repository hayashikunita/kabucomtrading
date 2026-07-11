"""
ウォークフォワード分析機能
過学習を検証するため、訓練期間とテスト期間に分割してバックテストを実行
"""

import json
import logging
from datetime import datetime
from typing import Dict, List, Tuple

import pandas as pd

import settings
from app.data.yahoo import fetch_yahoo_data
from app.models.dfcandle import DataFrameCandle

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class WalkForwardAnalysis:
    """ウォークフォワード分析"""

    def __init__(
        self,
        product_code: str,
        total_days: int,
        train_ratio: float = 0.7,
        n_splits: int = 3,
        duration: str = "1d",
    ):
        """
        Args:
            product_code: 銘柄コード
            total_days: 総期間（日数）
            train_ratio: 訓練データの割合（0.0-1.0）
            n_splits: ウォークフォワードの分割数
            duration: 時間軸
        """
        self.product_code = product_code
        self.total_days = total_days
        self.train_ratio = train_ratio
        self.n_splits = n_splits
        self.duration = duration
        self.results = []

    def fetch_data(self):
        """データ取得"""
        logger.info(f"action=fetch_data product_code={self.product_code} days={self.total_days}")

        candles = fetch_yahoo_data(
            product_code=self.product_code,
            period_days=self.total_days,
            duration=self.duration,
            market="T",
        )

        if not candles:
            logger.error("action=fetch_data error=no_data")
            return []

        logger.info(f"action=fetch_data success count={len(candles)}")
        return candles

    def split_data(self, candles: List) -> List[Tuple[List, List]]:
        """
        データを訓練期間とテスト期間に分割

        Returns:
            [(train_data, test_data), ...] のリスト
        """
        total_count = len(candles)
        train_size = int(total_count * self.train_ratio)

        # ウォークフォワード分割を計算
        splits = []
        step_size = (total_count - train_size) // self.n_splits

        for i in range(self.n_splits):
            start_idx = i * step_size
            train_end_idx = start_idx + train_size
            test_end_idx = min(train_end_idx + step_size, total_count)

            if test_end_idx <= train_end_idx:
                break

            train_data = candles[start_idx:train_end_idx]
            test_data = candles[train_end_idx:test_end_idx]

            splits.append((train_data, test_data))
            logger.info(
                f"Split {i+1}: Train={len(train_data)} ({start_idx}-{train_end_idx}), "
                f"Test={len(test_data)} ({train_end_idx}-{test_end_idx})"
            )

        return splits

    def optimize_on_train(self, train_candles: List, strategy: str = "ema") -> Dict:
        """訓練データでパラメータ最適化"""
        df = DataFrameCandle(self.product_code, self.duration)

        # SimpleCandle変換
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

        df.candles = [SimpleCandle(c) for c in train_candles]

        # 戦略ごとに最適化
        if strategy == "ema":
            performance, p1, p2 = df.optimize_ema()
            return {"strategy": "ema", "performance": performance, "period1": p1, "period2": p2}

        if strategy == "bb":
            performance, n, k = df.optimize_bb()
            return {"strategy": "bb", "performance": performance, "n": n, "k": k}

        if strategy == "rsi":
            performance, period, buy_th, sell_th = df.optimize_rsi()
            return {
                "strategy": "rsi",
                "performance": performance,
                "period": period,
                "buy_threshold": buy_th,
                "sell_threshold": sell_th,
            }

        if strategy == "macd":
            performance, fast, slow, signal = df.optimize_macd()
            return {
                "strategy": "macd",
                "performance": performance,
                "fast_period": fast,
                "slow_period": slow,
                "signal_period": signal,
            }

        raise ValueError(f"Unknown strategy: {strategy}")

    def test_on_test(self, test_candles: List, optimized_params: Dict) -> float:
        """テストデータで検証"""
        df = DataFrameCandle(self.product_code, self.duration)

        # SimpleCandle変換
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

        df.candles = [SimpleCandle(c) for c in test_candles]

        strategy = optimized_params["strategy"]

        # 戦略ごとにテスト
        if strategy == "ema":
            df.add_ema(optimized_params["period1"])
            df.add_ema(optimized_params["period2"])
            signal_events = df.back_test_ema(optimized_params["period1"], optimized_params["period2"])

        elif strategy == "bb":
            df.add_bbands(optimized_params["n"], optimized_params["k"])
            signal_events = df.back_test_bb(optimized_params["n"], optimized_params["k"])

        elif strategy == "rsi":
            df.add_rsi(optimized_params["period"])
            signal_events = df.back_test_rsi(
                optimized_params["period"], optimized_params["buy_threshold"], optimized_params["sell_threshold"]
            )

        elif strategy == "macd":
            df.add_macd(
                optimized_params["fast_period"], optimized_params["slow_period"], optimized_params["signal_period"]
            )
            signal_events = df.back_test_macd(
                optimized_params["fast_period"], optimized_params["slow_period"], optimized_params["signal_period"]
            )

        else:
            return 0.0

        return signal_events.profit if signal_events and signal_events.profit else 0.0

    def run_analysis(self, strategy: str = "ema"):
        """ウォークフォワード分析を実行"""
        logger.info(f"action=run_analysis product_code={self.product_code} strategy={strategy}")

        # データ取得
        candles = self.fetch_data()
        if not candles:
            logger.error("action=run_analysis error=no_data")
            return

        # データ分割
        splits = self.split_data(candles)

        # 各分割でバックテスト
        for i, (train_data, test_data) in enumerate(splits):
            logger.info(f"action=run_split split={i+1}/{len(splits)}")

            # 訓練データで最適化
            optimized_params = self.optimize_on_train(train_data, strategy)
            train_performance = optimized_params["performance"]

            logger.info(f"Train performance: {train_performance:.2f}")
            logger.info(f"Optimized params: {optimized_params}")

            # テストデータで検証
            test_performance = self.test_on_test(test_data, optimized_params)

            logger.info(f"Test performance: {test_performance:.2f}")

            # 結果を保存
            result = {
                "split": i + 1,
                "train_size": len(train_data),
                "test_size": len(test_data),
                "train_performance": train_performance,
                "test_performance": test_performance,
                "degradation": train_performance - test_performance,
                "degradation_percent": ((train_performance - test_performance) / train_performance * 100)
                if train_performance != 0
                else 0,
                "optimized_params": optimized_params,
            }

            self.results.append(result)

        logger.info("action=run_analysis status=complete")

    def get_summary_stats(self) -> Dict:
        """サマリー統計を取得"""
        if not self.results:
            return {}

        train_perfs = [r["train_performance"] for r in self.results]
        test_perfs = [r["test_performance"] for r in self.results]
        degradations = [r["degradation"] for r in self.results]

        return {
            "n_splits": len(self.results),
            "avg_train_performance": sum(train_perfs) / len(train_perfs),
            "avg_test_performance": sum(test_perfs) / len(test_perfs),
            "avg_degradation": sum(degradations) / len(degradations),
            "avg_degradation_percent": sum(r["degradation_percent"] for r in self.results) / len(self.results),
            "stability_score": min(test_perfs) / max(test_perfs) if max(test_perfs) > 0 else 0,
        }

    def save_results(self, filename: str):
        """結果をJSONファイルに保存"""
        output = {
            "product_code": self.product_code,
            "total_days": self.total_days,
            "train_ratio": self.train_ratio,
            "n_splits": self.n_splits,
            "duration": self.duration,
            "timestamp": datetime.now().isoformat(),
            "summary": self.get_summary_stats(),
            "results": self.results,
        }

        with open(filename, "w", encoding="utf-8") as f:
            json.dump(output, f, indent=2, ensure_ascii=False)

        logger.info(f"action=save_results file={filename}")

    def print_summary(self):
        """サマリーを表示"""
        print("\n" + "=" * 80)
        print("ウォークフォワード分析結果")
        print("=" * 80)
        print(f"銘柄コード: {self.product_code}")
        print(f"総期間: {self.total_days}日")
        print(f"訓練データ比率: {self.train_ratio * 100:.0f}%")
        print(f"分割数: {self.n_splits}")
        print("-" * 80)

        for result in self.results:
            print(f"\n【Split {result['split']}/{self.n_splits}】")
            print(f"  訓練データサイズ: {result['train_size']}")
            print(f"  テストデータサイズ: {result['test_size']}")
            print(f"  訓練パフォーマンス: {result['train_performance']:.2f}")
            print(f"  テストパフォーマンス: {result['test_performance']:.2f}")
            print(f"  劣化: {result['degradation']:.2f} ({result['degradation_percent']:.1f}%)")

        print("\n" + "-" * 80)
        stats = self.get_summary_stats()
        print(f"平均訓練パフォーマンス: {stats['avg_train_performance']:.2f}")
        print(f"平均テストパフォーマンス: {stats['avg_test_performance']:.2f}")
        print(f"平均劣化: {stats['avg_degradation']:.2f} ({stats['avg_degradation_percent']:.1f}%)")
        print(f"安定性スコア: {stats['stability_score']:.3f}")
        print("=" * 80 + "\n")


def main():
    """メイン実行関数"""
    import argparse

    parser = argparse.ArgumentParser(description="ウォークフォワード分析")
    parser.add_argument("--code", type=str, required=True, help="銘柄コード")
    parser.add_argument("--days", type=int, default=730, help="総期間（日数）")
    parser.add_argument("--train-ratio", type=float, default=0.7, help="訓練データ比率")
    parser.add_argument("--splits", type=int, default=3, help="分割数")
    parser.add_argument("--strategy", type=str, default="ema", choices=["ema", "bb", "rsi", "macd"], help="戦略")
    parser.add_argument("--duration", type=str, default=settings.trade_duration, help="時間軸")

    args = parser.parse_args()

    print(f"\nウォークフォワード分析開始")
    print(f"銘柄コード: {args.code}")
    print(f"総期間: {args.days}日")
    print(f"訓練データ比率: {args.train_ratio * 100:.0f}%")
    print(f"分割数: {args.splits}")
    print(f"戦略: {args.strategy}")
    print()

    # 分析実行
    wf = WalkForwardAnalysis(
        product_code=args.code,
        total_days=args.days,
        train_ratio=args.train_ratio,
        n_splits=args.splits,
        duration=args.duration,
    )

    wf.run_analysis(strategy=args.strategy)

    # 結果表示
    wf.print_summary()

    # 結果保存
    filename = (
        f"{settings.walkforward_dir}/"
        f"walkforward_{args.code}_{args.strategy}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    )
    wf.save_results(filename)

    print(f"\n分析完了！結果は {filename} に保存されました。")


if __name__ == "__main__":
    main()
