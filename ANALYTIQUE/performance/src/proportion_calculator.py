# performance_analysis/src/proportion_calculator.py

import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from datetime import timedelta

class ProportionCalculator:
    def __init__(self, market_value_df, summed_market_value_df):
        self.market_value_df = market_value_df
        self.summed_market_value_df = summed_market_value_df

    def calculate_proportions(self):
        """Calculate the proportion of each asset's value by its total type"""
        return self.market_value_df.div(self.summed_market_value_df, level='Type', axis=1)

    def get_latest_data(self, proportion_df):
        """Get the latest date and corresponding data from the proportions DataFrame"""
        last_date = proportion_df.index[-1]
        latest_data = proportion_df.loc[last_date]

        # Ensure latest_data is a DataFrame, not a Series
        if isinstance(latest_data, pd.Series):
            latest_data = latest_data.to_frame().T

        return last_date, latest_data

    def plot_pie_charts_by_type(self, latest_data, last_date):
        """Plot pie charts for the latest data by type."""
        unique_types = latest_data.columns.get_level_values('Type').unique()

        fig, axes = plt.subplots(1, len(unique_types), figsize=(15, 7))
        fig.suptitle(f"Proportion of Asset Types as of {last_date.strftime('%Y-%m-%d')}", fontsize=16)

        for i, asset_type in enumerate(unique_types):
            proportions = latest_data.xs(asset_type, level='Type', axis=1).T.squeeze()
            proportions = proportions[proportions != 0].dropna()
            labels = [f"{label} (short)" if value < 0 else label for label, value in proportions.items()]

            if not proportions.empty:
                axes[i].pie(
                    proportions.abs(),
                    labels=labels,
                    autopct='%1.2f%%',
                    startangle=90,
                    pctdistance=0.85,
                    wedgeprops={'edgecolor': 'white', 'linewidth': 1}
                )
                axes[i].set_title(f"{asset_type}")
            else:
                axes[i].set_title(f"No valid data for {asset_type}")

        plt.tight_layout()
        # plt.show()

    def calculate_and_plot_proportions(self):
        """Calculate proportions and plot pie charts for the latest data by type."""
        proportion_df = self.calculate_proportions()
        last_date, latest_data = self.get_latest_data(proportion_df)
        self.plot_pie_charts_by_type(latest_data, last_date)
