import pandas as pd
import requests

funds_name = ['Tactic', 'Strategic', 'Global']

fund_dict = {
    'NBC5703': {
        'fundName': 'NBI International Equity Fund', 
        'fundKey': 105946
    },
}

class BNI_FUND:
    """Class to fetch historical data for BNI funds."""
    
    def __init__(self, ticker, fund_data):
        self.ticker = ticker
        self.fundKey = fund_data['fundKey']
        self.fundName = fund_data['fundName']

    def getHistoricalData(self):
        """Fetches historical data for the given fund."""
        URL = f'https://www.nbinvestments.ca/bin/fundDetailsHistoricalData?fundKey={self.fundKey}&period=custom&startDate=&endDate=&lang=en'
        headers = {
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:122.0) Gecko/20100101 Firefox/122.0"
        }
        try:
            session = requests.Session()
            response = session.get(URL, headers=headers)
            response.raise_for_status()

            # Parse JSON data
            data = response.json()

            # Check for valid data
            if not data:
                print(f'No data found for {self.ticker}')
                return pd.DataFrame()

            # Build DataFrame
            df = pd.DataFrame(data)
            df['value'] = df['value'].str.replace('$', '', regex=False).astype(float)
            df['date'] = pd.to_datetime(df['date'], format='%m/%d/%Y')
            df.set_index('date', inplace=True)

            # Rename column 
            df.index.name = 'Date'
            df.rename(columns={'value': self.ticker}, inplace=True)
            return df
        except:
            print("No NBI funds")
            return pd.DataFrame()
