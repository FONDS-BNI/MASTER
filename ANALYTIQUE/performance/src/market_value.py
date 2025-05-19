# performance_analysis/src/market_value.py

class MarketValueCalculator:
    @staticmethod
    def calculate_market_value(prices_df, quantities_df):
        """Calculate the market value of assets"""
        market_value_df = prices_df.mul(quantities_df, level='Ticker')
        summed_market_value_df = market_value_df.groupby(level='Type', axis=1).sum()
        return market_value_df, summed_market_value_df
