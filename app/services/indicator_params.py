from flask import Request


def _int_param(req: Request, key: str, default: int, min_value: int = 1) -> int:
    raw = req.args.get(key)
    if not raw:
        return default
    try:
        value = int(raw)
    except (TypeError, ValueError):
        return default
    return value if value >= min_value else default


def _float_param(req: Request, key: str, default: float, min_value: float = 0.0) -> float:
    raw = req.args.get(key)
    if not raw:
        return default
    try:
        value = float(raw)
    except (TypeError, ValueError):
        return default
    return value if value >= min_value else default


def apply_requested_indicators(req: Request, df) -> None:
    """Apply indicator parameters from request args to DataFrameCandle."""
    if req.args.get("sma"):
        df.add_sma(_int_param(req, "smaPeriod1", 7))
        df.add_sma(_int_param(req, "smaPeriod2", 14))
        df.add_sma(_int_param(req, "smaPeriod3", 50))

    if req.args.get("ema"):
        df.add_ema(_int_param(req, "emaPeriod1", 7))
        df.add_ema(_int_param(req, "emaPeriod2", 14))
        df.add_ema(_int_param(req, "emaPeriod3", 50))

    if req.args.get("bbands"):
        df.add_bbands(_int_param(req, "bbandsN", 20), _float_param(req, "bbandsK", 2.0))

    if req.args.get("ichimoku"):
        df.add_ichimoku()

    if req.args.get("rsi"):
        df.add_rsi(_int_param(req, "rsiPeriod", 14))

    if req.args.get("macd"):
        df.add_macd(
            _int_param(req, "macdPeriod1", 12),
            _int_param(req, "macdPeriod2", 26),
            _int_param(req, "macdPeriod3", 9),
        )
