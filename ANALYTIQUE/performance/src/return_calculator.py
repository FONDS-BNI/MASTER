import pandas as pd

class ReturnCalculator:
    @staticmethod
    def calculate_returns(summed_market_value_df, starting_date, df_investments):
        """Calculate daily and cumulative returns adjusted for cash flows, including the 'Global' fund."""

        df_investments['Date'] = pd.to_datetime(df_investments['Date'])
        df_investments.set_index('Date', inplace=True)

        cash_flow_df = df_investments.pivot_table(index='Date', columns='Type', values='Amount', aggfunc='sum').fillna(0)
        cash_flow_df['Global'] = cash_flow_df.sum(axis=1)
        cash_flow_df = cash_flow_df.reindex(summed_market_value_df.index, fill_value=0)

        mv_prev = summed_market_value_df.shift(1)
        
        daily_returns_df = summed_market_value_df.pct_change().fillna(0)
        adjusted_returns_df = (summed_market_value_df - cash_flow_df - mv_prev) / summed_market_value_df
        daily_returns_df = daily_returns_df.mask((cash_flow_df != 0), adjusted_returns_df).fillna(0)
        cumulative_returns_df = (1 + daily_returns_df[starting_date:]).cumprod() - 1

        weekly_market_value_df = summed_market_value_df.resample('W').last()
        weekly_cash_flow_df = cash_flow_df.resample('W').sum()
        mv_prev_weekly = weekly_market_value_df.shift(1)
        weekly_returns_df = weekly_market_value_df.pct_change().fillna(0)
        adjusted_weekly_returns_df = (weekly_market_value_df - weekly_cash_flow_df - mv_prev_weekly) / weekly_market_value_df
        weekly_returns_df = weekly_returns_df.mask((weekly_cash_flow_df != 0), adjusted_weekly_returns_df).fillna(0)
        cumulative_weekly_returns_df = (1 + weekly_returns_df[starting_date:]).cumprod() - 1

        return daily_returns_df, cumulative_returns_df, weekly_returns_df, cumulative_weekly_returns_df
