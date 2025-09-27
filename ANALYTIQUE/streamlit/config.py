from pathlib import Path
 
DATA_DIR = Path(__file__).parent / 'data'
PRICES_PARQUET = DATA_DIR / 'prices.parquet'
TRANSACTION_FILE = DATA_DIR / "stock_final.xlsx"

# Bloomberg tickers for the ETFs we track
TICKERS = ['XBB.TO', 'XCB.TO', 'XEF.TO', 'XEM.TO', 'XHY.TO', 'XIG.TO', 'XIU.TO', 'XSB.TO', 'XUS.TO']

