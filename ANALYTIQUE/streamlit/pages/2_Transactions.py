import streamlit as st
import pandas as pd
from pathlib import Path
from datetime import date
from functools import lru_cache

# -------------------- Constants --------------------
DATA_DIR = Path(__file__).parent.parent.parent / "performance/data"
TRANSACTION_FILE = DATA_DIR / "stock_final.xlsx"
TICKERS = ['XBB.TO', 'XCB.TO', 'XEF.TO', 'XEM.TO', 'XHY.TO', 'XIG.TO', 'XIU.TO', 'XSB.TO', 'XUS.TO']

st.set_page_config(
    page_title="Transactions & Holdings", 
    layout="wide"
)

# -------------------- Data Loading --------------------
@st.cache_data(show_spinner=False)
def load_transactions(path: Path) -> pd.DataFrame:
    if not path.exists():
        return pd.DataFrame()
    df = pd.read_excel(path, sheet_name="Transactions", usecols=range(5), index_col=0)
    df.index = pd.to_datetime(df.index).tz_localize(None)
    if 'Date' in df.columns:
        df['Date'] = pd.to_datetime(df['Date']).dt.tz_localize(None)
    if {'Quantity', 'Price'}.issubset(df.columns):
        df['Value'] = df['Quantity'] * df['Price']
    return df.sort_index()

@st.cache_data(show_spinner=False)
def get_trading_days(start: pd.Timestamp, end: pd.Timestamp) -> pd.DatetimeIndex:
    return pd.bdate_range(start=start.normalize(), end=end.normalize())

# -------------------- Split Loader --------------------
@st.cache_data(ttl=3600, show_spinner=False)
def load_splits(tickers: list[str]) -> pd.DataFrame:
    try:
        from yahoo_api import YahooAPI
        raw = YahooAPI().get_yahoo_data(tickers, metric=['splits'])
    except Exception:
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

# -------------------- Holdings Builder (optimized) --------------------
@st.cache_data(show_spinner=False)
def _pre_aggregate(df: pd.DataFrame) -> pd.DataFrame:
    # Aggregate all transactions to daily net quantity per ticker
    g = (df.groupby([df.index.date, 'Ticker'])['Quantity']
           .sum()
           .unstack(fill_value=0.0))
    g.index = pd.to_datetime(g.index)
    return g.sort_index()

@st.cache_data(show_spinner=False)
def build_holdings(df: pd.DataFrame,
                   start: pd.Timestamp,
                   end: pd.Timestamp,
                   fund: str) -> pd.DataFrame:
    if df.empty:
        return pd.DataFrame()

    if fund == "Strategic":
        work = df[df['Type'] == 'Strategic']
    elif fund == "Tactic":
        work = df[df['Type'] == 'Tactic']
    else:
        work = df

    if work.empty or not {'Ticker', 'Quantity'}.issubset(work.columns):
        return pd.DataFrame()

    grouped = _pre_aggregate(work)
    first_date = grouped.index.min().normalize()
    trading_days = get_trading_days(first_date, end)
    grouped = grouped.reindex(trading_days, fill_value=0.0)
    holdings_full = grouped.cumsum()
    out = holdings_full.loc[start:end]

    return out

# -------------------- Sidebar / Filters --------------------
def sidebar_filters(df: pd.DataFrame) -> dict:
    st.sidebar.header("Filters")
    if df.empty:
        return {}
    min_date = df.index.min().date()
    max_date = df.index.max().date()

    with st.sidebar.container(border=True):
        mode = st.radio(
            "Date range",
            ["All", "YTD", "1Y", "3Y", "5Y", "Custom"],
            index=5
        )

        manual = st.date_input(
            "Custom range",
            value=[min_date, max_date],
            min_value=min_date,
            max_value=max_date
        )

    if mode == "All":
        start_date, end_date = min_date, max_date
    elif mode == "YTD":
        start_date, end_date = date(max_date.year, 1, 1), max_date
    elif mode == "1Y":
        start_candidate = (pd.Timestamp(max_date) - pd.DateOffset(years=1)).date()
        start_date, end_date = max(start_candidate, min_date), max_date
    elif mode == "3Y":
        start_candidate = (pd.Timestamp(max_date) - pd.DateOffset(years=3)).date()
        start_date, end_date = max(start_candidate, min_date), max_date
    elif mode == "5Y":
        start_candidate = (pd.Timestamp(max_date) - pd.DateOffset(years=5)).date()
        start_date, end_date = max(start_candidate, min_date), max_date
    else:
        if len(manual) == 2:
            start_date, end_date = manual
        else:
            start_date, end_date = min_date, max_date

    if start_date > end_date:
        start_date, end_date = end_date, start_date

    with st.sidebar.container(border=True):
        fund = st.radio("Fund", ["Global", "Strategic", "Tactic"])

    return {
        "start": pd.to_datetime(start_date),
        "end": pd.to_datetime(end_date),
        "fund": fund
    }

# -------------------- Small Helpers --------------------
def _fund_filter(df: pd.DataFrame, fund: str) -> pd.DataFrame:
    if fund == "Strategic":
        return df[df['Type'] == 'Strategic']
    if fund == "Tactic":
        return df[df['Type'] == 'Tactic']
    return df

# -------------------- Display --------------------
def render_page(df: pd.DataFrame, f: dict):
    start, end, fund = f["start"], f["end"], f["fund"]
    tx = _fund_filter(df, fund)
    tx = tx.loc[(tx.index >= start) & (tx.index <= end)].copy()

    st.title(f"{fund} Fund Overview")
    st.caption(f"Date range: {start.date()} → {end.date()}")
    
    tabs = st.tabs(["Transactions", "Holdings", "Splits"])
    # Transactions
    with tabs[0]:
        st.caption(f"Rows: {len(tx)} — Columns: {len(tx.columns)}")
        st.dataframe(tx, use_container_width=True, height=500)
        
    # Holdings
    with tabs[1]:
        holdings = build_holdings(df, start, end, fund)
        st.caption(f"Rows: {len(holdings)} — Columns: {len(holdings.columns)}")
        st.dataframe(holdings, use_container_width=True, height=500)

    # Splits
    with tabs[2]:
        splits = load_splits(TICKERS)
        if splits.empty:
            st.info("No split data available.")
        else:
            s_filtered = splits.loc[(splits.index >= start) & (splits.index <= end)]
            if s_filtered.empty:
                st.info("No splits in selected range.")
            else:
                st.caption(f"Rows: {len(s_filtered)} — Columns: {len(s_filtered.columns)}")
                st.dataframe(s_filtered, use_container_width=True)

# -------------------- Main --------------------
def main():
    df = load_transactions(TRANSACTION_FILE)
    if df.empty:
        st.error("No transaction data found.")
        return
    filters = sidebar_filters(df)
    if not filters:
        return
    render_page(df, filters)

    # Minimal custom styling
    st.markdown("""
    <style>
    section[data-testid="stSidebar"] {width: 330px !important;}
    .stMetric label {font-size:0.75rem;}
    </style>
    """, unsafe_allow_html=True)

if __name__ == "__main__":
    main()
