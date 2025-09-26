import streamlit as st 
import pandas as pd
import numpy as np
from pathlib import Path

prices_path = Path(__file__).parent / 'data/stock_final.xlsx'
prices_sheet = 'Copy source'

holdings = pd.read_excel(prices_path, sheet_name=prices_sheet, engine='openpyxl')
print(holdings.head())


### STREAMLIT
st.write("Performance")



# def main():

# if __name__ == "__main__":
#     main()