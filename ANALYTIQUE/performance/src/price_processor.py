import pandas as pd
from .config import DATA_DIR, CONFIG
from .bni_fund import BNI_FUND, fund_dict

class PriceProcessor:
    def __init__(self):
        file_path = DATA_DIR / CONFIG['file_name']
        self.prices_excel = pd.read_excel(
            file_path,
            sheet_name=CONFIG['sheet_prices'],
            engine='openpyxl'
        )

    def process_prices(self):
        """Process asset prices dataframe."""
        num_assets = self.prices_excel.shape[1] // 2
        assets_df = []

        # Loop over each pair of date and price columns
        for i in range(num_assets):
            date_col  = self.prices_excel.columns[2 * i]
            price_col = self.prices_excel.columns[2 * i + 1]
            asset_name = price_col

            asset_df = (
                self.prices_excel[[date_col, price_col]]
                .dropna(subset=[date_col])
            )
            asset_df.columns = ['Date', 'Price']
            asset_df['Asset'] = asset_name
            asset_df['Date']  = pd.to_datetime(asset_df['Date'])
            assets_df.append(asset_df)

        combined_df = pd.concat(assets_df, ignore_index=True)
        combined_df.drop_duplicates(subset=['Date', 'Asset'], inplace=True)

        pivot_df = (
            combined_df
            .pivot(index='Date', columns='Asset', values='Price')
            .sort_index()
            .fillna(method='ffill')
        )

        # Add BNI funds
        all_data = []
        for ticker, fund_data in fund_dict.items():
            fund = BNI_FUND(ticker, fund_data)
            df   = fund.getHistoricalData()
            if not df.empty:
                all_data.append(df)

        if all_data:
            df_funds = pd.concat(all_data, axis=1).sort_index()
            merged  = pivot_df.merge(
                df_funds,
                left_index=True,
                right_index=True,
                how='outer'
            )[:pivot_df.index.max()]
            return merged.fillna(method='ffill')

        print('No data retrieved')
        return pivot_df
