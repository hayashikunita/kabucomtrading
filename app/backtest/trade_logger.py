"""
取引ログを記録・管理するモジュール
"""

import json
from datetime import datetime
from typing import Dict, List, Optional

import pandas as pd


class TradeLogger:
    """取引の詳細をログとして記録"""

    def __init__(self):
        self.trades: List[Dict] = []
        self.current_position: Optional[Dict] = None

    def open_position(
        self,
        time: datetime,
        price: float,
        side: str,
        quantity: int = 1,
        strategy: str = "",
        indicator_values: Optional[Dict] = None,
    ):
        """ポジションをオープン"""
        self.current_position = {
            "entry_time": time,
            "entry_price": price,
            "side": side,
            "quantity": quantity,
            "strategy": strategy,
            "indicator_values_entry": indicator_values or {},
        }

    def close_position(
        self,
        time: datetime,
        price: float,
        indicator_values: Optional[Dict] = None,
        profit_override: Optional[float] = None,
        extra_fields: Optional[Dict] = None,
    ):
        """ポジションをクローズ"""
        if self.current_position is None:
            return

        # 損益計算
        if self.current_position["side"] == "BUY":
            profit = (price - self.current_position["entry_price"]) * self.current_position["quantity"]
        else:  # SELL
            profit = (self.current_position["entry_price"] - price) * self.current_position["quantity"]

        if profit_override is not None:
            profit = profit_override

        # 取引記録を保存
        trade = {
            "entry_time": self.current_position["entry_time"],
            "exit_time": time,
            "entry_price": self.current_position["entry_price"],
            "exit_price": price,
            "side": self.current_position["side"],
            "quantity": self.current_position["quantity"],
            "profit": profit,
            "profit_percent": (profit / (self.current_position["entry_price"] * self.current_position["quantity"]))
            * 100,
            "duration": (time - self.current_position["entry_time"]).total_seconds() / 3600,  # 時間単位
            "strategy": self.current_position["strategy"],
            "indicator_values_entry": self.current_position["indicator_values_entry"],
            "indicator_values_exit": indicator_values or {},
        }

        if extra_fields:
            trade.update(extra_fields)

        self.trades.append(trade)
        self.current_position = None

    def get_trades(self) -> List[Dict]:
        """すべての取引記録を取得"""
        return self.trades

    def save_to_csv(self, filename: str):
        """取引記録をCSVファイルに保存"""
        if not self.trades:
            print("保存する取引記録がありません")
            return

        # DataFrameに変換
        df = pd.DataFrame(self.trades)

        # indicator_values列をJSON文字列に変換
        if "indicator_values_entry" in df.columns:
            df["indicator_values_entry"] = df["indicator_values_entry"].apply(json.dumps)
        if "indicator_values_exit" in df.columns:
            df["indicator_values_exit"] = df["indicator_values_exit"].apply(json.dumps)

        # CSVに保存
        df.to_csv(filename, index=False, encoding="utf-8-sig")
        print(f"取引記録を保存しました: {filename} ({len(self.trades)}件)")

    def save_to_json(self, filename: str):
        """取引記録をJSONファイルに保存"""
        if not self.trades:
            print("保存する取引記録がありません")
            return

        # datetime型をISO形式の文字列に変換
        trades_serializable = []
        for trade in self.trades:
            trade_copy = trade.copy()
            if isinstance(trade_copy.get("entry_time"), datetime):
                trade_copy["entry_time"] = trade_copy["entry_time"].isoformat()
            if isinstance(trade_copy.get("exit_time"), datetime):
                trade_copy["exit_time"] = trade_copy["exit_time"].isoformat()
            trades_serializable.append(trade_copy)

        with open(filename, "w", encoding="utf-8") as f:
            json.dump(trades_serializable, f, indent=2, ensure_ascii=False)

        print(f"取引記録を保存しました: {filename} ({len(self.trades)}件)")

    def get_summary_stats(self) -> Dict:
        """取引記録のサマリー統計を取得"""
        if not self.trades:
            return {}

        df = pd.DataFrame(self.trades)

        return {
            "total_trades": len(self.trades),
            "winning_trades": len(df[df["profit"] > 0]),
            "losing_trades": len(df[df["profit"] < 0]),
            "total_profit": df["profit"].sum(),
            "average_profit": df["profit"].mean(),
            "max_profit": df["profit"].max(),
            "min_profit": df["profit"].min(),
            "average_duration_hours": df["duration"].mean(),
            "total_duration_hours": df["duration"].sum(),
        }

    def print_summary(self):
        """サマリーを表示"""
        stats = self.get_summary_stats()

        if not stats:
            print("取引記録がありません")
            return

        print("\n" + "=" * 60)
        print("取引ログサマリー")
        print("=" * 60)
        print(f"総取引数:        {stats['total_trades']}")
        print(f"勝ちトレード:    {stats['winning_trades']}")
        print(f"負けトレード:    {stats['losing_trades']}")
        print(f"総利益:          {stats['total_profit']:,.2f}")
        print(f"平均利益:        {stats['average_profit']:,.2f}")
        print(f"最大利益:        {stats['max_profit']:,.2f}")
        print(f"最大損失:        {stats['min_profit']:,.2f}")
        print(f"平均保有時間:    {stats['average_duration_hours']:.2f}時間")
        print("=" * 60 + "\n")

    def clear(self):
        """記録をクリア"""
        self.trades = []
        self.current_position = None
