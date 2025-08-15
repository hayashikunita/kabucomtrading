DURATION_5S = '5s'
DURATION_1M = '1m'
DURATION_1H = '1h'
DURATIONS = [DURATION_5S, DURATION_1M, DURATION_1H]

GRANULARITY_5S = '0'   # kabusapi: 0=Tick
GRANULARITY_1M = '1'   # kabusapi: 1=1分足
GRANULARITY_1H = '2'   # kabusapi: 2=日足や時間足（用途に応じて変更）

TRADE_MAP = {
    DURATION_5S: {
        'duration': DURATION_5S,
        'granularity': GRANULARITY_5S,
    },
    DURATION_1M: {
        'duration': DURATION_1M,
        'granularity': GRANULARITY_1M,
    },
    DURATION_1H: {
        'duration': DURATION_1H,
        'granularity': GRANULARITY_1H,
    }
}

BUY = '2'   # kabusapi: 2=買い
SELL = '1'  # kabusapi: 1=売り

PRODUCT_CODE_USD_JPY = '1459'  # kabusapi用の銘柄コード例（ETF: 1459）