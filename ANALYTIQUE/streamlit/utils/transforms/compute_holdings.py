from typing import Callable
import pandas as pd

def _pre_aggregate(df: pd.DataFrame) -> pd.DataFrame:
    """
    Aggregate transactions to daily net quantity per ticker.
    Expects df indexed by date and having 'Ticker' and 'Quantity' columns.
    """
    # ensure columns present
    df = df.copy()
    if 'Ticker' not in df.columns or 'Quantity' not in df.columns:
        raise ValueError("Ticker and Quantity must be present")
    # group by date (index) and ticker
    g = (df.groupby([df.index.date, 'Ticker'])['Quantity']
           .sum().unstack(fill_value=0.0))
    g.index = pd.to_datetime(g.index)
    return g.sort_index()

def build_holdings(df: pd.DataFrame,
                   start: pd.Timestamp,
                   end: pd.Timestamp,
                   fund: str,
                   trading_days_func: Callable[[pd.Timestamp, pd.Timestamp], pd.DatetimeIndex]) -> pd.DataFrame:
    """
    Build holdings timeseries (cumulative sum of daily net quantities) for selected fund.
    Parameter trading_days_func is injected for testability.
    """
    if df is None or df.empty:
        return pd.DataFrame()

    # fund filter
    if fund == "Strategic":
        work = df[df['Type'] == 'Strategic']
    elif fund == "Tactic":
        work = df[df['Type'] == 'Tactic']
    else:
        work = df

    if work.empty:
        return pd.DataFrame()

    grouped = _pre_aggregate(work)
    first_date = grouped.index.min().normalize()
    trading_days = trading_days_func(first_date, end)  # injected
    grouped = grouped.reindex(trading_days, fill_value=0.0)
    holdings_full = grouped.cumsum()
    # slice by requested window
    return holdings_full.loc[start:end]
