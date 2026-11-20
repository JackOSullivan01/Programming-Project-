import pandas as pd
import numpy as np
import plotly.graph_objects as go
from scipy import stats
import gradio as gr


# ==============================================================================
# 1. DATA LOADING & PREPROCESSING ENGINE
# ==============================================================================
def load_and_prepare_data(filepath: str = "industry_returns_clean.csv") -> pd.DataFrame:
    """
    Loads daily industry return series, parses datetime index,
    and ensures clean numeric formatting across all sector columns.
    """
    df = pd.read_csv(filepath)
    df["Date"] = pd.to_datetime(df["Date"])
    df = df.set_index("Date").sort_index()
    return df


def resample_returns(df: pd.DataFrame, frequency: str) -> pd.DataFrame:
    """
    Compounds daily simple returns into the chosen return frequency
    (Daily, Weekly, Monthly, or Quarterly) using geometric linking:
    R_period = prod(1 + r_t) - 1
    """
    freq_map = {
        "Daily": None,
        "Weekly": "W-FRI",
        "Monthly": "ME",
        "Quarterly": "QE",
    }
    rule = freq_map.get(frequency)
    if rule is None:
        return df

    # Compound daily returns accurately across each period
    compounded = (1.0 + df).resample(rule).prod() - 1.0
    return compounded.dropna(how="all")