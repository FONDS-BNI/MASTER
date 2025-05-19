import pandas as pd
import xlwings as xw
import matplotlib.pyplot as plt
from pathlib import Path
from datetime import timedelta

from .config                import CONFIG, DATA_DIR, OUTPUT_DIR, PPT_INPUT, PPT_OUTPUT
from .data_loader           import DataLoader
from .price_processor       import PriceProcessor
from .dividend_processor    import DividendProcessor
from .transaction_processor import TransactionProcessor
from .market_value          import MarketValueCalculator
from .return_calculator     import ReturnCalculator
from .plotter               import Plotter
from .metrics_calculator    import MetricsCalculator
from .bni_fund              import funds_name

# Excel PPT paths
file_path_excel_pour_pp = PPT_INPUT
file_path_output_pp     = PPT_OUTPUT


class PortfolioAnalysis:
    def __init__(self, config):
        self.config                = config
        self.data_loader           = DataLoader()
        self.transaction_processor = TransactionProcessor()
        self.market_value_calculator = MarketValueCalculator()
        self.return_calculator     = ReturnCalculator()
        self.plotter               = Plotter()

        # output directories
        self.output_path        = OUTPUT_DIR

        # always returns five items
        ( self.prices_excel,
          self.dividends_excel,
          self.splits_excel,
          self.transactions_excel,
          self.investments_excel ) = self.data_loader.load_data()

        # prepare the prices DataFrame
        self.prices_df = (
            PriceProcessor()
            .process_prices()
            .loc['2019-01-06':]
        )


    def calculate_and_plot_total_return(self, summed_market_value_df):
        # 1) reload raw sheets
        _, df_dividends, df_splits, _, df_investments = self.data_loader.load_data()

        # 2) compute daily & weekly returns
        starting_date = self.prices_df.index.max() - pd.DateOffset(years=3)
        daily_ret, cum_ret, weekly_ret, _ = self.return_calculator.calculate_returns(
            summed_market_value_df,
            starting_date,
            df_investments
        )

        # 3) evolution of $1,000 investment (daily)
        invest_vals = self.config['initial_investment'] * (1 + cum_ret)
        t0 = invest_vals.index[0] - timedelta(days=1)
        invest_vals.loc[t0] = self.config['initial_investment']
        invest_vals = invest_vals.sort_index()

        # 4) prepare adjusted prices & dividends for benchmark
        adj_prices = self.prices_df.copy()
        for _, row in df_splits.iterrows():
            cols = [c for c in adj_prices.columns if row['Asset'] in c]
            adj_prices.loc[adj_prices.index >= row['Ex-Date'], cols] *= row['Split']

        div_df = DividendProcessor.process_dividends(df_dividends)
        div_df = div_df[self.prices_df.index.min():self.prices_df.index.max()]

        # 5) build weekly benchmark returns
        weekly_assets      = adj_prices.resample('W').last()
        weekly_divs        = div_df.resample('W').last()
        weekly_div_returns = weekly_divs / weekly_assets
        weekly_asset_ret   = weekly_assets.pct_change().fillna(0).add(weekly_div_returns, fill_value=0)

        weekly_ret['Benchmark'] = (
            0.6 * weekly_asset_ret['XBB CN Equity']
          + 0.4 * (
                0.35 * weekly_asset_ret['XIU CN Equity']
              + 0.35 * weekly_asset_ret['XUS CN Equity']
              + 0.2  * weekly_asset_ret['XEF CN Equity']
              + 0.1  * weekly_asset_ret['XEM CN Equity']
            )
        )

        # 6) generate and save metrics plots into output/
        for window in (52, 156):
            self.plot_metrics(weekly_ret, window)

        # 7) final daily‐evolution plots per portfolio
        cum_bench    = (1 + weekly_ret['Benchmark'][starting_date:]).cumprod() - 1
        invest_bench = self.config['initial_investment'] * (1 + cum_bench)
        invest_bench.loc[t0] = self.config['initial_investment']
        invest_bench = invest_bench.sort_index()

        for fund in cum_ret.columns.get_level_values('Type'):
            self.plotter.plot_investment_evolution(
                invest_vals[fund],
                invest_bench,
                fund,
                self.config['initial_investment']
            )


    def plot_metrics(self, weekly_fund_returns, window):
        date_1 = pd.Timestamp('2025-02-06') ## ligne pour allocation tactique 06 février 2025 -> Tactique 2
        date_2 = pd.Timestamp('2025-03-06') ## ligne pour allocaiton tactique 06 mars 2025    -> Tactique 1
        start_point = '2024-01-01'
        bench = weekly_fund_returns['Benchmark']

        settings = {
            'Global':    {"VAM": 130, "RI": 0.5, "RA": 260, "window": window},
            'Strategic': {"VAM": 100, "RI": 0.5, "RA": 200, "window": window},
            'Tactic':    {"VAM": 250, "RI": 0.5, "RA": 500, "window": window}
        }

        metrics = [
            ('VAM', MetricsCalculator.calculate_value_added_average),
            ('RA',  MetricsCalculator.calculate_active_risk),
            ('RI',  MetricsCalculator.calculate_information_ratio)
        ]

        latest = {k: {} for k, _ in metrics}
        fig, axs = plt.subplots(3, 3, figsize=(10,8), sharey='col')
        handle1 = handle2 = None

        for i, (fund, cfg) in enumerate(settings.items()):
            returns = weekly_fund_returns[fund]
            calc    = MetricsCalculator(returns, bench, cfg["window"])
            for j, (key, func) in enumerate(metrics):
                ax = axs[i, j]
                vals = func(calc)[start_point:]
                l1   = ax.axvline(x=date_1, color='lightblue', linestyle='--', linewidth=0.9)
                l2   = ax.axvline(x=date_2, color='grey',     linestyle='--', linewidth=0.9)
                if handle1 is None:
                    handle1, handle2 = l1, l2
                ax.plot(vals.index, vals, color='b')
                ax.axhline(cfg[key], color='r', linewidth=2)
                if i < 2:
                    ax.set_xticklabels([])
                else:
                    ax.tick_params(axis='x', rotation=45)
                latest[key][fund] = vals.iloc[-1]

        fig.legend([handle1, handle2], ['First allocation', 'Second allocation'],
                   loc='lower center', ncol=2, frameon=False)
        plt.tight_layout(rect=[0,0.05,1,1])

        
        output_file = self.output_path / f"metrics_{window/52:.0f}Y_plot.pdf"
        self.output_path.mkdir(parents=True, exist_ok=True)
        plt.savefig(output_file, dpi=300)


        latest_df = pd.DataFrame(latest).T
        with pd.ExcelWriter(file_path_output_pp, mode='a', engine='openpyxl') as writer:
            latest_df[funds_name].to_excel(
                writer,
                sheet_name=f"Ratios - {round(window,0)/52}Y",
                index=True
            )

    def run_analysis(self):
        # reload raw sheets
        ( df_prices,
          df_dividends,
          df_splits,
          df_transactions,
          df_investments ) = self.data_loader.load_data()

        # process transactions
        quantities_df, cash_df = self.transaction_processor.process_transactions(
            df_transactions,
            self.prices_df,
            df_splits,
            df_dividends,
            df_investments
        )

        # write snapshots
        wb = xw.Book(file_path_excel_pour_pp)
        with pd.ExcelWriter(file_path_output_pp, engine='openpyxl') as writer:
            for date_id in [
                'Today', 'Tactic 1', 'Tactic 2', 'Tactic 3', 'Tactic 4',
                'Strategic 1', 'Strategic 2', 'Strategic 3', 'Strategic 4'
            ]:
                date = wb.names[date_id.replace(" ", "")]\
                         .refers_to_range.value.strftime('%Y-%m-%d')
                df = quantities_df.loc[quantities_df.index == date]
                df.columns = ['_'.join(col).strip() for col in df.columns]
                melted = (
                    df.reset_index()
                      .melt(id_vars=['Date'],
                            var_name='Type_Ticker',
                            value_name='Value')
                )
                melted[['Type','Ticker']] = (
                    melted['Type_Ticker']
                          .str.split('_', expand=True)
                )
                pivot = melted.pivot(index='Ticker',
                                     columns='Type',
                                     values='Value')[['Tactic','Strategic']]
                combined = (
                    pivot.join(
                        self.prices_df.loc[date].rename('Price'),
                        how='left'
                    )
                    .fillna(0)
                )
                combined.to_excel(writer, sheet_name=f"{date_id} - {date}")
        wb.close()

        # market values & total return
        mv_df, summed_mv_df = self.market_value_calculator.calculate_market_value(
            self.prices_df,
            quantities_df
        )
        cash_df = cash_df.reindex(summed_mv_df.index).fillna(method='ffill')
        summed_mv_df = summed_mv_df.add(cash_df, fill_value=0)

        self.calculate_and_plot_total_return(summed_mv_df)