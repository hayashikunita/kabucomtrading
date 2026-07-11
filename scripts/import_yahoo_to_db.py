"""Yahoo Finance data importer for SQLite candle tables."""

import argparse

from app.data.yahoo import save_yahoo_data_to_db


def main():
    parser = argparse.ArgumentParser(description="Yahoo FinanceデータをSQLiteへ保存")
    parser.add_argument("--code", type=str, required=True, help="銘柄コード (例: 7203)")
    parser.add_argument("--days", type=int, default=365, help="取得日数 (デフォルト: 365)")
    parser.add_argument("--duration", type=str, default="1d", choices=["5s", "1m", "1h", "1d"], help="時間軸")
    parser.add_argument("--market", type=str, default="T", help="市場サフィックス (例: T)")

    args = parser.parse_args()

    saved = save_yahoo_data_to_db(
        product_code=args.code,
        period_days=args.days,
        duration=args.duration,
        market=args.market,
    )

    print(f"saved_rows={saved}")


if __name__ == "__main__":
    main()
