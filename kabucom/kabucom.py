import logging
import math
import time
from datetime import datetime

import requests

import constants
import settings

ORDER_FILLED = "2"  # kabusapi: 2=約定済

logger = logging.getLogger(__name__)


class Balance(object):
    def __init__(self, available):
        self.available = available


class Ticker(object):
    def __init__(self, symbol, timestamp, bid, ask, volume):
        self.symbol = symbol
        self.timestamp = timestamp
        self.bid = bid
        self.ask = ask
        self.volume = volume

    @property
    def mid_price(self):
        return (self.bid + self.ask) / 2

    @property
    def time(self):
        return datetime.fromtimestamp(self.timestamp)

    def truncate_date_time(self, duration):
        ticker_time = self.time
        if duration == constants.DURATION_5S:
            new_sec = math.floor(self.time.second / 5) * 5
            ticker_time = datetime(
                self.time.year, self.time.month, self.time.day, self.time.hour, self.time.minute, new_sec
            )
            time_format = "%Y-%m-%d %H:%M:%S"
        elif duration == constants.DURATION_1M:
            time_format = "%Y-%m-%d %H:%M"
        elif duration == constants.DURATION_1H:
            time_format = "%Y-%m-%d %H"
        else:
            logger.warning("action=truncate_date_time error=no_datetime_format")
            return None

        str_date = datetime.strftime(ticker_time, time_format)
        return datetime.strptime(str_date, time_format)


class Order(object):
    def __init__(self, symbol, side, qty, price=None, order_state=None, order_id=None):
        self.symbol = symbol
        self.side = side
        self.qty = qty
        self.price = price
        self.order_state = order_state
        self.order_id = order_id


class OrderTimeoutError(Exception):
    """Order timeout error"""


class Trade(object):
    def __init__(self, trade_id, side, price, qty):
        self.trade_id = trade_id
        self.side = side
        self.price = price
        self.qty = qty


class KabusApiClient(object):
    def __init__(self, token, url):
        self.token = token
        self.url = url

    def get_balance(self) -> Balance:
        endpoint = f"{self.url}/wallet/cash"
        headers = {"X-API-KEY": self.token}
        resp = requests.get(endpoint, headers=headers, verify=False)
        resp.raise_for_status()
        available = resp.json()[0]["Cash"]
        return Balance(available)

    def get_ticker(self, symbol, exchange=1) -> Ticker:
        endpoint = f"{self.url}/board"
        headers = {"X-API-KEY": self.token}
        params = {"symbol": symbol, "exchange": exchange}
        resp = requests.get(endpoint, headers=headers, params=params, verify=False)
        resp.raise_for_status()
        data = resp.json()
        timestamp = int(datetime.strptime(data["CurrentPriceTime"], "%Y-%m-%dT%H:%M:%S.%f").timestamp())
        bid = data["BidPrice"]
        ask = data["AskPrice"]
        volume = data.get("TradingVolume", 0)
        return Ticker(symbol, timestamp, bid, ask, volume)

    def send_order(self, order: Order) -> Trade:
        endpoint = f"{self.url}/sendorder"
        headers = {"X-API-KEY": self.token}
        data = {
            "Password": settings.password,
            "Symbol": order.symbol,
            "Exchange": 1,
            "SecurityType": 1,
            "Side": order.side,
            "CashMargin": 3,
            "DelivType": 2,
            "FundType": "AA",
            "Qty": order.qty,
            "Price": order.price if order.price else 0,
            "ExpireDay": 0,
            "FrontOrderType": 20 if order.price else 10,
        }
        resp = requests.post(endpoint, headers=headers, json=data, verify=False)
        resp.raise_for_status()
        order_id = resp.json()["OrderId"]
        order = self.wait_order_complete(order_id)
        if not order:
            logger.error("action=send_order error=timeout")
            raise OrderTimeoutError
        return self.trade_details(order.order_id)

    def wait_order_complete(self, order_id) -> Order:
        count = 0
        timeout_count = 5
        while True:
            order = self.get_order(order_id)
            if order.order_state == ORDER_FILLED:
                return order
            time.sleep(1)
            count += 1
            if count > timeout_count:
                return None

    def get_order(self, order_id) -> Order:
        endpoint = f"{self.url}/order"
        headers = {"X-API-KEY": self.token}
        params = {"orderId": order_id}
        resp = requests.get(endpoint, headers=headers, params=params, verify=False)
        resp.raise_for_status()
        data = resp.json()
        order = Order(
            symbol=data["Symbol"],
            side=data["Side"],
            qty=data["Qty"],
            price=data["Price"],
            order_state=data["State"],
            order_id=order_id,
        )
        return order

    def trade_details(self, order_id) -> Trade:
        endpoint = f"{self.url}/orders"
        headers = {"X-API-KEY": self.token}
        resp = requests.get(endpoint, headers=headers, verify=False)
        resp.raise_for_status()
        for t in resp.json():
            if t["OrderId"] == order_id:
                return Trade(trade_id=t["OrderId"], side=t["Side"], price=t["Price"], qty=t["Qty"])
        return None

    def get_open_trade(self) -> list:
        endpoint = f"{self.url}/orders"
        headers = {"X-API-KEY": self.token}
        resp = requests.get(endpoint, headers=headers, verify=False)
        resp.raise_for_status()
        trades_list = []
        for t in resp.json():
            if t["State"] == ORDER_FILLED:
                trades_list.append(Trade(trade_id=t["OrderId"], side=t["Side"], price=t["Price"], qty=t["Qty"]))
        return trades_list

    def trade_close(self, order_id) -> Trade:
        # kabusapiは現物取引の注文取消APIのみ。信用取引の場合は返済注文を送信
        # ここでは例として注文取消APIを使用
        endpoint = f"{self.url}/cancelorder"
        headers = {"X-API-KEY": self.token}
        data = {"Password": settings.password, "OrderId": order_id}
        resp = requests.post(endpoint, headers=headers, json=data, verify=False)
        resp.raise_for_status()
        # 取消後の状態取得
        return self.get_order(order_id)
