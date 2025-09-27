import requests
import json
import pandas as pd
from typing import Any, Dict, List, Optional
from urllib.parse import urlencode
from io import StringIO

tickers = {
    'XUS': '251422/ishares-sp-500-index-etf',
    'XEF': '251421/ishares-msci-eafe-imi-index-etf',
    'XEM': '239636/ishares-msci-emerging-markets-index-etf',
    'XIU': '239832/ishares-sptsx-60-index-etf',
    'XCB': '239485/ishares-canadian-corporate-bond-index-etf'
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
    "Price",
    "Location",
    "Exchange",
    "Currency",
    "FX Rate",
    "Market Currency",
]

NUMERIC_COLUMNS = {
    "Market Value",
    "Weight (%)",
    "Notional Value",
    "Shares",
    "Price",
    "FX Rate",
}

def build_json_url(path_fragment: str, as_of_date: Optional[str] = None, use_alt: bool = False) -> str:
    numeric_id = "1464253357804" if use_alt else "1464253357814"
    base = f"https://www.blackrock.com/ca/investors/en/products/{path_fragment}/{numeric_id}.ajax"
    params = {"tab": "lookthrus", "fileType": "json"}
    if as_of_date:
        params["asOfDate"] = as_of_date
    return f"{base}?{urlencode(params)}"

def build_csv_url(path_fragment: str, ticker: str) -> str:
    base = f"https://www.blackrock.com/ca/investors/en/products/{path_fragment}/1464253357814.ajax"
    params = {"fileType": "csv", "fileName": f"{ticker}_holdings", "dataType": "fund"}
    return f"{base}?{urlencode(params)}"

def _find_list_of_dicts(obj: Any, depth: int = 0) -> Optional[List[Dict]]:
    if depth > 10:
        return None
    if isinstance(obj, list):
        if obj and all(isinstance(x, dict) for x in obj[:5]):
            return obj
        for elem in obj:
            found = _find_list_of_dicts(elem, depth + 1)
            if found:
                return found
    elif isinstance(obj, dict):
        for v in obj.values():
            found = _find_list_of_dicts(v, depth + 1)
            if found:
                return found
    return None

def _coerce_numeric(val):
    if val is None or val == "":
        return None
    if isinstance(val, (int, float)):
        return float(val)
    if isinstance(val, str):
        v = val.strip().replace(",", "").replace("%", "")
        if v == "":
            return None
        try:
            return float(v)
        except:
            return None
    return None

def _extract_from_security_subdict(item: Dict[str, Any], field: str) -> Optional[Any]:
    sec = item.get("security")
    if not isinstance(sec, dict):
        return None
    if field == "Ticker":
        return sec.get("ticker") or sec.get("symbol")
    if field == "Name":
        return sec.get("name") or sec.get("securityName")
    if field == "Sector":
        return sec.get("sector") or sec.get("gicsSector")
    if field == "Asset Class":
        return sec.get("assetClass") or sec.get("assetType")
    return None

def _strip_preamble_rows(df: pd.DataFrame) -> pd.DataFrame:
    # If a row inside data has 'Ticker' literal in Ticker column, drop all rows up to and including it
    if "Ticker" in df.columns:
        mask = df["Ticker"].astype(str) == "Ticker"
        if mask.any():
            first_idx = df.index[mask][0]
            df = df.loc[first_idx + 1 :].copy()
            df.reset_index(drop=True, inplace=True)
    return df

def holdings_from_json_obj(obj: Any) -> Optional[pd.DataFrame]:
    holdings_list = _find_list_of_dicts(obj)
    if not holdings_list:
        return None
    rows = []
    for item in holdings_list:
        if not isinstance(item, dict):
            continue
        row = {}
        for col in TARGET_COLUMNS:
            val = item.get(col)
            if (val is None or val == "") and col in {"Ticker", "Name", "Sector", "Asset Class"}:
                val = _extract_from_security_subdict(item, col)
            if col == "Weight (%)":
                num = _coerce_numeric(val)
                if num is not None and 0 <= num <= 1:
                    num *= 100
                row[col] = num
            elif col in NUMERIC_COLUMNS:
                row[col] = _coerce_numeric(val)
            else:
                if isinstance(val, (int, float)):
                    val = str(val)
                row[col] = val
        rows.append(row)
    if not rows:
        return None
    df = pd.DataFrame(rows)
    for c in TARGET_COLUMNS:
        if c not in df:
            df[c] = None
    df = df[TARGET_COLUMNS]
    df = _strip_preamble_rows(df)
    return df

def try_fetch_json(url: str) -> Optional[Any]:
    resp = requests.get(url, headers=HEADERS, timeout=30)
    resp.raise_for_status()
    try:
        return resp.json()
    except:
        text = resp.content.decode("utf-8-sig", errors="replace")
        return json.loads(text)

def _parse_numeric_series(series: pd.Series) -> pd.Series:
    return pd.to_numeric(
        series.astype(str)
              .str.replace(",", "", regex=False)
              .str.replace("%", "", regex=False)
              .str.strip(),
        errors="coerce"
    )

def _load_csv_exact(csv_text: str) -> pd.DataFrame:
    lines = csv_text.splitlines()
    header_idx = None
    for i, ln in enumerate(lines):
        if ln.startswith("Ticker,"):
            header_idx = i
            break
    if header_idx is not None:
        csv_text = "\n".join(lines[header_idx:])
    df = pd.read_csv(StringIO(csv_text))
    missing = [c for c in TARGET_COLUMNS if c not in df.columns]
    if missing:
        raise RuntimeError(f"CSV missing expected columns: {missing}")
    df = df[TARGET_COLUMNS].copy()

    # Remove preamble rows if an embedded header line exists
    df = _strip_preamble_rows(df)

    for c in NUMERIC_COLUMNS:
        df[c] = _parse_numeric_series(df[c])
    if df["Weight (%)"].notna().any():
        max_w = df["Weight (%)"].max()
        if max_w is not None and max_w <= 1.5:
            df["Weight (%)"] = df["Weight (%)"] * 100.0
    return df

def fetch_holdings(ticker: str, as_of_date: Optional[str] = None) -> pd.DataFrame:
    path_fragment = tickers[ticker]
    for use_alt in (False, True):
        try:
            url = build_json_url(path_fragment, as_of_date, use_alt=use_alt)
            data = try_fetch_json(url)
            df_json = holdings_from_json_obj(data)
            if df_json is not None and not df_json.empty:
                return df_json
        except Exception:
            pass
    csv_url = build_csv_url(path_fragment, ticker)
    resp = requests.get(csv_url, headers=HEADERS, timeout=30)
    resp.raise_for_status()
    csv_text = resp.content.decode("utf-8-sig", errors="replace")
    return _load_csv_exact(csv_text)

if __name__ == "__main__":
    for tk in tickers:
        print(f"\n=== {tk} ===")
        try:
            df = fetch_holdings(tk)
            print(df.head())
            print("rows:", len(df))
        except Exception as e:
            print("Failed:", e)
