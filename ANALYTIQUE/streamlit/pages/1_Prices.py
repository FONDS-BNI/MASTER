import streamlit as st
import pandas as pd
from pathlib import Path
from datetime import date
import plotly.express as px

# --- Constants ---
DATA_DIR = Path(__file__).parent.parent.parent / 'performance/data'
PRICES_PARQUET = DATA_DIR / 'prices.parquet'

# --- Page Configuration ---
st.set_page_config(
    page_title="Price Data Viewer", 
    layout="wide"
)

# --- Data Loading ---
@st.cache_data
def load_parquet_data(file_path: Path) -> pd.DataFrame:
    """
    Load and preprocess price data from a Parquet file.
    The data is cached to improve performance.
    """
    if not file_path.exists():
        st.error(f"Data file not found: {file_path}")
        return pd.DataFrame()
    
    df = pd.read_parquet(file_path)
    df = df.loc['2019-01-01':].dropna(how="all")

    return df

# --- Sidebar Components ---
def build_sidebar(df: pd.DataFrame) -> dict:
    """
    Builds sidebar controls for date range, tickers, frequency, and display options.
    Returns a dict of filter settings.
    """
    st.sidebar.header("Filter controls")

    with st.sidebar.container(border=True):
        if df.empty:
            st.warning("No data available to build filters.")
            return {}

        min_date, max_date = df.index.min().date(), df.index.max().date()

        # Allow user to choose how to define the date range
        mode = st.radio("Date range selection", ["All", "YTD", "1 Year", "3 Years", "5 Years", "Custom"], index=5)
        
        # Manual mode always shows a date range picker
        manual_range = st.date_input(
            "Choose a date range",
            value=[min_date, max_date],
            min_value=min_date,
            max_value=max_date,
        )
        
        if mode == "Custom":
            if len(manual_range) == 2:
                start_date, end_date = manual_range
            else:
                start_date, end_date = min_date, max_date
        elif mode == "YTD":
            start_date, end_date = date(max_date.year, 1, 1), max_date
        elif mode == "1 Year":
            start_candidate = (pd.Timestamp(max_date) - pd.DateOffset(years=1)).date()
            start_date, end_date = max(start_candidate, min_date), max_date
        elif mode == "3 Years":
            start_candidate = (pd.Timestamp(max_date) - pd.DateOffset(year=3)).date()
            start_date, end_date = max(start_candidate, min_date), max_date
        elif mode == "5 Years":
            start_candidate = (pd.Timestamp(max_date) - pd.DateOffset(years=5)).date()
            start_date, end_date = max(start_candidate, min_date), max_date
        elif mode == "All":
            start_date, end_date = min_date, max_date

    # Ensure ordering
    if start_date > end_date:
        start_date, end_date = end_date, start_date

    # Tickers selection with scrollable checkboxes
    all_tickers = list(df.columns)
    if "selected_tickers" not in st.session_state:
        st.session_state.selected_tickers = all_tickers.copy()

    with st.sidebar.expander("Tickers to show", expanded=True):
        # Scrollable checkbox list
        new_selection = []
        for ticker in all_tickers:
            checked = ticker in st.session_state.selected_tickers
            if st.checkbox(ticker, value=checked, key=f"chk_{ticker}"):
                new_selection.append(ticker)
        st.session_state.selected_tickers = new_selection

    # Resampling frequency
    with st.sidebar.container(border=True):
        freq = st.selectbox(
            "Resample frequency", ["D", "W", "M"], index=0, help="Select data resampling frequency."
        )

    # Data display options
    with st.sidebar.container(border=True):
        data_option = st.radio(
            "Data options", ("Prices", "Returns", "Returns (Cummulative)")
        )

    return {
        "start_date": start_date,
        "end_date": end_date,
        "tickers": st.session_state.selected_tickers,
        "freq": freq,
        "data_option": data_option,
    }

# --- Main Content ---
def display_main_content(df: pd.DataFrame, filters: dict) -> None:
    """
    Display filtered data table and line chart.
    """
    st.title("Data Viewer")

    if df.empty or not filters:
        st.info("No data to display. Adjust filters or load data.")
        return

    start, end = pd.to_datetime(filters["start_date"]), pd.to_datetime(filters["end_date"])
    filtered = df.loc[start:end]

    # Apply frequency resampling
    if filters["freq"] != "None":
        filtered = filtered.resample(filters["freq"]).last().dropna(how="all")

    # Filter selected tickers
    if filters["tickers"]:
        filtered = filtered[filters["tickers"]]
    else:
        filtered = pd.DataFrame()

    # Compute returns if requested
    if filters["data_option"] == "Returns":
        filtered = filtered.pct_change().dropna(how="all") * 100
    elif filters["data_option"] == "Returns (Cummulative)":
        filtered = filtered.pct_change().dropna(how="all").cumsum() * 100

    st.caption(f"Date range: {start.date()} → {end.date()}")

    tabs = st.tabs(["Data Table", "Line Chart"])

    with tabs[0]:
        st.caption(f"Rows: {len(filtered)} — Columns: {len(filtered.columns)}")
        st.dataframe(filtered, use_container_width=True)

    with tabs[1]:
        if filtered.empty:
            st.info("No data to display. Adjust filters or select tickers.")
        else:
            fig = px.line(filtered, title="Price Data Over Time")
            st.plotly_chart(fig, use_container_width=True)
    
# --- Main App Logic ---
def main():
    price_data = load_parquet_data(PRICES_PARQUET)

    if not price_data.empty:
        filters = build_sidebar(price_data)
        display_main_content(price_data, filters)

if __name__ == "__main__":
    main()
