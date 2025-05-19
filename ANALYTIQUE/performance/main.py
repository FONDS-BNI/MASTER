from src.config import CONFIG, DATA_DIR, OUTPUT_DIR, PPT_INPUT, PPT_OUTPUT
from src.portfolio_analysis import PortfolioAnalysis

def main():
    analysis = PortfolioAnalysis(CONFIG)
    analysis.run_analysis()

if __name__ == "__main__":
    main()
