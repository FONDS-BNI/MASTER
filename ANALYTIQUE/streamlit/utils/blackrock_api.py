import threading
import pandas as pd
import requests
from concurrent.futures import ThreadPoolExecutor, as_completed
from functools import lru_cache
from io import StringIO
from typing import Any, Dict, List, Optional, Iterable
from urllib.parse import urlencode

# ---------------------------------------------------------------------
# Static data
# ---------------------------------------------------------------------
tickers = {
    'XBB': '239493/ishares-canadian-universe-bond-index-etf',
    'XCB': '239485/ishares-canadian-corporate-bond-index-etf',
    'XEF': '251421/ishares-msci-eafe-imi-index-etf',
    'XEM': '239636/ishares-msci-emerging-markets-index-etf',
    'XHY': '239858/ishares-us-high-yield-bond-index-etf-cadhedged-fund',
    'XIG': '239859/ishares-us-ig-corporate-bond-index-etf-cadhedged-fund',
    'XIU': '239832/ishares-sptsx-60-index-etf',
    'XSB': '239491/ishares-canadian-short-term-bond-index-etf',
    'XUS': '251422/ishares-sp-500-index-etf',
}
# Here's hwo to get the data above
# 1. Go to https://www.blackrock.com/ca.
# 2. Search for an ETF (e.g., XIU).
# 3. Right click anywhere on the ETF page and select "Inspect" to open developer tools.
# 4. In the developer tools, go to the "Network" tab.
# 5. May need to refresh the page (F5 or Ctrl+R).
# 6. In the "Network" tab, look for requests that contain "ajax" in the "Name" column.
# 7. Click on one of these requests to see its details, including the URL path fragment in "Headers".
# 8. Copy the path fragment which is the part after /products/ and before the numeric ID (e.g., 1464253357814).

ETF_NAME_MAP: Dict[str, str] = {
    tk: frag.split('/', 1)[1].replace('-', ' ')
    for tk, frag in tickers.items()
}

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:122.0) "
        "Gecko/20100101 Firefox/122.0"
    )
}

TARGET_COLUMNS = [
    "Ticker",
    "Name",
    "Sector",
    "Asset Class",
    "Market Value",
    "Weight (%)",
    "Notional Value",
    "Shares",
    "Par Value",
    "Price",
    "Location",
    "Exchange",
    "Currency",
    "Duration",
    "FX Rate",
    "Maturity",
    "Coupon (%)",
    "Market Currency",
    "Effective Date",
]

NUMERIC_COLUMNS = {
    "Market Value",
    "Weight (%)",
    "Notional Value",
    "Shares",
    "Par Value",
    "Price",
    "Duration",
    "FX Rate",
    "Maturity",
    "Coupon (%)",
}

# ---------------------------------------------------------------------
# Optimized session handling
# ---------------------------------------------------------------------
_session_lock = threading.Lock()
_global_session: Optional[requests.Session] = None


def get_session() -> requests.Session:
    global _global_session
    if _global_session is None:
        with _session_lock:
            if _global_session is None:
                s = requests.Session()
                adapter = requests.adapters.HTTPAdapter(
                    pool_connections=32,
                    pool_maxsize=32,
                    max_retries=2
                )
                s.mount("https://", adapter)
                s.mount("http://", adapter)
                s.headers.update(HEADERS)
                _global_session = s
    return _global_session


# ---------------------------------------------------------------------
# URL builders
# ---------------------------------------------------------------------
def build_csv_url(path_fragment: str, ticker: str, as_of_date: Optional[str] = None) -> str:
    base = f"https://www.blackrock.com/ca/investors/en/products/{path_fragment}/1464253357814.ajax"
    params = {
        "fileType": "csv",
        "fileName": f"{ticker}_holdings",
        "dataType": "fund",
    }
    if as_of_date:
        params["asOfDate"] = as_of_date
    return f"{base}?{urlencode(params)}"


# ---------------------------------------------------------------------
# Download layer with caching
# ---------------------------------------------------------------------
@lru_cache(maxsize=256)
def _download_text(url: str) -> str:
    resp = get_session().get(url, timeout=30)
    resp.raise_for_status()
    return resp.content.decode("utf-8-sig", errors="replace")


# ---------------------------------------------------------------------
# Parsing helpers
# ---------------------------------------------------------------------
def _coerce_numeric(val):
    if val in (None, ""):
        return None
    if isinstance(val, (int, float)):
        return float(val)
    if isinstance(val, str):
        v = val.strip().replace(",", "").replace("%", "")
        if not v:
            return None
        try:
            return float(v)
        except ValueError:
            return None
    return None


def _strip_preamble_rows(df: pd.DataFrame) -> pd.DataFrame:
    if "Ticker" in df.columns:
        mask = df["Ticker"].astype(str) == "Ticker"
        if mask.any():
            first_idx = df.index[mask][0]
            df = df.loc[first_idx + 1 :].copy()
            df.reset_index(drop=True, inplace=True)
    return df


def _parse_numeric_series(series: pd.Series) -> pd.Series:
    s = series.astype(str)
    if not (s.str.contains(",").any() or s.str.contains("%").any()):
        return pd.to_numeric(s, errors="coerce")
    s = s.str.replace(",", "", regex=False).str.replace("%", "", regex=False).str.strip()
    return pd.to_numeric(s, errors="coerce")


def _load_csv_exact(csv_text: str) -> pd.DataFrame:
    # Find header line
    lines = csv_text.splitlines()
    header_idx = None
    for i, ln in enumerate(lines):
        if ln.startswith("Ticker,"):
            header_idx = i
            break
    if header_idx is not None:
        csv_text = "\n".join(lines[header_idx:])
    df = pd.read_csv(StringIO(csv_text))

    # Normalize header spacing / stray BOM
    normalized_map = {c.strip(): c for c in df.columns}
    for target in TARGET_COLUMNS:
        if target not in df.columns and target.strip() in normalized_map:
            df.rename(columns={normalized_map[target.strip()]: target}, inplace=True)

    # Add any missing expected columns as empty (requested change)
    for col in TARGET_COLUMNS:
        if col not in df.columns:
            df[col] = pd.NA

    # Reorder (safe because all now exist)
    df = df[TARGET_COLUMNS].copy()

    df = _strip_preamble_rows(df)

    for c in NUMERIC_COLUMNS:
        df[c] = _parse_numeric_series(df[c])

    # Scale weight if in 0-1 range
    if df["Weight (%)"].notna().any():
        max_w = df["Weight (%)"].max()
        if max_w is not None and max_w <= 1.5:
            df["Weight (%)"] = df["Weight (%)"] * 100.0

    return df


def _add_parent_etf_columns(df: pd.DataFrame, ticker: str) -> pd.DataFrame:
    df = df.copy()
    df["ETF Ticker"] = ticker
    df["ETF Name"] = ETF_NAME_MAP.get(ticker, ticker)
    return df


# ---------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------
def fetch_holdings(ticker: str, as_of_date: Optional[str] = None) -> pd.DataFrame:
    path_fragment = tickers[ticker]
    csv_url = build_csv_url(path_fragment, ticker, as_of_date=as_of_date)
    csv_text = _download_text(csv_url)
    df = _load_csv_exact(csv_text)
    return _add_parent_etf_columns(df, ticker)


def fetch_all_holdings(
    ticker_list: Optional[Iterable[str]] = None,
    as_of_date: Optional[str] = None,
    ignore_errors: bool = True,
    max_workers: int = 8
) -> pd.DataFrame:
    if ticker_list is None:
        ticker_list = list(tickers.keys())
    ticker_list = list(ticker_list)

    results: List[pd.DataFrame] = []
    errors: Dict[str, Exception] = {}

    with ThreadPoolExecutor(max_workers=min(max_workers, len(ticker_list) or 1)) as ex:
        future_map = {
            ex.submit(fetch_holdings, tk, as_of_date): tk for tk in ticker_list
        }
        for fut in as_completed(future_map):
            tk = future_map[fut]
            try:
                df = fut.result()
                if not df.empty:
                    results.append(df)
            except Exception as e:
                if not ignore_errors:
                    raise
                errors[tk] = e

    if not results:
        raise RuntimeError(f"No holdings fetched. Errors: { {k: str(v) for k,v in errors.items()} }")

    return pd.concat(results, ignore_index=True)


# ---------------------------------------------------------------------
# Script usage
# ---------------------------------------------------------------------
def _demo_individual():
    for tk in tickers:
        print(f"\n=== {tk} ===")
        try:
            df = fetch_holdings(tk)
            print(df.head(3))
            print("rows:", len(df))
        except Exception as e:
            print("Failed:", e)


def _demo_all():
    print("\n=== ALL TOGETHER (concurrent) ===")
    try:
        all_df = fetch_all_holdings()
        print(all_df.head(5))
        print("total rows:", len(all_df))
        print("etfs included:", all_df['ETF Ticker'].nunique())
    except Exception as e:
        print("Failed fetching all:", e)


if __name__ == "__main__":
    _demo_individual()
    _demo_all()
