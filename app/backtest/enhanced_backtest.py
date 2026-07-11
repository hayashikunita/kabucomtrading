"""
リスク管理機能を備えた拡張バックテストエンジン
"""

import logging
import math
from datetime import datetime
from typing import Dict, List, Optional

from app.backtest.backtest_metrics import BacktestMetrics
from app.backtest.backtest_visualizer import BacktestVisualizer
from app.backtest.trade_logger import TradeLogger

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class RiskManagement:
    """リスク管理クラス"""

    def __init__(
        self,
        initial_capital: float = 1000000,
        position_size_percent: float = 100.0,
        transaction_cost_percent: float = 0.1,
        slippage_percent: float = 0.02,
        stop_loss_percent: Optional[float] = None,
        take_profit_percent: Optional[float] = None,
        max_positions: int = 1,
        risk_per_trade_percent: float = 2.0,
        max_position_quantity: int = 1_000_000,
        min_valid_price: float = 1e-6,
    ):
        self.initial_capital = initial_capital
        self.current_capital = initial_capital
        self.position_size_percent = position_size_percent
        self.transaction_cost_percent = transaction_cost_percent
        self.slippage_percent = slippage_percent
        self.stop_loss_percent = stop_loss_percent
        self.take_profit_percent = take_profit_percent
        self.max_positions = max_positions
        self.risk_per_trade_percent = risk_per_trade_percent
        self.max_position_quantity = max_position_quantity
        self.min_valid_price = min_valid_price
        self.current_positions = 0

    def can_open_position(self) -> bool:
        return self.current_positions < self.max_positions

    def calculate_position_size(self, price: float) -> int:
        if not math.isfinite(price) or price <= self.min_valid_price:
            return 0
        if not math.isfinite(self.current_capital) or self.current_capital <= 0:
            return 0

        available_capital = self.current_capital * (self.position_size_percent / 100.0)
        quantity = int(available_capital / price)
        quantity = max(1, quantity)
        return min(quantity, self.max_position_quantity)

    def calculate_stop_loss_price(self, entry_price: float, side: str) -> Optional[float]:
        if self.stop_loss_percent is None:
            return None
        if side == "BUY":
            return entry_price * (1 - self.stop_loss_percent / 100.0)
        return entry_price * (1 + self.stop_loss_percent / 100.0)

    def calculate_take_profit_price(self, entry_price: float, side: str) -> Optional[float]:
        if self.take_profit_percent is None:
            return None
        if side == "BUY":
            return entry_price * (1 + self.take_profit_percent / 100.0)
        return entry_price * (1 - self.take_profit_percent / 100.0)

    def should_stop_loss(self, current_price: float, entry_price: float, side: str) -> bool:
        stop_loss_price = self.calculate_stop_loss_price(entry_price, side)
        if stop_loss_price is None:
            return False
        if side == "BUY":
            return current_price <= stop_loss_price
        return current_price >= stop_loss_price

    def should_take_profit(self, current_price: float, entry_price: float, side: str) -> bool:
        take_profit_price = self.calculate_take_profit_price(entry_price, side)
        if take_profit_price is None:
            return False
        if side == "BUY":
            return current_price >= take_profit_price
        return current_price <= take_profit_price

    def update_capital(self, profit: float):
        self.current_capital += profit

    def open_position(self):
        self.current_positions += 1

    def close_position(self):
        self.current_positions = max(0, self.current_positions - 1)

    def get_stats(self) -> Dict:
        return {
            "initial_capital": self.initial_capital,
            "current_capital": self.current_capital,
            "total_profit": self.current_capital - self.initial_capital,
            "return_percent": ((self.current_capital - self.initial_capital) / self.initial_capital) * 100,
            "transaction_cost_percent": self.transaction_cost_percent,
            "slippage_percent": self.slippage_percent,
            "current_positions": self.current_positions,
        }


class EnhancedBacktest:
    """リスク管理機能を備えた拡張バックテスト"""

    def __init__(
        self,
        product_code: str,
        candles: List,
        risk_management: Optional[RiskManagement] = None,
    ):
        self.product_code = product_code
        self.candles = candles
        self.risk_management = risk_management or RiskManagement()
        self.trade_logger = TradeLogger()
        self.current_position = None

    @staticmethod
    def _candle_value(candle, name: str, default: float = 0.0) -> float:
        return float(getattr(candle, name, default))

    def _position_stop_loss_price(self) -> Optional[float]:
        if not self.current_position:
            return None
        fixed_price = self.current_position.get("stop_loss_price")
        if fixed_price is not None:
            return fixed_price

        stop_pct = self.current_position.get("stop_loss_percent")
        if stop_pct is not None:
            entry = self.current_position["entry_price"]
            side = self.current_position["side"]
            if side == "BUY":
                return entry * (1 - stop_pct / 100.0)
            return entry * (1 + stop_pct / 100.0)

        base_stop = self.risk_management.calculate_stop_loss_price(
            self.current_position["entry_price"], self.current_position["side"]
        )
        dynamic_stop = self.current_position.get("dynamic_stop_loss_price")
        if dynamic_stop is None:
            return base_stop
        if base_stop is None:
            return dynamic_stop
        if self.current_position["side"] == "BUY":
            return max(base_stop, dynamic_stop)
        return min(base_stop, dynamic_stop)

    def _position_take_profit_price(self) -> Optional[float]:
        if not self.current_position:
            return None
        fixed_price = self.current_position.get("take_profit_price")
        if fixed_price is not None:
            return fixed_price

        take_pct = self.current_position.get("take_profit_percent")
        if take_pct is not None:
            entry = self.current_position["entry_price"]
            side = self.current_position["side"]
            if side == "BUY":
                return entry * (1 + take_pct / 100.0)
            return entry * (1 - take_pct / 100.0)

        return self.risk_management.calculate_take_profit_price(
            self.current_position["entry_price"], self.current_position["side"]
        )

    def _update_dynamic_risk_levels(self, candle, candle_index: int):
        if not self.current_position:
            return

        side = self.current_position["side"]
        entry_price = self.current_position["entry_price"]
        high_price = self._candle_value(candle, "high", self._candle_value(candle, "close"))
        low_price = self._candle_value(candle, "low", self._candle_value(candle, "close"))

        if side == "BUY":
            self.current_position["highest_price"] = max(self.current_position["highest_price"], high_price)
        else:
            self.current_position["lowest_price"] = min(self.current_position["lowest_price"], low_price)

        break_even_trigger_percent = self.current_position.get("break_even_trigger_percent")
        if break_even_trigger_percent is not None:
            if side == "BUY" and high_price >= entry_price * (1 + break_even_trigger_percent / 100.0):
                current_dynamic = self.current_position.get("dynamic_stop_loss_price")
                self.current_position["dynamic_stop_loss_price"] = max(current_dynamic or entry_price, entry_price)
            elif side == "SELL" and low_price <= entry_price * (1 - break_even_trigger_percent / 100.0):
                current_dynamic = self.current_position.get("dynamic_stop_loss_price")
                self.current_position["dynamic_stop_loss_price"] = min(current_dynamic or entry_price, entry_price)

        trailing_stop_percent = self.current_position.get("trailing_stop_percent")
        if trailing_stop_percent is not None:
            if side == "BUY":
                trailing_stop = self.current_position["highest_price"] * (1 - trailing_stop_percent / 100.0)
                current_dynamic = self.current_position.get("dynamic_stop_loss_price")
                self.current_position["dynamic_stop_loss_price"] = max(current_dynamic or trailing_stop, trailing_stop)
            else:
                trailing_stop = self.current_position["lowest_price"] * (1 + trailing_stop_percent / 100.0)
                current_dynamic = self.current_position.get("dynamic_stop_loss_price")
                self.current_position["dynamic_stop_loss_price"] = min(current_dynamic or trailing_stop, trailing_stop)

        self.current_position["bars_held"] = candle_index - self.current_position["entry_index"]

    def _stop_loss_trigger_price(self, candle) -> Optional[float]:
        stop_loss_price = self._position_stop_loss_price()
        if stop_loss_price is None or not self.current_position:
            return None
        if self.current_position["side"] == "BUY":
            return stop_loss_price if self._candle_value(candle, "low") <= stop_loss_price else None
        return stop_loss_price if self._candle_value(candle, "high") >= stop_loss_price else None

    def _take_profit_trigger_price(self, candle) -> Optional[float]:
        take_profit_price = self._position_take_profit_price()
        if take_profit_price is None or not self.current_position:
            return None
        if self.current_position["side"] == "BUY":
            return take_profit_price if self._candle_value(candle, "high") >= take_profit_price else None
        return take_profit_price if self._candle_value(candle, "low") <= take_profit_price else None

    def _should_time_stop(self) -> bool:
        if not self.current_position:
            return False
        max_bars_hold = self.current_position.get("max_bars_hold")
        if max_bars_hold is None:
            return False
        return self.current_position.get("bars_held", 0) >= max_bars_hold

    def _apply_execution_price(self, price: float, side: str, is_entry: bool) -> float:
        slippage_rate = self.risk_management.slippage_percent / 100.0
        if (side == "BUY" and is_entry) or (side == "SELL" and not is_entry):
            return price * (1 + slippage_rate)
        return price * (1 - slippage_rate)

    def _estimate_years_from_candles(self) -> float:
        if not self.candles or len(self.candles) < 2:
            return 1.0

        first_time = getattr(self.candles[0], "time", None)
        last_time = getattr(self.candles[-1], "time", None)

        if not first_time or not last_time:
            return 1.0

        days = max((last_time - first_time).days, 1)
        return max(days / 365.25, 1 / 365.25)

    def execute_backtest(self, signals: List[Dict]) -> Dict:
        logger.info(f"action=execute_backtest signals={len(signals)}")
        signals_by_time: Dict = {}
        for signal in signals:
            signals_by_time.setdefault(signal["time"], []).append(signal)

        for candle_index, candle in enumerate(self.candles):
            candle_time = getattr(candle, "time", None)
            candle_close = self._candle_value(candle, "close")

            if self.current_position:
                self._update_dynamic_risk_levels(candle, candle_index)

                stop_trigger_price = self._stop_loss_trigger_price(candle)
                if stop_trigger_price is not None:
                    logger.info(f"Stop loss triggered at {stop_trigger_price}")
                    self._close_position(candle_time, stop_trigger_price, {}, "STOP_LOSS")

                if self.current_position:
                    take_trigger_price = self._take_profit_trigger_price(candle)
                    if take_trigger_price is not None:
                        logger.info(f"Take profit triggered at {take_trigger_price}")
                        self._close_position(candle_time, take_trigger_price, {}, "TAKE_PROFIT")

                if self.current_position and self._should_time_stop():
                    logger.info(f"Time stop triggered at {candle_close}")
                    self._close_position(candle_time, candle_close, {}, "TIME_STOP")

            for signal in signals_by_time.get(candle_time, []):
                signal_time = signal["time"]
                signal_type = signal["type"]
                signal_intent = signal.get("intent", "ENTRY")
                signal_price = signal["price"]
                indicators = signal.get("indicators", {})

                if self.current_position:
                    if (self.current_position["side"] == "BUY" and signal_type == "SELL") or (
                        self.current_position["side"] == "SELL" and signal_type == "BUY"
                    ):
                        self._close_position(signal_time, signal_price, indicators, "SIGNAL")
                else:
                    if signal_intent == "ENTRY" and self.risk_management.can_open_position():
                        self._open_position(signal_time, signal_price, signal_type, indicators, signal.get("risk", {}), candle_index)

        if self.current_position and self.candles:
            last_candle = self.candles[-1]
            final_price = self._candle_value(last_candle, "close", self._candle_value(last_candle, "open", 0.0))
            self._close_position(
                last_candle.time if hasattr(last_candle, "time") else datetime.now(),
                final_price,
                {},
                "END",
            )

        return self._generate_results()

    def _open_position(
        self,
        time: datetime,
        price: float,
        side: str,
        indicators: Dict,
        risk: Optional[Dict] = None,
        candle_index: int = 0,
    ):
        execution_price = self._apply_execution_price(price, side=side, is_entry=True)
        if not math.isfinite(execution_price) or execution_price <= self.risk_management.min_valid_price:
            logger.warning(f"skip_open_invalid_price price={execution_price}")
            return

        quantity = self.risk_management.calculate_position_size(execution_price)
        if quantity <= 0:
            logger.warning(f"skip_open_invalid_quantity quantity={quantity} price={execution_price}")
            return

        risk = risk or {}
        stop_loss_price = risk.get("stop_loss")
        take_profit_price = risk.get("take_profit")
        atr_stop_multiple = risk.get("atr_stop_multiple")
        atr_value = risk.get("atr_value")
        if stop_loss_price is None and atr_stop_multiple is not None and atr_value is not None:
            if side == "BUY":
                stop_loss_price = execution_price - float(atr_value) * float(atr_stop_multiple)
            else:
                stop_loss_price = execution_price + float(atr_value) * float(atr_stop_multiple)

        self.current_position = {
            "entry_time": time,
            "entry_price": execution_price,
            "side": side,
            "quantity": quantity,
            "stop_loss_price": stop_loss_price,
            "take_profit_price": take_profit_price,
            "stop_loss_percent": risk.get("stop_loss_pct"),
            "take_profit_percent": risk.get("take_profit_pct"),
            "trailing_stop_percent": risk.get("trailing_stop_pct"),
            "break_even_trigger_percent": risk.get("break_even_trigger_pct"),
            "max_bars_hold": risk.get("max_bars_hold"),
            "atr_stop_multiple": atr_stop_multiple,
            "atr_value": atr_value,
            "dynamic_stop_loss_price": None,
            "highest_price": execution_price,
            "lowest_price": execution_price,
            "entry_index": candle_index,
            "bars_held": 0,
        }

        self.risk_management.open_position()
        self.trade_logger.open_position(
            time=time, price=execution_price, side=side, quantity=quantity, indicator_values=indicators
        )

    def _close_position(self, time: datetime, price: float, indicators: Dict, reason: str):
        if not self.current_position:
            return

        side = self.current_position["side"]
        entry_price = self.current_position["entry_price"]
        quantity = self.current_position["quantity"]
        exit_price = self._apply_execution_price(price, side=side, is_entry=False)
        if not math.isfinite(exit_price) or exit_price <= self.risk_management.min_valid_price:
            logger.warning(f"close_with_entry_price_due_to_invalid_exit exit_price={exit_price}")
            exit_price = entry_price

        if side == "BUY":
            gross_profit = (exit_price - entry_price) * quantity
        else:
            gross_profit = (entry_price - exit_price) * quantity

        turnover = (entry_price + exit_price) * quantity
        total_cost = turnover * (self.risk_management.transaction_cost_percent / 100.0)
        net_profit = gross_profit - total_cost

        if not math.isfinite(net_profit):
            logger.warning("close_with_zero_profit_due_to_non_finite_profit")
            net_profit = 0.0

        self.risk_management.update_capital(net_profit)
        self.risk_management.close_position()

        self.trade_logger.close_position(
            time=time,
            price=exit_price,
            indicator_values=indicators,
            profit_override=net_profit,
            extra_fields={
                "gross_profit": gross_profit,
                "transaction_cost": total_cost,
                "close_reason": reason,
                "stop_loss_price": self.current_position.get("stop_loss_price"),
                "take_profit_price": self.current_position.get("take_profit_price"),
                "stop_loss_percent": self.current_position.get("stop_loss_percent"),
                "take_profit_percent": self.current_position.get("take_profit_percent"),
            },
        )

        self.current_position = None

    def _generate_results(self) -> Dict:
        trades = self.trade_logger.get_trades()
        metrics = BacktestMetrics(trades)
        years = self._estimate_years_from_candles()

        return {
            "product_code": self.product_code,
            "trades": trades,
            "total_trades": len(trades),
            "metrics": metrics.get_all_metrics(
                initial_capital=self.risk_management.initial_capital,
                years=years,
            ),
            "risk_management_stats": self.risk_management.get_stats(),
            "backtest_years": years,
        }

    def save_results(self, output_dir: str, prefix: str = "enhanced_backtest"):
        import os

        os.makedirs(output_dir, exist_ok=True)

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.trade_logger.save_to_csv(f"{output_dir}/{prefix}_trades_{timestamp}.csv")
        self.trade_logger.save_to_json(f"{output_dir}/{prefix}_trades_{timestamp}.json")

        visualizer = BacktestVisualizer(self.trade_logger.get_trades())
        visualizer.create_comprehensive_report(output_dir=output_dir, prefix=f"{prefix}_{timestamp}")

        logger.info(f"Results saved to {output_dir}/")

    def print_summary(self):
        trades = self.trade_logger.get_trades()
        metrics = BacktestMetrics(trades)

        print("\n" + "=" * 80)
        print("拡張バックテスト結果")
        print("=" * 80)
        print(f"銘柄コード: {self.product_code}")
        print("-" * 80)

        rm_stats = self.risk_management.get_stats()
        print(f"初期資金: {rm_stats['initial_capital']:,.0f}円")
        print(f"最終資金: {rm_stats['current_capital']:,.0f}円")
        print(f"総利益: {rm_stats['total_profit']:,.0f}円")
        print(f"リターン: {rm_stats['return_percent']:.2f}%")

        metrics.print_summary()


def main():
    print("EnhancedBacktest モジュール")
    print("他のスクリプトからインポートして使用してください。")


if __name__ == "__main__":
    main()
