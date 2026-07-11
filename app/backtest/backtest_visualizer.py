"""
バックテスト結果を可視化するモジュール
"""

from datetime import datetime
from typing import Dict, List, Optional

import matplotlib

matplotlib.use("Agg")  # GUIなし環境用
import matplotlib.dates as mdates
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns


class BacktestVisualizer:
    """バックテスト結果の可視化"""

    def __init__(self, trades: List[Dict], figsize=(15, 10)):
        """
        Args:
            trades: 取引記録のリスト
            figsize: グラフのサイズ
        """
        self.trades = trades
        self.figsize = figsize

        # 日本語フォント設定
        plt.rcParams["font.sans-serif"] = ["MS Gothic", "Yu Gothic", "Meiryo"]
        plt.rcParams["axes.unicode_minus"] = False

    def plot_equity_curve(self, initial_capital: float = 1000000, save_path: Optional[str] = None):
        """資産曲線をプロット"""
        if not self.trades:
            print("取引記録がありません")
            return

        # 累積損益を計算
        profits = [t["profit"] for t in self.trades]
        cumulative = np.cumsum(profits)
        equity = initial_capital + cumulative

        # 時刻データを取得
        times = [t["exit_time"] for t in self.trades]

        # プロット
        _, ax = plt.subplots(figsize=self.figsize)
        ax.plot(times, equity, linewidth=2, label="資産推移")
        ax.axhline(y=initial_capital, color="gray", linestyle="--", alpha=0.7, label="初期資産")
        ax.fill_between(times, initial_capital, equity, where=(equity >= initial_capital), alpha=0.3, color="green")
        ax.fill_between(times, initial_capital, equity, where=(equity < initial_capital), alpha=0.3, color="red")

        ax.set_xlabel("時刻")
        ax.set_ylabel("資産 (円)")
        ax.set_title("資産曲線 (Equity Curve)")
        ax.legend()
        ax.grid(True, alpha=0.3)

        # 日付フォーマット
        if times and isinstance(times[0], datetime):
            ax.xaxis.set_major_formatter(mdates.DateFormatter("%Y-%m-%d"))
            plt.xticks(rotation=45)

        plt.tight_layout()

        if save_path:
            plt.savefig(save_path, dpi=300, bbox_inches="tight")
            print(f"資産曲線を保存しました: {save_path}")
        else:
            plt.show()

        plt.close()

    def plot_drawdown(self, save_path: Optional[str] = None):
        """ドローダウンチャートをプロット"""
        if not self.trades:
            print("取引記録がありません")
            return

        # 累積損益を計算
        profits = [t["profit"] for t in self.trades]
        cumulative = np.cumsum(profits)

        # ドローダウンを計算
        running_max = np.maximum.accumulate(cumulative)
        drawdown = running_max - cumulative

        # 時刻データを取得
        times = [t["exit_time"] for t in self.trades]

        # プロット
        _, ax = plt.subplots(figsize=self.figsize)
        ax.fill_between(times, 0, drawdown, alpha=0.5, color="red", label="ドローダウン")
        ax.plot(times, drawdown, linewidth=2, color="darkred")

        ax.set_xlabel("時刻")
        ax.set_ylabel("ドローダウン (円)")
        ax.set_title("ドローダウンチャート")
        ax.legend()
        ax.grid(True, alpha=0.3)

        # 最大ドローダウンをマーク
        max_dd_idx = np.argmax(drawdown)
        ax.axhline(y=drawdown[max_dd_idx], color="black", linestyle="--", alpha=0.7)
        ax.text(times[0], drawdown[max_dd_idx], f"最大DD: {drawdown[max_dd_idx]:,.0f}円", verticalalignment="bottom")

        # 日付フォーマット
        if times and isinstance(times[0], datetime):
            ax.xaxis.set_major_formatter(mdates.DateFormatter("%Y-%m-%d"))
            plt.xticks(rotation=45)

        plt.tight_layout()

        if save_path:
            plt.savefig(save_path, dpi=300, bbox_inches="tight")
            print(f"ドローダウンチャートを保存しました: {save_path}")
        else:
            plt.show()

        plt.close()

    def plot_profit_distribution(self, save_path: Optional[str] = None):
        """損益分布のヒストグラムをプロット"""
        if not self.trades:
            print("取引記録がありません")
            return

        profits = [t["profit"] for t in self.trades]

        # プロット
        _, ax = plt.subplots(figsize=self.figsize)

        # ヒストグラム
        _, bins, patches = ax.hist(profits, bins=30, alpha=0.7, edgecolor="black")

        # 勝ちトレードと負けトレードで色分け
        for i, patch in enumerate(patches):
            if bins[i] < 0:
                patch.set_facecolor("red")
            else:
                patch.set_facecolor("green")

        # 統計情報を追加
        ax.axvline(x=0, color="black", linestyle="--", linewidth=2, alpha=0.7)
        ax.axvline(
            x=np.mean(profits),
            color="blue",
            linestyle="--",
            linewidth=2,
            alpha=0.7,
            label=f"平均: {np.mean(profits):.2f}",
        )

        ax.set_xlabel("損益 (円)")
        ax.set_ylabel("頻度")
        ax.set_title("損益分布")
        ax.legend()
        ax.grid(True, alpha=0.3, axis="y")

        plt.tight_layout()

        if save_path:
            plt.savefig(save_path, dpi=300, bbox_inches="tight")
            print(f"損益分布を保存しました: {save_path}")
        else:
            plt.show()

        plt.close()

    def plot_monthly_returns(self, save_path: Optional[str] = None):
        """月次リターンをプロット"""
        if not self.trades:
            print("取引記録がありません")
            return

        # DataFrameに変換
        df = pd.DataFrame(self.trades)

        # datetime型に変換
        if not isinstance(df["exit_time"].iloc[0], datetime):
            df["exit_time"] = pd.to_datetime(df["exit_time"])

        # 月ごとに集計
        df["year_month"] = df["exit_time"].dt.to_period("M")
        monthly = df.groupby("year_month")["profit"].sum()

        # プロット
        _, ax = plt.subplots(figsize=self.figsize)

        colors = ["green" if x > 0 else "red" for x in monthly.values]
        ax.bar(range(len(monthly)), monthly.values, color=colors, alpha=0.7, edgecolor="black")

        ax.set_xlabel("月")
        ax.set_ylabel("月次損益 (円)")
        ax.set_title("月次リターン")
        ax.axhline(y=0, color="black", linestyle="-", linewidth=1)
        ax.grid(True, alpha=0.3, axis="y")

        # X軸ラベル
        ax.set_xticks(range(len(monthly)))
        ax.set_xticklabels([str(x) for x in monthly.index], rotation=45, ha="right")

        plt.tight_layout()

        if save_path:
            plt.savefig(save_path, dpi=300, bbox_inches="tight")
            print(f"月次リターンを保存しました: {save_path}")
        else:
            plt.show()

        plt.close()

    def plot_parameter_heatmap(
        self,
        results: List[Dict],
        param1_name: str,
        param2_name: str,
        save_path: Optional[str] = None,
    ):
        """パラメータ最適化のヒートマップをプロット"""
        if not results:
            print("結果データがありません")
            return

        # DataFrameに変換
        df = pd.DataFrame(results)

        # ピボットテーブルを作成
        pivot = df.pivot(index=param1_name, columns=param2_name, values="performance")

        # プロット
        _, ax = plt.subplots(figsize=self.figsize)
        sns.heatmap(pivot, annot=False, fmt=".1f", cmap="RdYlGn", center=0, ax=ax, cbar_kws={"label": "パフォーマンス"})

        ax.set_title(f"パラメータ最適化ヒートマップ ({param1_name} vs {param2_name})")
        ax.set_xlabel(param2_name)
        ax.set_ylabel(param1_name)

        plt.tight_layout()

        if save_path:
            plt.savefig(save_path, dpi=300, bbox_inches="tight")
            print(f"ヒートマップを保存しました: {save_path}")
        else:
            plt.show()

        plt.close()

    def create_comprehensive_report(self, output_dir: str, prefix: str = "backtest"):
        """包括的なレポートを生成"""
        import os

        os.makedirs(output_dir, exist_ok=True)

        print(f"\n包括的なレポートを生成中: {output_dir}/")

        # 各種グラフを生成
        self.plot_equity_curve(save_path=f"{output_dir}/{prefix}_equity_curve.png")
        self.plot_drawdown(save_path=f"{output_dir}/{prefix}_drawdown.png")
        self.plot_profit_distribution(save_path=f"{output_dir}/{prefix}_profit_distribution.png")
        self.plot_monthly_returns(save_path=f"{output_dir}/{prefix}_monthly_returns.png")

        print(f"レポート生成完了: {output_dir}/")
