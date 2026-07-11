import os
from pathlib import Path

from flask import Flask, jsonify, render_template, request

import constants
import settings
from app.data.yahoo import fetch_yahoo_data, save_yahoo_data_to_db
from app.models.dfcandle import DataFrameCandle
from app.services.indicator_params import apply_requested_indicators

app = Flask(__name__, template_folder="../views")


@app.teardown_appcontext
def remove_session(ex=None):
    from app.models.base import Session

    Session.remove()


@app.route("/")
def index():
    return render_template("./chart.html")


@app.route("/api/candle/", methods=["GET"])
def api_make_handler():
    product_code = request.args.get("product_code")
    if not product_code:
        return jsonify({"error": "No product_code params"}), 400

    limit_str = request.args.get("limit")
    limit = 1000
    if limit_str:
        limit = int(limit_str)

    if limit < 0 or limit > 1000:
        limit = 1000

    duration = request.args.get("duration")
    if not duration:
        duration = constants.DURATION_1M
    duration_time = constants.TRADE_MAP[duration]["duration"]
    df = DataFrameCandle(product_code, duration_time)
    df.set_all_candles(limit)

    apply_requested_indicators(request, df)

    events = request.args.get("events")
    if events:
        if settings.back_test:
            from app.controllers.streamdata import stream

            df.events = stream.ai.signal_events
        else:
            df.add_events(df.candles[0].time)
    return jsonify(df.value), 200


@app.route("/api/yahoo/candle/", methods=["GET"])
def api_yahoo_handler():
    """Yahoo Financeからデータを取得するエンドポイント"""
    product_code = request.args.get("product_code")
    if not product_code:
        return jsonify({"error": "No product_code params"}), 400

    limit_str = request.args.get("limit")
    limit = 365
    if limit_str:
        limit = int(limit_str)

    if limit < 0 or limit > 1000:
        limit = 365

    duration = request.args.get("duration")
    if not duration:
        duration = constants.DURATION_1M
    duration_time = constants.TRADE_MAP.get(duration, {}).get("duration", constants.DURATION_1M)

    # Yahoo Financeからデータ取得
    yahoo_candles = fetch_yahoo_data(product_code=product_code, period_days=limit, duration=duration_time, market="T")

    if not yahoo_candles:
        return jsonify({"error": "No data from Yahoo Finance"}), 404

    # Create DataFrameCandle object (same format as backtest)
    df = DataFrameCandle(product_code, duration_time)

    # Convert Yahoo Finance data to candle list
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

    df.candles = [SimpleCandle(c) for c in yahoo_candles]

    apply_requested_indicators(request, df)

    return jsonify(df.value), 200


@app.route("/api/backtest/results/", methods=["GET"])
def api_backtest_results():
    """バックテスト結果を取得するエンドポイント"""
    import json

    results_file = Path(settings.backtest_results_file)
    legacy_file = Path("backtest_results.json")

    if not results_file.exists() and legacy_file.exists():
        results_file = legacy_file

    if not results_file.exists():
        return jsonify({"error": "No backtest results found"}), 404

    try:
        with results_file.open("r", encoding="utf-8") as f:
            results = json.load(f)
        return jsonify(results), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500


def start():
    # app.run(host='127.0.0.1', port=settings.web_port, threaded=True)
    app.run(host="0.0.0.0", port=settings.web_port, threaded=True)
