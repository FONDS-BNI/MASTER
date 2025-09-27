import streamlit as st
import pandas as pd
from pathlib import Path

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
