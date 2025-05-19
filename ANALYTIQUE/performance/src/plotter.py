import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from datetime import timedelta
from .config import OUTPUT_DIR

class Plotter:
    @staticmethod
    def plot_investment_evolution(investment_values_bni_hec,
                                  investment_values_reference,
                                  portfolio_bni_hec,
                                  initial_investment):
        """
        Plot the evolution of the investment over time for both
        the portfolio and reference. Saves a PDF into DATA_DIR
        and then shows the chart.
        """
        # Align the reference series to the portfolio's daily index
        ref_aligned = investment_values_reference.reindex(
            investment_values_bni_hec.index,
            method='ffill'
        )

        # Compute the ratio
        ratio = investment_values_bni_hec / ref_aligned - 1

        fig, ax1 = plt.subplots(figsize=(12, 6))
        plt.grid(axis='y')

        # Plot portfolio vs. reference
        ax1.plot(investment_values_bni_hec.index,
                 investment_values_bni_hec,
                 label=f'Portefeuille {portfolio_bni_hec}',
                 linewidth=2, color="darkred")
        ax1.plot(ref_aligned.index,
                 ref_aligned,
                 label='Portefeuille de Référence',
                 linewidth=2, color="navy")

        ax1.spines[['top', 'right', 'left']].set_visible(False)
        ax1.set_ylabel('Investment Value ($)', fontsize=12)
        ax1.set_title(
            f"Évolution d'un investissement de {initial_investment}$\n"
            f"Portefeuille {portfolio_bni_hec}",
            fontsize=16, fontweight='bold'
        )
        ax1.legend()

        # Twin axis for ratio
        ax2 = ax1.twinx()
        ax2.spines[['top', 'right', 'left']].set_visible(False)
        ax1.tick_params(left=False)
        ax2.tick_params(right=False, left=False)

        # Compute twin-axis limits
        left_min, left_max = ax1.get_ylim()
        top = left_max / initial_investment - 1
        bot = 1 - left_min / initial_investment
        ax2.set_ylim([-bot, top])

        # Fill positive/negative areas
        ax2.fill_between(investment_values_bni_hec.index,
                         ratio,
                         where=(ratio > 0),
                         alpha=0.3,
                         interpolate=True, color="darkred")
        ax2.fill_between(investment_values_bni_hec.index,
                         ratio,
                         where=(ratio < 0),
                         alpha=0.3,
                         interpolate=True, color="navy")
        ax2.set_ylabel('Ratio', fontsize=12)

        # Format x-axis as months
        start_date = investment_values_bni_hec.index[0] - timedelta(days=1)
        end_date   = investment_values_bni_hec.index[-1] + timedelta(days=1)
        ax1.set_xlim([start_date, end_date])
        ax1.xaxis.set_major_locator(mdates.MonthLocator(bymonthday=1))
        ax1.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m'))
        plt.setp(ax1.xaxis.get_majorticklabels(), rotation=45, ha='right')

        plt.tight_layout()

        # --- Save to OUTPUT_DIR ---
        filename = f"evolution_{portfolio_bni_hec}.pdf"
        save_path = OUTPUT_DIR / filename
        plt.savefig(save_path, dpi=300)

        #plt.show()  
