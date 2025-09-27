import streamlit as st
import pandas as pd
from pathlib import Path

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