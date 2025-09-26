import streamlit as st
import pandas as pd
from pathlib import Path
import pyarrow as pa
import pyarrow.parquet as pq
import plotly.express as px

# --- Constants ---
DATA_DIR = Path(__file__).parent / 'data'
PRICES_FILE = DATA_DIR / 'prices.csv'
PRICES_PARQUET = DATA_DIR / 'prices.parquet'

# --- Page Configuration ---
st.set_page_config(page_title="Price Data Viewer", layout="wide")

# --- Data Loading ---
@st.cache_data
# def load_data(file_path: Path) -> pd.DataFrame:
#     """
#     Load and preprocess price data from a CSV file.
#     The data is cached to improve performance.
#     """
#     if not file_path.exists():
#         st.error(f"Data file not found: {file_path}")
#         return pd.DataFrame()
    
#     df = pd.read_csv(file_path, index_col=0, parse_dates=True)
#     df = df.loc['2019-01-01':].dropna(how="all")
#     table = pa.Table.from_pandas(df)
#     pq.write_table(table, DATA_DIR / 'prices.parquet')

#     return table

def load_parquet_data(file_path: Path) -> pd.DataFrame:
    """
    Load and preprocess price data from a CSV file.
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

    if df.empty:
        st.sidebar.warning("No data available to build filters.")
        return {}

    min_date, max_date = df.index.min().date(), df.index.max().date()

    # Date range selection
    date_range = st.sidebar.date_input(
        "Date range",
        value=[min_date, max_date],
        min_value=min_date,
        max_value=max_date,
    )
    start_date, end_date = date_range if len(date_range) == 2 else (min_date, max_date)

    # Tickers selection with scrollable checkboxes
    all_tickers = list(df.columns)
    if "selected_tickers" not in st.session_state:
        st.session_state.selected_tickers = all_tickers.copy()

    with st.sidebar.expander("Tickers to show", expanded=True):
        # # Select all / Clear all buttons
        # col1, col2 = st.columns([1, 1])
        # with col1:
        #     if st.button("Select all"):
        #         st.session_state.selected_tickers = all_tickers.copy()
        # with col2:
        #     if st.button("Clear all"):
        #         st.session_state.selected_tickers = []

        # Scrollable checkbox list
        new_selection = []
        for ticker in all_tickers:
            checked = ticker in st.session_state.selected_tickers
            if st.checkbox(ticker, value=checked, key=f"chk_{ticker}"):
                new_selection.append(ticker)
        st.session_state.selected_tickers = new_selection

    # Resampling frequency
    freq = st.sidebar.selectbox(
        "Resample frequency", ["D", "W", "M"], index=0, help="Select data resampling frequency."
    )

    # Data display options
    data_option = st.sidebar.radio(
        "Data options", ("Prices", "Absolute Returns", "Relative Returns")
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
    st.title("Price Data Viewer")

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
    if filters["data_option"] == "Absolute Returns":
        filtered = filtered.pct_change().dropna(how="all") * 100
    elif filters["data_option"] == "Relative Returns":
        filtered = filtered.pct_change().dropna(how="all").cumsum() * 100

    st.subheader(f"Showing data from {start.date()} to {end.date()}")
    st.write(f"Rows: {len(filtered)} — Columns: {len(filtered.columns)}")

    tab1, tab2 = st.tabs(["Data Table", "Line Chart"])
    tab1.dataframe(filtered, use_container_width=True)

    if filtered.empty:
        tab2.info("No data to display. Adjust filters or select tickers.")
    else:
        fig = px.line(filtered, title="Price Data Over Time")
        tab2.plotly_chart(fig, use_container_width=True)


# --- Main App Logic ---
def main():
    price_data = load_parquet_data(PRICES_PARQUET)
    
    if not price_data.empty:
        filters = build_sidebar(price_data)
        display_main_content(price_data, filters)

if __name__ == "__main__":
    main()
