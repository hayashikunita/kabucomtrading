import json
import time
from collections import deque
from pathlib import Path

from flask import Flask, Response, jsonify, render_template, request, stream_with_context

import constants
import settings
from app.data.yahoo import fetch_yahoo_data, save_yahoo_data_to_db
from app.models.dfcandle import DataFrameCandle
from app.services.indicator_params import apply_requested_indicators

app = Flask(__name__, template_folder="../views")
BASE_DIR = Path(__file__).resolve().parents[2]
TERMINAL_MONITOR_DIRS = [
    BASE_DIR / "results" / "logs",
    BASE_DIR / "logs",
    BASE_DIR / "results" / "cache",
]


def _normalize_line_count(raw_value: str | None, default: int = 200, maximum: int = 2000) -> int:
    try:
        value = int(raw_value) if raw_value is not None else default
    except ValueError:
        return default
    return max(1, min(value, maximum))


def _is_path_allowed(path: Path) -> bool:
    try:
        resolved_path = path.resolve()
        for monitor_dir in TERMINAL_MONITOR_DIRS:
            if monitor_dir.exists() and resolved_path.is_relative_to(monitor_dir.resolve()):
                return resolved_path.is_file()
    except Exception:
        return False
    return False


def _resolve_target_file(file_param: str | None) -> Path | None:
    if not file_param:
        return None
    target = (BASE_DIR / file_param).resolve()
    if not _is_path_allowed(target):
        return None
    return target


def _discover_monitor_files() -> list[str]:
    patterns = ("*.log", "*.txt", "*.out", "*.json")
    discovered: list[str] = []
    for monitor_dir in TERMINAL_MONITOR_DIRS:
        if not monitor_dir.exists():
            continue
        for pattern in patterns:
            for path in monitor_dir.glob(pattern):
                if path.is_file():
                    discovered.append(path.relative_to(BASE_DIR).as_posix())
    discovered.sort()
    return discovered


def _read_tail_lines(path: Path, line_count: int) -> list[str]:
    with path.open("r", encoding="utf-8", errors="replace") as handle:
        return list(deque(handle, maxlen=line_count))


@app.teardown_appcontext
def remove_session(ex=None):
    from app.models.base import Session

    Session.remove()


@app.route("/")
def index():
    return render_template("./chart.html")


@app.route("/terminal")
def terminal_monitor():
    return render_template("./terminal.html")


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


@app.route("/api/terminal/files", methods=["GET"])
def api_terminal_files():
    return jsonify({"files": _discover_monitor_files()}), 200


@app.route("/api/terminal/tail", methods=["GET"])
def api_terminal_tail():
    target = _resolve_target_file(request.args.get("file"))
    if target is None:
        return jsonify({"error": "invalid file path"}), 400

    lines = _normalize_line_count(request.args.get("lines"), default=200, maximum=2000)
    try:
        tail_lines = _read_tail_lines(target, lines)
    except OSError as e:
        return jsonify({"error": str(e)}), 500

    try:
        position = target.stat().st_size
    except OSError:
        position = 0

    return jsonify(
        {
            "file": target.relative_to(BASE_DIR).as_posix(),
            "lines": [line.rstrip("\n") for line in tail_lines],
            "position": position,
        }
    ), 200


@app.route("/api/terminal/stream", methods=["GET"])
def api_terminal_stream():
    target = _resolve_target_file(request.args.get("file"))
    if target is None:
        return jsonify({"error": "invalid file path"}), 400

    start_pos = request.args.get("position")
    try:
        cursor = int(start_pos) if start_pos is not None else target.stat().st_size
    except (ValueError, OSError):
        cursor = 0
    cursor = max(0, cursor)

    @stream_with_context
    def generate():
        nonlocal cursor
        while True:
            if not target.exists():
                yield "event: error\ndata: file deleted\n\n"
                return

            try:
                current_size = target.stat().st_size
            except OSError:
                current_size = cursor

            if cursor > current_size:
                cursor = 0

            chunk = ""
            try:
                with target.open("r", encoding="utf-8", errors="replace") as handle:
                    handle.seek(cursor)
                    chunk = handle.read()
                    cursor = handle.tell()
            except OSError as e:
                yield f"event: error\ndata: {json.dumps(str(e), ensure_ascii=False)}\n\n"
                return

            if chunk:
                payload = {"text": chunk, "position": cursor}
                yield f"data: {json.dumps(payload, ensure_ascii=False)}\n\n"
            else:
                yield ": keepalive\n\n"
            time.sleep(1)

    return Response(generate(), mimetype="text/event-stream")


def start():
    # app.run(host='127.0.0.1', port=settings.web_port, threaded=True)
    app.run(host="0.0.0.0", port=settings.web_port, threaded=True)
