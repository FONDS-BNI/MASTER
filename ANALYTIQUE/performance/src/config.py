import pandas as pd
from pathlib import Path
pd.options.display.float_format = '{:.4f}'.format

# ── Project Paths 
PROJECT_ROOT = Path(__file__).parent.parent
DATA_DIR     = PROJECT_ROOT / "data"
OUTPUT_DIR   = PROJECT_ROOT / "output"


# ── Excel / PPT Filenames 
PPT_INPUT  = DATA_DIR / "Excel pour PPT.xlsx"
PPT_OUTPUT = DATA_DIR / "data_ppt.xlsx"

# ── Analysis Configuration 
CONFIG = {
    "file_name":        "stock_final.xlsx",
    "sheet_prices":     "Copy source",
    "sheet_dividends":  "Copy dividends",
    "sheet_splits":     "Copy splits",
    "sheet_transactions":"Transactions",
    "sheet_investments": "Investments",
    "starting_date":    "2023-05-01",
    "initial_investment": 1000,
    "portfolio_reference": "Portefeuille de référence",
}
