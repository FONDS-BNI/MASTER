import streamlit as st
import pandas as pd
from pathlib import Path
import pyarrow as pa
from datetime import date
import pyarrow.parquet as pq
import plotly.express as px

# --- Constants ---
DATA_DIR = Path(__file__).parent / 'data'
PRICES_FILE = DATA_DIR / 'prices.csv'
PRICES_PARQUET = DATA_DIR / 'prices.parquet'
TRANSACTION_FILE = DATA_DIR / 'stock_final.xlsx'

# --- Page Configuration ---
# st.set_page_config(page_title="Price Data Viewer", layout="wide")

# # --- Data Loading ---
# @st.cache_data
# def load_data_transactions(file_path: Path) -> pd.DataFrame:
#     """
#     Load and preprocess transaction data from a CSV file.
#     The data is cached to improve performance.
#     """
#     if not file_path.exists():
#         st.error(f"Transaction data file not found: {file_path}")
#         return pd.DataFrame()
    
#     # Read only the first 4 columns from the 'Transactions' sheet
#     df = pd.read_excel(file_path, sheet_name="Transactions", usecols=range(5), index_col=0)
#     if 'Date' in df.columns:
#         df['Date'] = pd.to_datetime(df['Date'])

#     df['Value'] = df['Quantity'] * df['Price']

#     return df

# # def load_data(file_path: Path) -> pd.DataFrame:
# #     """
# #     Load and preprocess price data from a CSV file.
# #     The data is cached to improve performance.
# #     """
# #     if not file_path.exists():
# #         st.error(f"Data file not found: {file_path}")
# #         return pd.DataFrame()
    
# #     df = pd.read_csv(file_path, index_col=0, parse_dates=True)
# #     df = df.loc['2019-01-01':].dropna(how="all")
# #     table = pa.Table.from_pandas(df)
# #     pq.write_table(table, DATA_DIR / 'prices.parquet')

# #     return table

# def load_parquet_data(file_path: Path) -> pd.DataFrame:
#     """
#     Load and preprocess price data from a CSV file.
#     The data is cached to improve performance.
#     """
#     if not file_path.exists():
#         st.error(f"Data file not found: {file_path}")
#         return pd.DataFrame()
    
#     df = pd.read_parquet(file_path)
#     df = df.loc['2019-01-01':].dropna(how="all")

#     return df

# # --- Sidebar Components ---
# def build_sidebar(df: pd.DataFrame) -> dict:
#     """
#     Builds sidebar controls for date range, tickers, frequency, and display options.
#     Returns a dict of filter settings.
#     """
#     st.sidebar.header("Filter controls")

#     with st.sidebar.container(border=True):
#         if df.empty:
#             st.warning("No data available to build filters.")
#             return {}

#         min_date, max_date = df.index.min().date(), df.index.max().date()

#         # Allow user to choose how to define the date range
#         mode = st.radio("Date range selection", ["All", "YTD", "1 Year", "3 Years", "5 Years", "Custom"], index=5)
        
#         # Manual mode always shows a date range picker
#         manual_range = st.date_input(
#             "Choose a date range",
#             value=[min_date, max_date],
#             min_value=min_date,
#             max_value=max_date,
#         )
        
#         if mode == "Custom":
#             if len(manual_range) == 2:
#                 start_date, end_date = manual_range
#             else:
#                 start_date, end_date = min_date, max_date
#         elif mode == "YTD":
#             start_date, end_date = date(max_date.year, 1, 1), max_date
#         elif mode == "1 Year":
#             start_candidate = (pd.Timestamp(max_date) - pd.DateOffset(years=1)).date()
#             start_date, end_date = max(start_candidate, min_date), max_date
#         elif mode == "3 Years":
#             start_candidate = (pd.Timestamp(max_date) - pd.DateOffset(year=3)).date()
#             start_date, end_date = max(start_candidate, min_date), max_date
#         elif mode == "5 Years":
#             start_candidate = (pd.Timestamp(max_date) - pd.DateOffset(years=5)).date()
#             start_date, end_date = max(start_candidate, min_date), max_date
#         elif mode == "All":
#             start_date, end_date = min_date, max_date

#     # Ensure ordering
#     if start_date > end_date:
#         start_date, end_date = end_date, start_date

#     # Tickers selection with scrollable checkboxes
#     all_tickers = list(df.columns)
#     if "selected_tickers" not in st.session_state:
#         st.session_state.selected_tickers = all_tickers.copy()

#     with st.sidebar.expander("Tickers to show", expanded=True):
#         # Scrollable checkbox list
#         new_selection = []
#         for ticker in all_tickers:
#             checked = ticker in st.session_state.selected_tickers
#             if st.checkbox(ticker, value=checked, key=f"chk_{ticker}"):
#                 new_selection.append(ticker)
#         st.session_state.selected_tickers = new_selection

#     # Resampling frequency
#     with st.sidebar.container(border=True):
#         freq = st.selectbox(
#             "Resample frequency", ["D", "W", "M"], index=0, help="Select data resampling frequency."
#         )

#     # Data display options
#     with st.sidebar.container(border=True):
#         data_option = st.radio(
#             "Data options", ("Prices", "Returns", "Returns (Cummulative)")
#         )

#     return {
#         "start_date": start_date,
#         "end_date": end_date,
#         "tickers": st.session_state.selected_tickers,
#         "freq": freq,
#         "data_option": data_option,
#     }

# # --- Main Content ---
# def display_main_content(df: pd.DataFrame, filters: dict) -> None:
#     """
#     Display filtered data table and line chart.
#     """
#     st.title("Data Viewer")

#     if df.empty or not filters:
#         st.info("No data to display. Adjust filters or load data.")
#         return

#     start, end = pd.to_datetime(filters["start_date"]), pd.to_datetime(filters["end_date"])
#     filtered = df.loc[start:end]

#     # Apply frequency resampling
#     if filters["freq"] != "None":
#         filtered = filtered.resample(filters["freq"]).last().dropna(how="all")

#     # Filter selected tickers
#     if filters["tickers"]:
#         filtered = filtered[filters["tickers"]]
#     else:
#         filtered = pd.DataFrame()

#     # Compute returns if requested
#     if filters["data_option"] == "Returns":
#         filtered = filtered.pct_change().dropna(how="all") * 100
#     elif filters["data_option"] == "Returns (Cummulative)":
#         filtered = filtered.pct_change().dropna(how="all").cumsum() * 100

#     st.subheader(f"Showing data from {start.date()} to {end.date()}")
#     st.write(f"Rows: {len(filtered)} — Columns: {len(filtered.columns)}")

#     tab1, tab2 = st.tabs(["Data Table", "Line Chart"])
#     tab1.dataframe(filtered, use_container_width=True)

#     if filtered.empty:
#         tab2.info("No data to display. Adjust filters or select tickers.")
#     else:
#         fig = px.line(filtered, title="Price Data Over Time")
#         tab2.plotly_chart(fig, use_container_width=True)

# # --- Display Transactions ---
# def display_transactions(df: pd.DataFrame) -> None:
#     st.title("Transaction Viewer")

#     with st.container(border=True):
#         if df.empty:
#             st.info("No transaction data to display.")
#             return
#         mode = st.radio("Fund Selection", ["Global", "Strategic", "Tactic"], index=0)
        
#     if mode == "Global":
#         filtered_df = df
#     elif mode == "Strategic":
#         filtered_df = df[df['Type'] == 'Strategic']
#     elif mode == "Tactic":
#         filtered_df = df[df['Type'] == 'Tactic']

#     st.write(f"Rows: {len(filtered_df)} — Columns: {len(filtered_df.columns)}")
#     st.dataframe(filtered_df)

# # --- Main App Logic ---
# def main():
#     price_data = load_parquet_data(PRICES_PARQUET)
#     transaction_data = load_data_transactions(TRANSACTION_FILE)

#     if not price_data.empty:
#         filters = build_sidebar(price_data)
#         display_main_content(price_data, filters)
#         display_transactions(transaction_data)

# if __name__ == "__main__":
#     main()

from yahoo_api import YahooAPI
tickers = ['XBB.TO', 'XCB.TO', 'XEF.TO', 'XEM.TO', 'XHY.TO', 'XIG.TO', 'XIU.TO', 'XSB.TO', 'XUS.TO']

splits = YahooAPI().get_yahoo_data(tickers, metric=['splits'])
print(splits)