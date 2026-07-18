"""Yahoo Finance data importer for SQLite candle tables.

単一銘柄取り込みに加えて、東証全銘柄の低速バッチ取り込みに対応する。
"""

import argparse
import json
import re
import sys
import time
import urllib.parse
import urllib.request
from pathlib import Path

import pandas as pd

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from app.data.yahoo import save_yahoo_data_to_db

JPX_LISTING_PAGE = "https://www.jpx.co.jp/markets/statistics-equities/misc/01.html"


def _extract_codes_from_df(df: pd.DataFrame) -> list[str]:
    candidates = [
        "コード",
        "銘柄コード",
        "Code",
        "code",
    ]
    code_col = None
    for col in df.columns:
        col_str = str(col).strip()
        if col_str in candidates or any(key in col_str for key in ["コード", "Code", "code"]):
            code_col = col
            break

    if code_col is None:
        return []

    codes: list[str] = []
    for raw in df[code_col].astype(str):
        m = re.search(r"\b(\d{4})\b", raw)
        if m:
            codes.append(m.group(1))
    # 順序維持で重複削除
    return list(dict.fromkeys(codes))


def _find_jpx_list_url() -> str:
    with urllib.request.urlopen(JPX_LISTING_PAGE, timeout=30) as response:
        html = response.read().decode("utf-8", errors="ignore")

    # 上場銘柄一覧の xls/xlsx へのリンクを拾う
    matches = re.findall(r'href="([^"]+data_j\.(?:xls|xlsx))"', html)
    if not matches:
        matches = re.findall(r'href="([^"]+\.(?:xls|xlsx))"', html)
    if not matches:
        raise RuntimeError("JPXの上場銘柄一覧ファイルURLを検出できませんでした")

    for href in matches:
        abs_url = urllib.parse.urljoin(JPX_LISTING_PAGE, href)
        if "data_j" in abs_url or "listed" in abs_url.lower() or "jpx" in abs_url.lower():
            return abs_url
    return urllib.parse.urljoin(JPX_LISTING_PAGE, matches[0])


def _load_tse_codes_from_jpx() -> list[str]:
    list_url = _find_jpx_list_url()
    df = pd.read_excel(list_url, dtype=str)
    codes = _extract_codes_from_df(df)
    if not codes:
        raise RuntimeError("JPX上場銘柄一覧から銘柄コードを抽出できませんでした")
    return codes


def _load_codes_from_file(path: str) -> list[str]:
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(f"codes file not found: {path}")

    text = p.read_text(encoding="utf-8")
    codes = re.findall(r"\b\d{4}\b", text)
    return list(dict.fromkeys(codes))


def _load_resume(path: Path) -> dict:
    if not path.exists():
        return {"done": [], "failed": []}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        done = list(dict.fromkeys([str(x) for x in data.get("done", [])]))
        failed = list(dict.fromkeys([str(x) for x in data.get("failed", [])]))
        return {"done": done, "failed": failed}
    except Exception:
        return {"done": [], "failed": []}


def _save_resume(path: Path, done: list[str], failed: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "done": done,
        "failed": failed,
        "updated_at_epoch": int(time.time()),
    }
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def _run_bulk_import(
    codes: list[str],
    days: int,
    duration: str,
    market: str,
    sleep_sec: float,
    resume_path: Path,
    max_symbols: int,
) -> None:
    state = _load_resume(resume_path)
    done = list(state["done"])
    failed = [code for code in state["failed"] if code not in set(done)]
    done_set = set(done)
    failed_set = set(failed)

    targets = [c for c in codes if c not in done_set]
    if max_symbols > 0:
        targets = targets[:max_symbols]

    total = len(targets)
    print(f"bulk_import_start total_targets={total} sleep_sec={sleep_sec}")
    if total == 0:
        print("bulk_import_nothing_to_do")
        return

    for idx, code in enumerate(targets, start=1):
        try:
            saved = save_yahoo_data_to_db(
                product_code=code,
                period_days=days,
                duration=duration,
                market=market,
            )
            if saved > 0:
                if code not in done_set:
                    done.append(code)
                    done_set.add(code)
                if code in failed_set:
                    failed = [x for x in failed if x != code]
                    failed_set.discard(code)
                print(f"[{idx}/{total}] code={code} saved_rows={saved}")
            else:
                if code not in failed_set:
                    failed.append(code)
                    failed_set.add(code)
                print(f"[{idx}/{total}] code={code} no_data_or_no_insert saved_rows=0")
        except Exception as e:
            if code not in failed_set:
                failed.append(code)
                failed_set.add(code)
            print(f"[{idx}/{total}] code={code} error={e}")

        _save_resume(resume_path, done, failed)
        if sleep_sec > 0:
            time.sleep(sleep_sec)

    print(
        f"bulk_import_done success_total={len(done)} failed_total={len(failed)} resume_file={resume_path}"
    )


def main():
    parser = argparse.ArgumentParser(description="Yahoo FinanceデータをSQLiteへ保存")
    parser.add_argument("--code", type=str, help="銘柄コード (例: 7203)")
    parser.add_argument("--days", type=int, default=365, help="取得日数 (デフォルト: 365)")
    parser.add_argument("--duration", type=str, default="1d", choices=["5s", "1m", "1h", "1d"], help="時間軸")
    parser.add_argument("--market", type=str, default="T", help="市場サフィックス (例: T)")

    parser.add_argument("--all-tse", action="store_true", help="東証上場銘柄をJPX一覧から読み込んで順次取り込む")
    parser.add_argument("--codes-file", type=str, default="", help="銘柄コード一覧ファイル(4桁コードを抽出)")
    parser.add_argument("--sleep-sec", type=float, default=1.5, help="銘柄ごとの待機秒数")
    parser.add_argument(
        "--resume-file",
        type=str,
        default="results/cache/bulk_import_tse_resume.json",
        help="進捗保存ファイル",
    )
    parser.add_argument("--max-symbols", type=int, default=0, help="先頭N銘柄のみ実行(0で全件)")

    args = parser.parse_args()

    if args.all_tse or args.codes_file:
        if args.codes_file:
            codes = _load_codes_from_file(args.codes_file)
        else:
            codes = _load_tse_codes_from_jpx()

        _run_bulk_import(
            codes=codes,
            days=args.days,
            duration=args.duration,
            market=args.market,
            sleep_sec=max(0.0, float(args.sleep_sec)),
            resume_path=Path(args.resume_file),
            max_symbols=int(args.max_symbols),
        )
        return

    if not args.code:
        raise SystemExit("--code か --all-tse / --codes-file のいずれかを指定してください")

    saved = save_yahoo_data_to_db(
        product_code=args.code,
        period_days=args.days,
        duration=args.duration,
        market=args.market,
    )

    print(f"saved_rows={saved}")


if __name__ == "__main__":
    main()
