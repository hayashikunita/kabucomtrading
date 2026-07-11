"""
バックテスト結果の詳細な統計指標を計算するモジュール
"""

from typing import Dict, List

import numpy as np


class BacktestMetrics:
    """バックテストの詳細なパフォーマンス指標を計算"""

    def __init__(self, trades: List[Dict]):
        """
        Args:
            trades: 取引記録のリスト。各要素は辞書形式で以下のキーを持つ:
                - entry_time: エントリー時刻
                - exit_time: イグジット時刻
                - entry_price: エントリー価格
                - exit_price: イグジット価格
                - profit: 損益
                - side: 'BUY' or 'SELL'
        """
        self.trades = trades
        self.profits = [t["profit"] for t in trades] if trades else []

    def total_profit(self) -> float:
        """総利益"""
        return sum(self.profits)

    def total_trades(self) -> int:
        """総取引数"""
        return len(self.trades)

    def winning_trades(self) -> int:
        """勝ちトレード数"""
        return sum(1 for p in self.profits if p > 0)

    def losing_trades(self) -> int:
        """負けトレード数"""
        return sum(1 for p in self.profits if p < 0)

    def win_rate(self) -> float:
        """勝率 (%)"""
        if self.total_trades() == 0:
            return 0.0
        return (self.winning_trades() / self.total_trades()) * 100

    def average_profit(self) -> float:
        """平均利益"""
        if not self.profits:
            return 0.0
        return np.mean(self.profits)

    def average_win(self) -> float:
        """平均勝ちトレード"""
        wins = [p for p in self.profits if p > 0]
        if not wins:
            return 0.0
        return np.mean(wins)

    def average_loss(self) -> float:
        """平均負けトレード"""
        losses = [p for p in self.profits if p < 0]
        if not losses:
            return 0.0
        return np.mean(losses)

    def profit_factor(self) -> float:
        """プロフィットファクター (総利益 / 総損失)"""
        gross_profit = sum(p for p in self.profits if p > 0)
        gross_loss = abs(sum(p for p in self.profits if p < 0))

        if gross_loss == 0:
            return float("inf") if gross_profit > 0 else 0.0
        return gross_profit / gross_loss

    def max_drawdown(self) -> float:
        """最大ドローダウン"""
        if not self.profits:
            return 0.0

        cumulative = np.cumsum(self.profits)
        running_max = np.maximum.accumulate(cumulative)
        drawdown = running_max - cumulative
        return np.max(drawdown)

    def max_drawdown_percent(self, initial_capital: float = 1000000) -> float:
        """最大ドローダウン率 (%)"""
        max_dd = self.max_drawdown()
        if initial_capital == 0:
            return 0.0
        return (max_dd / initial_capital) * 100

    def sharpe_ratio(self, risk_free_rate: float = 0.0) -> float:
        """シャープレシオ"""
        if not self.profits or len(self.profits) < 2:
            return 0.0

        returns = np.array(self.profits)
        excess_returns = returns - risk_free_rate

        if np.std(excess_returns) == 0:
            return 0.0

        return np.mean(excess_returns) / np.std(excess_returns)

    def sortino_ratio(self, risk_free_rate: float = 0.0) -> float:
        """ソルティノレシオ (下方リスクのみを考慮)"""
        if not self.profits or len(self.profits) < 2:
            return 0.0

        returns = np.array(self.profits)
        excess_returns = returns - risk_free_rate
        downside_returns = excess_returns[excess_returns < 0]

        if len(downside_returns) == 0 or np.std(downside_returns) == 0:
            return 0.0

        return np.mean(excess_returns) / np.std(downside_returns)

    def max_consecutive_wins(self) -> int:
        """最大連勝数"""
        if not self.profits:
            return 0

        max_wins = 0
        current_wins = 0

        for profit in self.profits:
            if profit > 0:
                current_wins += 1
                max_wins = max(max_wins, current_wins)
            else:
                current_wins = 0

        return max_wins

    def max_consecutive_losses(self) -> int:
        """最大連敗数"""
        if not self.profits:
            return 0

        max_losses = 0
        current_losses = 0

        for profit in self.profits:
            if profit < 0:
                current_losses += 1
                max_losses = max(max_losses, current_losses)
            else:
                current_losses = 0

        return max_losses

    def expectancy(self) -> float:
        """期待値 (平均利益 × 勝率 + 平均損失 × 負率)"""
        if self.total_trades() == 0:
            return 0.0

        win_rate = self.win_rate() / 100
        loss_rate = 1 - win_rate

        return (self.average_win() * win_rate) + (self.average_loss() * loss_rate)

    def recovery_factor(self) -> float:
        """リカバリーファクター (総利益 / 最大ドローダウン)"""
        max_dd = self.max_drawdown()
        if max_dd == 0:
            return float("inf") if self.total_profit() > 0 else 0.0
        return self.total_profit() / max_dd

    def calmar_ratio(self, years: float = 1.0) -> float:
        """カルマーレシオ (年間リターン / 最大ドローダウン)"""
        max_dd = self.max_drawdown()
        if max_dd == 0:
            return 0.0

        annual_return = self.total_profit() / years
        return annual_return / max_dd

    def robust_score(self, initial_capital: float = 1000000) -> float:
        """リスク調整済みの総合スコア (0-100)"""
        if self.total_trades() == 0 or initial_capital <= 0:
            return 0.0

        return_percent = (self.total_profit() / initial_capital) * 100.0
        return_norm = np.clip((return_percent + 50.0) / 150.0, 0.0, 1.0)

        sharpe = self.sharpe_ratio()
        sharpe_norm = (np.tanh(sharpe / 2.0) + 1.0) / 2.0

        max_dd_pct = self.max_drawdown_percent(initial_capital)
        drawdown_norm = np.clip(1.0 - (max_dd_pct / 30.0), 0.0, 1.0)

        win_rate_norm = np.clip(self.win_rate() / 100.0, 0.0, 1.0)

        pf = self.profit_factor()
        pf_norm = 1.0 if np.isinf(pf) else np.clip(pf / 5.0, 0.0, 1.0)

        score = (
            0.30 * return_norm
            + 0.25 * sharpe_norm
            + 0.20 * drawdown_norm
            + 0.15 * win_rate_norm
            + 0.10 * pf_norm
        )
        return float(score * 100.0)

    def get_all_metrics(self, initial_capital: float = 1000000, years: float = 1.0) -> Dict:
        """すべての指標を辞書形式で取得"""
        return {
            "total_profit": self.total_profit(),
            "total_trades": self.total_trades(),
            "winning_trades": self.winning_trades(),
            "losing_trades": self.losing_trades(),
            "win_rate": self.win_rate(),
            "average_profit": self.average_profit(),
            "average_win": self.average_win(),
            "average_loss": self.average_loss(),
            "profit_factor": self.profit_factor(),
            "max_drawdown": self.max_drawdown(),
            "max_drawdown_percent": self.max_drawdown_percent(initial_capital),
            "sharpe_ratio": self.sharpe_ratio(),
            "sortino_ratio": self.sortino_ratio(),
            "max_consecutive_wins": self.max_consecutive_wins(),
            "max_consecutive_losses": self.max_consecutive_losses(),
            "expectancy": self.expectancy(),
            "recovery_factor": self.recovery_factor(),
            "calmar_ratio": self.calmar_ratio(years),
            "robust_score": self.robust_score(initial_capital),
        }

    def print_summary(self):
        """指標のサマリーを表示"""
        print("\n" + "=" * 70)
        print("詳細パフォーマンス指標")
        print("=" * 70)
        print(f"総利益:                  {self.total_profit():,.2f}")
        print(f"総取引数:                {self.total_trades()}")
        print(f"勝ちトレード数:          {self.winning_trades()}")
        print(f"負けトレード数:          {self.losing_trades()}")
        print(f"勝率:                    {self.win_rate():.2f}%")
        print("-" * 70)
        print(f"平均利益:                {self.average_profit():,.2f}")
        print(f"平均勝ちトレード:        {self.average_win():,.2f}")
        print(f"平均負けトレード:        {self.average_loss():,.2f}")
        print(f"期待値:                  {self.expectancy():,.2f}")
        print("-" * 70)
        print(f"プロフィットファクター:  {self.profit_factor():.2f}")
        print(f"最大ドローダウン:        {self.max_drawdown():,.2f}")
        print(f"最大連勝数:              {self.max_consecutive_wins()}")
        print(f"最大連敗数:              {self.max_consecutive_losses()}")
        print("-" * 70)
        print(f"シャープレシオ:          {self.sharpe_ratio():.3f}")
        print(f"ソルティノレシオ:        {self.sortino_ratio():.3f}")
        print(f"リカバリーファクター:    {self.recovery_factor():.2f}")
        print(f"カルマーレシオ:          {self.calmar_ratio():.2f}")
        print(f"ロバストスコア:          {self.robust_score():.2f}")
        print("=" * 70 + "\n")
