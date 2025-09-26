import streamlit as st
import pandas as pd
from pathlib import Path
import pyarrow as pa
from datetime import date
import pyarrow.parquet as pq
import plotly.express as px

# --- Constants ---
DATA_DIR = Path(__file__).parent.parent.parent / 'data'
# print("DATA_DIR:", Path(__file__).parent)
TRANSACTION_FILE = DATA_DIR / 'stock_final.xlsx'

# --- Page Configuration ---
st.set_page_config(page_title="Price Data Viewer", layout="wide")

# --- Data Loading ---
@st.cache_data
def load_data_transactions(file_path: Path) -> pd.DataFrame:
    """
    Load and preprocess transaction data from a CSV file.
    The data is cached to improve performance.
    """
    if not file_path.exists():
        st.error(f"Transaction data file not found: {file_path}")
        return pd.DataFrame()
    
    # Read only the first 4 columns from the 'Transactions' sheet
    df = pd.read_excel(file_path, sheet_name="Transactions", usecols=range(5), index_col=0)
    if 'Date' in df.columns:
        df['Date'] = pd.to_datetime(df['Date'])

    df['Value'] = df['Quantity'] * df['Price']

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

    if df.empty:
            st.info("No transaction data to display.")
            return
    
    with st.sidebar.container(border=True):
        mode = st.radio("Fund Selection", ["Global", "Strategic", "Tactic"], index=0)
        
    return {
        "start_date": start_date,
        "end_date": end_date,
        "fund": mode,
    }

# --- Display Transactions ---
def display_transactions(df: pd.DataFrame, filters: dict) -> None:
    st.title("Transaction Viewer")

    start, end = pd.to_datetime(filters["start_date"]), pd.to_datetime(filters["end_date"])
    filtered_df = df.loc[start:end]

    if filters["fund"] == "Global":
        filtered_df = filtered_df
    elif filters["fund"] == "Strategic":
        filtered_df = filtered_df[filtered_df['Type'] == 'Strategic']
    elif filters["fund"] == "Tactic":
        filtered_df = filtered_df[filtered_df['Type'] == 'Tactic']

    st.subheader(f"Showing data from {start.date()} to {end.date()}")
    st.write(f"Rows: {len(filtered_df)} — Columns: {len(filtered_df.columns)}")
    
    st.dataframe(filtered_df)

# --- Main App Logic ---
def main():
    transaction_data = load_data_transactions(TRANSACTION_FILE)

    if not transaction_data.empty:
        filters = build_sidebar(transaction_data)
        display_transactions(transaction_data, filters)

if __name__ == "__main__":
    main()
