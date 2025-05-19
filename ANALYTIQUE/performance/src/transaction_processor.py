import pandas as pd
from pathlib import Path
from .config import DATA_DIR, CONFIG

class TransactionProcessor:
    @staticmethod
    def process_transactions(df_transactions, prices_df, df_split, df_dividends, df_investments):
        """Process the transactions dataframe and align it with the prices dataframe"""

        # Pivot the transactions to summarize quantities by fund
        pivot_df = df_transactions.pivot_table(index='Date', columns=['Type', 'Ticker'], values='Quantity', aggfunc='sum').fillna(0)

        # Cash transactions by fund
        df_transactions['Value'] = -df_transactions['Quantity'] * df_transactions['Price']
        cash_transactions_df = df_transactions.pivot_table(index='Date', columns='Type', values='Value', aggfunc='sum').fillna(0)

        # Accumulate quantities over time by ticker
        quantities_df = pivot_df.cumsum()
        quantities_df = quantities_df.reindex(prices_df.index).fillna(method='ffill').fillna(0)

        # Add Global sum for each ticker
        global_sum = quantities_df.groupby(level='Ticker', axis=1).sum()
        global_sum.columns = pd.MultiIndex.from_product(
            [['Global'], global_sum.columns.get_level_values('Ticker').unique()],
            names=['Type', 'Ticker']
        )
        quantities_df = pd.concat([quantities_df, global_sum], axis=1)
       
        # Process dividends
        for i in range(0, df_dividends.shape[1], 5):
            ticker_name = df_dividends.columns[i]
            ex_date_col = df_dividends.iloc[1:, i + 1]
            payable_date_col = df_dividends.iloc[1:, i + 3]
            dividend_amount_col = df_dividends.iloc[1:, i + 4]

            df = pd.DataFrame({
                'Ex-Date': ex_date_col,
                'Payable Date': payable_date_col,
                'Dividend': dividend_amount_col
            }).dropna(subset=['Ex-Date'])

            df['Ex-Date'] = pd.to_datetime(df['Ex-Date'])
            df.set_index('Ex-Date', inplace=True)

            new_columns = pd.MultiIndex.from_product([[ticker_name], df.columns])
            df.columns = new_columns

            qt_df = quantities_df.loc[:, (slice(None), ticker_name)]

            for ex_date, dividend_row in df.iterrows():
                if ex_date in qt_df.index:
                    index_pos = qt_df.index.get_loc(ex_date)
                    quantity_on_ex_date = qt_df.iloc[index_pos - 1] 
                    
                    total_dividend_strategic = (
                        quantity_on_ex_date['Strategic'].values[0] * dividend_row[(ticker_name, 'Dividend')]
                        if 'Strategic' in quantity_on_ex_date.index else 0
                    )
                    total_dividend_tactic = (
                        quantity_on_ex_date['Tactic'].values[0] * dividend_row[(ticker_name, 'Dividend')]
                        if 'Tactic' in quantity_on_ex_date.index else 0
                    )

                    payable_date = pd.to_datetime(dividend_row[(ticker_name, 'Payable Date')])

                    if payable_date in cash_transactions_df.index:
                        cash_transactions_df.at[payable_date, 'Strategic'] += total_dividend_strategic
                        cash_transactions_df.at[payable_date, 'Tactic'] += total_dividend_tactic
                    else:
                        cash_transactions_df.loc[payable_date] = {
                            'Strategic': total_dividend_strategic,
                            'Tactic': total_dividend_tactic
                        }

        # Additional detailed dividend handling...
        # load the same Excel file from your data/ folder
        file = DATA_DIR / CONFIG['file_name']
        div_raw_df = pd.read_excel(file, sheet_name='Copy dividends', header=[0,1])
        div_df = div_raw_df.stack(level=0).reset_index()
        div_df.rename(columns={'level_1': 'Ticker'}, inplace=True)
        div_df.drop('level_0', axis=1, inplace=True)
        div_df['Ex-Date'] = pd.to_datetime(div_df['Ex-Date'])
        div_df['Payable Date'] = pd.to_datetime(div_df['Payable Date'])
        div_df['Dividend Amount'] = pd.to_numeric(div_df['Dividend Amount'], errors='coerce')

        def get_last_quantities_before_date(quantities_df, date):
            quantities_before_date = quantities_df.loc[:date-pd.Timedelta(days=1)]
            if quantities_before_date.empty:
                return None
            else:
                return quantities_before_date.iloc[-1]
            
        dividend_amounts = []
        for idx, row in div_df.iterrows():
            ticker = row['Ticker']
            ex_date = row['Ex-Date']
            payable_date = row['Payable Date']
            div_amount = row['Dividend Amount']

            last_quantities = get_last_quantities_before_date(quantities_df, ex_date)
            if last_quantities is None:
                continue
            else:
                if ticker in quantities_df.columns.get_level_values(1):
                    quantities_for_ticker = last_quantities.xs(ticker, level='Ticker')
                    total_div = quantities_for_ticker * div_amount
                    total_div_df = total_div.to_frame(name='Dividend Amount')
                    total_div_df['Ticker'] = ticker
                    total_div_df['Payable Date'] = payable_date
                    total_div_df.reset_index(inplace=True)
                    dividend_amounts.append(total_div_df)

        if dividend_amounts:
            total_div_df = pd.concat(dividend_amounts)
            result_df = total_div_df.groupby(['Payable Date', 'Type'])['Dividend Amount']\
                                    .sum().unstack('Type')
            result_df.reset_index(inplace=True)
            result_df.fillna(0, inplace=True)
        else:
            print('No div')

        cash_transactions_df.sort_index(inplace=True)

        cash_df = df_investments.pivot_table(index='Date', columns='Type', values='Amount', aggfunc='sum').fillna(0)
        cash_transactions_df = cash_df.add(cash_transactions_df, fill_value=0)
 
        cash_df = cash_transactions_df.cumsum()
        cash_df['Global'] = cash_df.sum(axis=1)

        # test             
        test = pd.concat([cash_transactions_df, cash_df], axis=1)
        # print(test[:60])
        # print(test[61:120])
        # print(test[121:180])
        # print(quantities_df)

        return quantities_df, cash_df
