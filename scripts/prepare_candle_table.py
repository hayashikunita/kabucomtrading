"""Create/prepare candle table for a symbol and duration."""

import argparse

from app.models.candle import factory_candle_class


def main():
    parser = argparse.ArgumentParser(description="銘柄・時間軸に対応するローソク足テーブルを作成")
    parser.add_argument("--code", required=True, help="銘柄コード (例: 7203)")
    parser.add_argument("--duration", default="1d", choices=["5s", "1m", "1h", "1d"], help="時間軸")
    args = parser.parse_args()

    cls = factory_candle_class(args.code, args.duration)
    print(f"prepared_table={cls.__tablename__}")


if __name__ == "__main__":
    main()
