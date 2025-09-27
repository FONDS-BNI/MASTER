from __future__ import annotations
import streamlit as st
import pandas as pd
from datetime import date

import config
from utils.loaders.load_raw_transactions import load_transactions
from utils.loaders.api.load_raw_splits import load_splits
from utils.transforms.compute_holdings import build_holdings as compute_holdings


# -------------------- Page Config --------------------
st.set_page_config(page_title="Transactions & Holdings", layout="wide")


# -------------------- CACHED UTILITIES --------------------
@st.cache_data(show_spinner=False)
def get_trading_days(start: pd.Timestamp, end: pd.Timestamp) -> pd.DatetimeIndex:
    """
    Return business days between start and end (inclusive).
    Cached to avoid recomputation across reruns.
    """
    start = pd.to_datetime(start).normalize()
    end = pd.to_datetime(end).normalize()
    return pd.bdate_range(start=start, end=end)


# -------------------- Sidebar / Filters --------------------
def sidebar_filters(df: pd.DataFrame) -> dict:
    """
    Render filters in the sidebar and return filter dict:
    {"start": Timestamp, "end": Timestamp, "fund": str}
    """
    st.sidebar.header("Filters")
    if df.empty:
        st.sidebar.info("No data available.")
        return {}

    min_date = df.index.min().date()
    max_date = df.index.max().date()

    with st.sidebar.expander("Date range", expanded=True):
        mode = st.radio(
            "Preset range",
            ["All", "YTD", "1Y", "3Y", "5Y", "Custom"],
            index=5
        )

        manual = st.date_input(
            "Custom range",
            value=(min_date, max_date),  # returns tuple when two dates provided
            min_value=min_date,
            max_value=max_date
        )

    # compute start/end
    if mode == "All":
        start_date, end_date = min_date, max_date
    elif mode == "YTD":
        start_date, end_date = date(max_date.year, 1, 1), max_date
    else:
        years_map = {"1Y": 1, "3Y": 3, "5Y": 5}
        if mode in years_map:
            start_candidate = (pd.Timestamp(max_date) - pd.DateOffset(years=years_map[mode])).date()
            start_date, end_date = max(start_candidate, min_date), max_date
        else:  # Custom
            if isinstance(manual, tuple) and len(manual) == 2:
                start_date, end_date = manual
            else:
                start_date, end_date = min_date, max_date

    # safe order
    if start_date > end_date:
        start_date, end_date = end_date, start_date

    with st.sidebar.container(border=True): 
        fund = st.radio("Fund", ["Global", "Strategic", "Tactic"])

    return {
        "start": pd.to_datetime(start_date),
        "end": pd.to_datetime(end_date),
        "fund": fund
    }


# -------------------- Display helpers --------------------
def render_transactions_tab(tx: pd.DataFrame, fund: str):
    if fund == "Strategic":
        work = tx[tx['Type'] == 'Strategic']
    elif fund == "Tactic":
        work = tx[tx['Type'] == 'Tactic']
    else:
        work = tx
    st.caption(f"Rows: {len(work)} — Columns: {len(work.columns)}")
    st.dataframe(tx, use_container_width=True, height=500)


def render_holdings_tab(df: pd.DataFrame, start: pd.Timestamp, end: pd.Timestamp, fund: str):
    holdings = compute_holdings(df=df, start=start, end=end, fund=fund, trading_days_func=get_trading_days)
    st.caption(f"Rows: {len(holdings)} — Columns: {len(holdings.columns)}")
    st.dataframe(holdings, use_container_width=True, height=500)


def render_splits_tab(start: pd.Timestamp, end: pd.Timestamp):
    splits = load_splits(config.TICKERS)
    if splits.empty:
        st.info("No split data available.")
        return
    s_filtered = splits.loc[(splits.index >= start) & (splits.index <= end)]
    if s_filtered.empty:
        st.info("No splits in selected range.")
        return
    st.caption(f"Rows: {len(s_filtered)} — Columns: {len(s_filtered.columns)}")
    st.dataframe(s_filtered, use_container_width=True)


# -------------------- Main --------------------
def main():
    # Load transactions (loader handles config paths + parsing)
    df = load_transactions(config.TRANSACTION_FILE)

    if df is None or df.empty:
        st.error("No transaction data found.")
        return

    # ensure index is DatetimeIndex (loader should do this but be defensive)
    if not isinstance(df.index, pd.DatetimeIndex):
        df.index = pd.to_datetime(df.index)

    filters = sidebar_filters(df)
    if not filters:
        return

    start, end, fund = filters["start"], filters["end"], filters["fund"]
    tx = df.loc[(df.index >= start) & (df.index <= end)]
    st.title(f"{fund} Fund Overview")
    st.caption(f"Date range: {start.date()} → {end.date()}")

    tabs = st.tabs(["Transactions", "Holdings", "Splits"])
    with tabs[0]:
        render_transactions_tab(tx, fund)
    with tabs[1]:
        render_holdings_tab(df, start, end, fund)
    with tabs[2]:
        render_splits_tab(start, end)

    # Minimal custom styling
    st.markdown("""
    <style>
    section[data-testid="stSidebar"] {width: 330px !important;}
    .stMetric label {font-size:0.75rem;}
    </style>
    """, unsafe_allow_html=True)


if __name__ == "__main__":
    main()
