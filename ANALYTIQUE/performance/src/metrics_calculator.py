import numpy as np

class MetricsCalculator:
    def __init__(self, fund_returns, benchmark_returns, window):
        self.excess_returns = fund_returns - benchmark_returns
        self.window = window

    def calculate_value_added_average(self):
        """Calculate Valeur Ajoutée Moyenne (VAM)"""
        avg_excess_return = self.excess_returns.rolling(window=self.window).mean()
        value_added_avg = (1 + avg_excess_return) ** 52 - 1  # Annualizing the average excess return
        return value_added_avg * 10000  

    def calculate_active_risk(self):
        """Calculate Risque Actif (RA)"""
        rolling_variance = self.excess_returns.rolling(window=self.window).var()
        active_risk = np.sqrt(52 * rolling_variance)
        return active_risk * 10000 

    def calculate_information_ratio(self):
        """Calculate the Information Ratio (RI)"""
        vam = self.calculate_value_added_average()
        active_risk = self.calculate_active_risk()
        information_ratio = vam / active_risk 
        return information_ratio
