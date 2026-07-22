"""Yahoo Financeの財務諸表を一括取得してキャッシュDBへ保存するCLI。"""

import argparse
import json
import re
import sqlite3
import sys
import time
import urllib.parse
import urllib.request
from io import StringIO
from pathlib import Path

import pandas as pd
import yfinance as yf

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

JPX_LISTING_PAGE = "https://www.jpx.co.jp/markets/statistics-equities/misc/01.html"
DEFAULT_CACHE_DB = ROOT_DIR / "stockdata.sql"


def _ensure_fin_cache_table(db_path: Path) -> None:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(db_path) as con:
        con.execute(
            """
            CREATE TABLE IF NOT EXISTS financial_cache (
                symbol TEXT PRIMARY KEY,
                updated_at TEXT NOT NULL,
                info_json TEXT NOT NULL,
                financials_json TEXT NOT NULL,
                balance_sheet_json TEXT NOT NULL,
                cashflow_json TEXT NOT NULL
            )
            """
        )


def _df_to_json(df: pd.DataFrame | None) -> str:
    if df is None:
        return ""
    try:
        return df.to_json(orient="split", date_format="iso")
    except Exception:
        return ""


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


def _extract_codes_from_df(df: pd.DataFrame) -> list[str]:
    candidates = ["コード", "銘柄コード", "Code", "code"]
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
    return list(dict.fromkeys(codes))


def _find_jpx_list_url() -> str:
    with urllib.request.urlopen(JPX_LISTING_PAGE, timeout=30) as response:
        html = response.read().decode("utf-8", errors="ignore")

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


def _build_symbol(code: str, market: str) -> str:
    c = str(code).strip()
    if c.startswith("^") or "." in c:
        return c
    if market:
        return f"{c}.{market}"
    return c


def _save_one_symbol_to_cache(symbol: str, db_path: Path) -> None:
    ticker = yf.Ticker(symbol)
    info = ticker.info or {}
    financials = ticker.financials
    balance_sheet = ticker.balance_sheet
    cashflow = ticker.cashflow

    with sqlite3.connect(db_path) as con:
        con.execute(
            """
            INSERT INTO financial_cache (
                symbol, updated_at, info_json, financials_json, balance_sheet_json, cashflow_json
            ) VALUES (?, ?, ?, ?, ?, ?)
            ON CONFLICT(symbol) DO UPDATE SET
                updated_at=excluded.updated_at,
                info_json=excluded.info_json,
                financials_json=excluded.financials_json,
                balance_sheet_json=excluded.balance_sheet_json,
                cashflow_json=excluded.cashflow_json
            """,
            (
                symbol,
                pd.Timestamp.now(tz="UTC").isoformat(),
                json.dumps(info, ensure_ascii=False, default=str),
                _df_to_json(financials),
                _df_to_json(balance_sheet),
                _df_to_json(cashflow),
            ),
        )


def _run_bulk_fetch(
    symbols: list[str],
    db_path: Path,
    sleep_sec: float,
    resume_path: Path,
    max_symbols: int,
) -> None:
    _ensure_fin_cache_table(db_path)

    state = _load_resume(resume_path)
    done = list(state["done"])
    failed = [code for code in state["failed"] if code not in set(done)]
    done_set = set(done)
    failed_set = set(failed)

    targets = [s for s in symbols if s not in done_set]
    if max_symbols > 0:
        targets = targets[:max_symbols]

    total = len(targets)
    print(f"bulk_financial_fetch_start total_targets={total} sleep_sec={sleep_sec}")
    if total == 0:
        print("bulk_financial_fetch_nothing_to_do")
        return

    for idx, symbol in enumerate(targets, start=1):
        try:
            _save_one_symbol_to_cache(symbol, db_path)
            if symbol not in done_set:
                done.append(symbol)
                done_set.add(symbol)
            if symbol in failed_set:
                failed = [x for x in failed if x != symbol]
                failed_set.discard(symbol)
            print(f"[{idx}/{total}] symbol={symbol} status=ok")
        except Exception as e:
            if symbol not in failed_set:
                failed.append(symbol)
                failed_set.add(symbol)
            print(f"[{idx}/{total}] symbol={symbol} status=error error={e}")

        _save_resume(resume_path, done, failed)
        if sleep_sec > 0:
            time.sleep(sleep_sec)

    print(
        f"bulk_financial_fetch_done success_total={len(done)} failed_total={len(failed)} resume_file={resume_path} cache_db={db_path}"
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="Yahoo Finance財務諸表を一括取得してキャッシュDBへ保存")
    parser.add_argument("--symbol", type=str, help="単一銘柄シンボル (例: 7203.T, ^N225)")
    parser.add_argument("--code", type=str, help="単一銘柄コード (例: 7203)")
    parser.add_argument("--market", type=str, default="T", help="市場サフィックス (例: T)")

    parser.add_argument("--all-tse", action="store_true", help="JPX上場銘柄を自動取得して実行")
    parser.add_argument("--codes-file", type=str, default="", help="銘柄コード一覧ファイル")
    parser.add_argument("--sleep-sec", type=float, default=1.5, help="銘柄ごとの待機秒数")
    parser.add_argument("--max-symbols", type=int, default=0, help="先頭N銘柄のみ実行(0で全件)")
    parser.add_argument(
        "--resume-file",
        type=str,
        default="results/cache/bulk_financial_fetch_resume.json",
        help="進捗保存ファイル",
    )
    parser.add_argument(
        "--cache-db",
        type=str,
        default=str(DEFAULT_CACHE_DB),
        help="保存先キャッシュDBファイル",
    )

    args = parser.parse_args()

    db_path = Path(args.cache_db)
    resume_path = Path(args.resume_file)

    if args.all_tse or args.codes_file:
        if args.codes_file:
            codes = _load_codes_from_file(args.codes_file)
        else:
            codes = _load_tse_codes_from_jpx()
        symbols = [_build_symbol(code, args.market) for code in codes]
        _run_bulk_fetch(
            symbols=symbols,
            db_path=db_path,
            sleep_sec=max(0.0, float(args.sleep_sec)),
            resume_path=resume_path,
            max_symbols=int(args.max_symbols),
        )
        return

    if args.symbol:
        symbol = args.symbol.strip()
    elif args.code:
        symbol = _build_symbol(args.code, args.market)
    else:
        raise SystemExit("--symbol / --code / --all-tse / --codes-file のいずれかを指定してください")

    _ensure_fin_cache_table(db_path)
    _save_one_symbol_to_cache(symbol, db_path)
    print(f"saved_financials symbol={symbol} cache_db={db_path}")


if __name__ == "__main__":
    main()
