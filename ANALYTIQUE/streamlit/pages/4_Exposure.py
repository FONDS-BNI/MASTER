import streamlit as st
import pandas as pd
import numpy as np
import altair as alt
from datetime import date

import config
from utils.transforms.compute_holdings import build_holdings
from utils.loaders.load_raw_transactions import load_transactions
from utils.loaders.load_raw_prices import load_parquet_data
from utils.loaders.api.blackrock_api import fetch_all_holdings

# -------------------- Page Config --------------------
st.set_page_config(page_title="Deep Exposure Decomposition", layout="wide")
st.title("Deep Exposure Decomposition (ETF Look-Through)")

# -------------------- Caching --------------------
@st.cache_data(show_spinner=False)
def get_trading_days(start: pd.Timestamp, end: pd.Timestamp) -> pd.DatetimeIndex:
    start = pd.to_datetime(start).normalize()
    end = pd.to_datetime(end).normalize()
    return pd.bdate_range(start=start, end=end)

@st.cache_data(show_spinner=True)
def load_prices() -> pd.DataFrame:
    return load_parquet_data(config.PRICES_PARQUET)

@st.cache_data(show_spinner=True)
def load_underlyers_snapshot(tickers=None) -> pd.DataFrame:
    return fetch_all_holdings(ticker_list=tickers)

@st.cache_data(show_spinner=False)
def compute_holdings_cached(df: pd.DataFrame, start: pd.Timestamp, end: pd.Timestamp, fund: str):
    return build_holdings(df=df, start=start, end=end, fund=fund, trading_days_func=get_trading_days)

# -------------------- Sidebar Filters --------------------
def sidebar_filters(tx: pd.DataFrame) -> dict:
    st.sidebar.header("Filters")
    if tx.empty:
        return {}
    min_date = tx.index.min().date()
    max_date = tx.index.max().date()

    with st.sidebar.expander("Date range", expanded=True):
        mode = st.radio("Preset", ["All","YTD","1Y","3Y","5Y","Custom"], index=5, horizontal=True)
        manual = st.date_input("Custom range", value=(min_date, max_date), min_value=min_date, max_value=max_date)

    if mode == "All":
        start_date, end_date = min_date, max_date
    elif mode == "YTD":
        start_date, end_date = date(max_date.year,1,1), max_date
    else:
        years_map = {"1Y":1,"3Y":3,"5Y":5}
        if mode in years_map:
            start_candidate = (pd.Timestamp(max_date) - pd.DateOffset(years=years_map[mode])).date()
            start_date, end_date = max(start_candidate,min_date), max_date
        else:
            if isinstance(manual, tuple) and len(manual)==2:
                start_date, end_date = manual
            else:
                start_date, end_date = min_date, max_date
    if start_date > end_date:
        start_date, end_date = end_date, start_date

    fund = st.sidebar.radio("Fund", ["Global","Strategic","Tactic"], horizontal=True)
    return {
        "start": pd.to_datetime(start_date),
        "end": pd.to_datetime(end_date),
        "fund": fund
    }

# -------------------- Core Computation --------------------
UNDERLYER_DIMENSIONS = ["Sector","Asset Class","Location","Currency"]

FIXED_INCOME_FLAG = lambda df: (df["Duration"].notna()) | (df["Coupon (%)"].notna())

COUNTRY_COORDS = {
    "United States": (37.0902,-95.7129),
    "Canada": (56.1304,-106.3468),
    "Japan": (36.2048,138.2529),
    "United Kingdom": (55.3781,-3.4360),
    "Germany": (51.1657,10.4515),
    "France": (46.2276,2.2137),
    "China": (35.8617,104.1954),
    "Australia": (-25.2744,133.7751),
    "Switzerland": (46.8182,8.2275),
    "Netherlands": (52.1326,5.2913),
    "Brazil": (-14.2350,-51.9253),
    "Mexico": (23.6345,-102.5528),
    "Spain": (40.4637,-3.7492),
    "Italy": (41.8719,12.5674),
    "Sweden": (60.1282,18.6435),
}

def _safe_weights(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    if df["Weight (%)"].isna().all():
        df["Weight (%)"] = 0.0
    return df

@st.cache_data(show_spinner=True)
def compute_underlyer_exposures(
    holdings_qty: pd.DataFrame,
    prices: pd.DataFrame,
    underlyers: pd.DataFrame
):
    if holdings_qty.empty:
        return pd.DataFrame(), pd.DataFrame(), pd.DataFrame()

    common = holdings_qty.columns.intersection(prices.columns)
    if common.empty:
        return pd.DataFrame(), pd.DataFrame(), pd.DataFrame()
    prices = prices.reindex(holdings_qty.index).ffill()
    prices = prices[common]
    holdings_qty = holdings_qty[common]

    etf_values = holdings_qty * prices
    under_df = _safe_weights(underlyers.copy())
    under_df = under_df[under_df["ETF Ticker"].isin(common)]

    # --- Recalculate Weight (%) from Market Value within each ETF ---
    if "Market Value" in under_df.columns:
        mv_totals = under_df.groupby("ETF Ticker")["Market Value"].transform("sum")
        under_df["Weight (%)"] = np.where(mv_totals > 0, under_df["Market Value"] / mv_totals * 100.0, 0.0)

    all_under_tickers = under_df["Ticker"].unique()
    values_matrix = pd.DataFrame(0.0, index=etf_values.index, columns=all_under_tickers)

    meta_cols = ["Ticker","Name","Sector","Asset Class","Location","Currency","Duration","Coupon (%)","Maturity","ETF Ticker"]
    meta = (under_df.sort_values("Effective Date", ascending=False)
                  .drop_duplicates(subset=["Ticker"])
                  .set_index("Ticker")[meta_cols[1:]])

    for etf, sub in under_df.groupby("ETF Ticker"):
        if etf not in etf_values.columns:
            continue
        v_series = etf_values[etf]
        # Aggregate recalculated weights by Ticker (summing if duplicates)
        w = (sub.groupby("Ticker", as_index=False)["Weight (%)"]
                .sum())
        w["w"] = w["Weight (%)"].fillna(0) / 100.0
        exposures = np.outer(v_series.values, w["w"].values)
        df_exp = pd.DataFrame(exposures, index=v_series.index, columns=w["Ticker"].values)
        values_matrix.loc[:, w["Ticker"].values] += df_exp

    long = values_matrix.reset_index(names="Date").melt(id_vars="Date", var_name="Underlying", value_name="Exposure")
    long = long[long["Exposure"] != 0]
    long = long.join(meta, on="Underlying")

    return values_matrix, meta, long

def aggregate_dimension(long_df: pd.DataFrame, dimension: str) -> pd.DataFrame:
    if long_df.empty:
        return pd.DataFrame()
    tmp = long_df.copy()
    tmp[dimension] = tmp[dimension].fillna("Unknown")
    agg = (tmp.groupby(["Date", dimension])["Exposure"].sum()
              .reset_index()
              .pivot(index="Date", columns=dimension, values="Exposure")
              .fillna(0.0)
              .sort_index())
    return agg

# -------------------- Visualization Helpers --------------------
def single_date_series(df: pd.DataFrame, d: pd.Timestamp) -> pd.Series:
    if df.empty: return pd.Series(dtype=float)
    if d not in df.index:
        d = df.index[df.index.get_indexer([d], method="nearest")[0]]
    return df.loc[d]

def bar_chart(series: pd.Series, title: str):
    if series.empty:
        st.info("No data.")
        return
    data = series.reset_index()
    data.columns = ["Category","Exposure"]
    data = data.sort_values("Exposure", ascending=False)
    chart = (alt.Chart(data)
             .mark_bar()
             .encode(y=alt.Y("Category", sort='-x'),
                     x=alt.X("Exposure:Q", title="Exposure"),
                     tooltip=["Category","Exposure"])
             .properties(height=500, title=title))
    st.altair_chart(chart, use_container_width=True)

# -------------------- Fixed Income Aggregations --------------------
def fixed_income_summary(long_df: pd.DataFrame, date_point: pd.Timestamp):
    if long_df.empty:
        st.info("No data.")
        return
    fi = long_df[(long_df["Date"]==date_point) & FIXED_INCOME_FLAG(long_df)]
    if fi.empty:
        st.info("No fixed income exposure for selected date.")
        return
    total = fi["Exposure"].sum()
    fi["Duration"] = pd.to_numeric(fi["Duration"], errors="coerce")
    fi["Coupon (%)"] = pd.to_numeric(fi["Coupon (%)"], errors="coerce")
    vw_duration = (fi["Exposure"] * fi["Duration"]).sum() / max(total,1) if fi["Duration"].notna().any() else np.nan
    vw_coupon = (fi["Exposure"] * fi["Coupon (%)"]).sum() / max(total,1) if fi["Coupon (%)"].notna().any() else np.nan

    col1,col2,col3 = st.columns(3)
    col1.metric("Fixed Income Notional", f"{total:,.0f}")
    col2.metric("Value-Weighted Duration", f"{vw_duration:,.2f}" if pd.notna(vw_duration) else "N/A")
    col3.metric("Value-Weighted Coupon (%)", f"{vw_coupon:,.2f}" if pd.notna(vw_coupon) else "N/A")

    fi["Dur Bucket"] = pd.cut(fi["Duration"],
                              bins=[-0.01,1,3,5,7,10,20,100],
                              labels=["0-1","1-3","3-5","5-7","7-10","10-20","20+"])
    dur_dist = fi.groupby("Dur Bucket")["Exposure"].sum().sort_index()
    bar_chart(dur_dist, "Duration Bucket Exposure")

# -------------------- Location Map --------------------
def location_map(series: pd.Series):
    if series.empty:
        st.info("No location data.")
        return
    df = series.reset_index()
    df.columns = ["Location","Exposure"]
    df["Location"] = df["Location"].fillna("Unknown")
    df = df[df["Location"] != "Unknown"]
    if df.empty:
        st.info("No mappable locations.")
        return
    df["coords"] = df["Location"].map(COUNTRY_COORDS)
    df = df[df["coords"].notna()]
    if df.empty:
        st.info("No coordinates available for current locations.")
        return
    df[["lat","lon"]] = pd.DataFrame(df["coords"].tolist(), index=df.index)
    st.map(df[["lat","lon","Exposure"]], size="Exposure")

# -------------------- Underlyers Table --------------------
def render_underlyers_table(long_df: pd.DataFrame, date_point: pd.Timestamp):
    if long_df.empty:
        st.info("No data.")
        return
    snap = long_df[long_df["Date"]==date_point].copy()
    if snap.empty:
        st.info("No exposures on selected date.")
        return
    snap = snap.groupby(["Underlying","Name","Sector","Asset Class","Location","Currency","Duration","Coupon (%)","ETF Ticker"]).agg({"Exposure":"sum"}).reset_index()
    total = snap["Exposure"].sum()
    snap["Pct"] = snap["Exposure"]/total
    snap = snap.sort_values("Exposure", ascending=False)
    st.caption(f"Underlyers on {date_point.date()} — Total {total:,.0f}")
    st.dataframe(snap, use_container_width=True, height=600)

# -------------------- Ticker Normalization Helpers --------------------
def normalize_etf_ticker(raw: str) -> str:
    if not isinstance(raw, str):
        return raw
    r = raw.strip().upper()
    if ' ' in r:
        r = r.split(' ')[0]
    if '.' in r:
        r = r.split('.')[0]
    return r

def normalize_holdings_columns(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return df
    norm_cols = [normalize_etf_ticker(c) for c in df.columns]
    temp = df.copy()
    temp.columns = norm_cols
    return temp.groupby(level=0, axis=1).sum()

def normalize_price_columns(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return df
    norm_cols = [normalize_etf_ticker(c) for c in df.columns]
    temp = df.copy()
    temp.columns = norm_cols
    combined = {}
    for col, sub in temp.groupby(level=0, axis=1):
        if sub.shape[1] == 1:
            combined[col] = sub.iloc[:, 0]
        else:
            combined[col] = sub.bfill(axis=1).iloc[:, 0]
    return pd.DataFrame(combined, index=temp.index).sort_index()

# -------------------- Main --------------------
def main():
    tx = load_transactions(config.TRANSACTION_FILE)
    if tx is None or tx.empty:
        st.error("No transactions available.")
        return
    if not isinstance(tx.index, pd.DatetimeIndex):
        tx.index = pd.to_datetime(tx.index)

    filters = sidebar_filters(tx)
    if not filters:
        return
    start, end, fund = filters["start"], filters["end"], filters["fund"]

    st.caption(f"Date range: {start.date()} → {end.date()} | Fund: {fund}")

    holdings = compute_holdings_cached(tx, start, end, fund)
    if holdings.empty:
        st.warning("No holdings for selection.")
        return

    original_holdings_cols = holdings.columns.tolist()
    holdings = normalize_holdings_columns(holdings)

    prices = load_prices()
    prices = normalize_price_columns(prices)

    underlying = load_underlyers_snapshot(list(holdings.columns))
    if underlying.empty:
        st.warning("No underlying holdings data fetched.")
        return

    values_matrix, meta, long_df = compute_underlyer_exposures(holdings, prices, underlying)
    if long_df.empty:
        st.warning("Unable to compute look-through exposures (maybe missing prices).")
        return

    dim_agg = {dim: aggregate_dimension(long_df, dim) for dim in UNDERLYER_DIMENSIONS}

    all_dates = holdings.index
    pick = st.slider("Select Date", min_value=all_dates.min().to_pydatetime(),
                     max_value=all_dates.max().to_pydatetime(),
                     value=all_dates.max().to_pydatetime())
    picked_date = pd.Timestamp(pick).normalize()

    total_series = values_matrix.sum(axis=1)
    total_value_latest = single_date_series(total_series.to_frame("Total"), picked_date).iloc[0]

    m1, m2, m3 = st.columns(3)
    m1.metric("Total Portfolio Value", f"{total_value_latest:,.0f}")
    m2.metric("Distinct Underlyers", f"{values_matrix.shape[1]}")
    m3.metric("ETFs Held", f"{holdings.shape[1]}")

    tabs = st.tabs([
        "Overview","Sector","Asset Class","Location","Currency","Fixed Income","Underlyers","Raw"
    ])

    # Overview Tab
    with tabs[0]:
        st.subheader("Overview")
        sec_series = single_date_series(dim_agg["Sector"], picked_date) if not dim_agg["Sector"].empty else pd.Series(dtype=float)
        ac_series = single_date_series(dim_agg["Asset Class"], picked_date) if not dim_agg["Asset Class"].empty else pd.Series(dtype=float)
        colA, colB = st.columns(2)
        with colA:
            bar_chart(sec_series.sort_values(ascending=False).head(15), f"Sector Exposure ({picked_date.date()})")
        with colB:
            bar_chart(ac_series.sort_values(ascending=False).head(15), f"Asset Class Exposure ({picked_date.date()})")

    # Sector
    with tabs[1]:
        st.subheader("Sector")
        s = single_date_series(dim_agg["Sector"], picked_date)
        bar_chart(s.sort_values(ascending=False), f"Sector Exposure ({picked_date.date()})")

    # Asset Class
    with tabs[2]:
        st.subheader("Asset Class")
        s = single_date_series(dim_agg["Asset Class"], picked_date)
        bar_chart(s.sort_values(ascending=False), f"Asset Class Exposure ({picked_date.date()})")

    # Location
    with tabs[3]:
        st.subheader("Location")
        loc_df = dim_agg["Location"]
        loc_series = single_date_series(loc_df, picked_date)
        col1,col2 = st.columns([1,1])
        with col1:
            bar_chart(loc_series.sort_values(ascending=False), f"Location Exposure ({picked_date.date()})")
        with col2:
            location_map(loc_series)

    # Currency
    with tabs[4]:
        st.subheader("Currency")
        cur_df = dim_agg["Currency"]
        s = single_date_series(cur_df, picked_date)
        bar_chart(s.sort_values(ascending=False), f"Currency Exposure ({picked_date.date()})")

    # Fixed Income
    with tabs[5]:
        st.subheader("Fixed Income Metrics")
        fixed_income_summary(long_df, picked_date)

    # Underlyers
    with tabs[6]:
        st.subheader("Underlyers (Look-Through)")
        render_underlyers_table(long_df, picked_date)

    # Raw
    with tabs[7]:
        st.subheader("Raw Data (Debug)")
        with st.expander("Original vs Normalized Holdings Columns"):
            st.write("Original:", original_holdings_cols)
            st.write("Normalized:", list(holdings.columns))
        with st.expander("Holdings (Quantities)"):
            st.dataframe(holdings, use_container_width=True, height=250)
        with st.expander("ETF Values"):
            st.dataframe((holdings * prices.reindex(holdings.index).ffill())[holdings.columns], use_container_width=True, height=250)
        with st.expander("Underlyer Values Matrix"):
            st.dataframe(values_matrix, use_container_width=True, height=300)
        with st.expander("Underlyer Metadata"):
            st.dataframe(meta, use_container_width=True, height=300)
        with st.expander("Long Form Exposures"):
            st.dataframe(long_df.head(5000), use_container_width=True, height=300)

    st.markdown("""
    <style>
    section[data-testid="stSidebar"] {width: 340px !important;}
    </style>
    """, unsafe_allow_html=True)

if __name__ == "__main__":
    main()
