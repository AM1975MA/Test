"""R0-P isolated research-only source-faithful downside-volatility numerical guard.

This file is not part of ETF Trader production. epsilon=0 gives the exact
current formula; epsilon>0 is an exploratory input-sign deadband, NOT a
recommended live trading configuration or automatically calibrated uncertainty.
"""
import numpy as np
import pandas as pd


def rolling_downvol_guard(log_returns: pd.DataFrame, horizon: int,
                          epsilon: float = 0.0, min_periods=None):
    if horizon <= 0 or epsilon < 0:
        raise ValueError("horizon must be positive and epsilon nonnegative")
    n = max(10, horizon // 2) if min_periods is None else min_periods
    return (log_returns.where(log_returns < -epsilon)
            .rolling(horizon, min_periods=n).std(ddof=0)
            * np.sqrt(252))


def cs_robust_dev(v: pd.DataFrame):
    median = v.median(axis=1)
    mad = v.sub(median, axis=0).abs().median(axis=1).replace(0, np.nan)
    return v.sub(median, axis=0).div(1.4826 * mad, axis=0).clip(-8, 8)
