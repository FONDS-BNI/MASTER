# performance_analysis/src/data_loader.py

import pandas as pd
from pathlib import Path
from .config import DATA_DIR, CONFIG

class DataLoader:
    def __init__(self):
        
        self.file_path          = DATA_DIR / CONFIG['file_name']
        self.sheet_prices       = CONFIG['sheet_prices']
        self.sheet_dividends    = CONFIG['sheet_dividends']
        self.sheet_splits       = CONFIG['sheet_splits']
        self.sheet_transactions = CONFIG['sheet_transactions']
        self.sheet_investments  = CONFIG['sheet_investments']

    def load_data(self):
        try:
            df_prices       = pd.read_excel(self.file_path, sheet_name=self.sheet_prices, engine='openpyxl')
            df_dividends    = pd.read_excel(self.file_path, sheet_name=self.sheet_dividends, engine='openpyxl')
            df_splits       = pd.read_excel(self.file_path, sheet_name=self.sheet_splits, engine='openpyxl')
            df_transactions = pd.read_excel(self.file_path, sheet_name=self.sheet_transactions, engine='openpyxl')
            df_investments  = pd.read_excel(self.file_path, sheet_name=self.sheet_investments, engine='openpyxl')
        except FileNotFoundError as e:
            print(f"Error loading data: {e}")
            return None, None, None, None, None

        return df_prices, df_dividends, df_splits, df_transactions, df_investments
