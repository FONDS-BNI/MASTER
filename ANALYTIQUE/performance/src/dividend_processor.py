# performance_analysis/src/dividend_processor.py

import pandas as pd

class DividendProcessor:
    @staticmethod
    def process_dividends(df_dividends):
        """Process asset prices dataframe."""
        num_assets = df_dividends.shape[1] // 5
        assets_df = []

        # Loop over each pair of date and price columns
        for i in range(num_assets):
            declared_date_col = df_dividends.columns[5 * i]
            df_dividends = df_dividends.loc[1:,]
            payable_date_col = df_dividends.columns[5 * i + 3]
            dividend_col = df_dividends.columns[5 * i + 4]
            asset_name = declared_date_col  # Assuming price_col name is the asset name

            # Extract and clean data for the current asset
            asset_df = df_dividends[[payable_date_col, dividend_col]].dropna(subset=[payable_date_col])
            asset_df.columns = ['Payable Date', 'Dividend']
            asset_df['Asset'] = asset_name
            asset_df['Payable Date'] = pd.to_datetime(asset_df['Payable Date'])

            # Append to the list of asset dataframes
            assets_df.append(asset_df)

        # Combine all asset dataframes into a single long-format dataframe
        combined_df = pd.concat(assets_df, ignore_index=True)
        combined_df.drop_duplicates(subset=['Payable Date', 'Asset'], inplace=True)

        # Pivot the dataframe to have assets as columns and dates as the index
        pivot_df = combined_df.pivot(index='Payable Date', columns='Asset', values='Dividend').fillna(0)

        # Forward-fill missing values
        pivot_df.sort_index(inplace=True)

        return pivot_df
