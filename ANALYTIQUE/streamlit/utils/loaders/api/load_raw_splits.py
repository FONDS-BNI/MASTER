import streamlit as st
import pandas as pd

def load_splits(tickers: list[str]) -> pd.DataFrame:
    try:
        from yahoo_api import YahooAPI
        raw = YahooAPI().get_yahoo_data(tickers, metric=['splits'])
    except Exception:
        print("Warning: could not load splits from Yahoo API")
        return pd.DataFrame()
    if raw is None or raw.empty:
        return pd.DataFrame()
    if isinstance(raw.columns, pd.MultiIndex):
        raw.columns = raw.columns.get_level_values(0)
    events = []
    for ticker in raw.columns:
        s = raw[ticker].dropna()
        changed = s[(s != 1) & (s.ne(s.shift()))]
        if not changed.empty:
            events.append(pd.DataFrame({'Ticker': ticker, 'SplitFactor': changed.values}, index=changed.index))
    return pd.concat(events).sort_index() if events else pd.DataFrame()
