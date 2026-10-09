"""Causal cleanup of defective threshold-sensitive downside volatility features.

The original downvol family uses the sample standard deviation of negative
returns with a minimum *negative-count* threshold, introducing NaN at an
arbitrary crossing of that threshold even with complete OHLC history.

This replacement is an explicit *semantic change*, not an imputation of raw
market data: downside root-mean-square with all h observations, positive returns
contributing zero, and strictly complete historical windows. Full-window
missing raw data remain NaN. It is never applied to canonical production files.
"""
from __future__ import annotations

import numpy as np
import pandas as pd


def downside_semideviation(log_returns: pd.DataFrame, horizon: int) -> pd.DataFrame:
    """Annualized zero-target downside semideviation using only past h returns."""
    if isinstance(horizon, bool) or not isinstance(horizon, int) or horizon < 2:
        raise ValueError("Invalid rolling window")
    if not isinstance(log_returns, pd.DataFrame) or log_returns.empty:
        raise ValueError("Expected nonempty returns frame")
    if not log_returns.index.is_unique or not log_returns.index.is_monotonic_increasing:
        raise ValueError("Non-monotone/duplicated return index")
    source=log_returns.astype(float)
    if np.isinf(source.to_numpy(float)).any():
        raise ValueError("Infinite return input")
    return np.sqrt(source.clip(upper=0).pow(2).rolling(horizon,min_periods=horizon).mean()*252.0)


def repair_downvol_family(panel: pd.DataFrame, log_returns: pd.DataFrame,
                          dates: pd.DatetimeIndex, horizons=(21,63,126)) -> pd.DataFrame:
    """Return a new complete source panel, replacing all raw/pct/dev columns together."""
    from etf_trader.source_only import kernel as k
    horizons=tuple(horizons)
    if not horizons or any(h not in (21,63,126) for h in horizons) or len(set(horizons))!=len(horizons):
        raise ValueError("Invalid downside feature horizon")
    keys=["signal_date","ticker"]
    expected=[f"downvol{h}{suffix}" for h in horizons for suffix in ("","_pct","_dev")]
    if not set(keys+expected).issubset(panel.columns) or panel.empty:
        raise ValueError("Missing/empty canonical panel/schema")
    if panel[keys].isna().any().any() or panel.duplicated(keys).any():
        raise ValueError("Invalid or repeated prediction keys")
    dates=pd.DatetimeIndex(dates)
    if not dates.is_unique or not dates.is_monotonic_increasing:
        raise ValueError("Invalid feature calendar")
    if panel.ticker.astype(str).isin(log_returns.columns).all() is False:
        raise ValueError("Unknown ticker in original returns")
    if not pd.to_datetime(panel.signal_date).isin(dates).all():
        raise ValueError("Original panel date outside frozen calendar")
    original=panel.copy(deep=True)
    z=panel.copy(deep=True)
    ids=pd.MultiIndex.from_arrays([pd.to_datetime(panel.signal_date).to_numpy(),panel.ticker.to_numpy()],
                                  names=["signal_date","ticker"])
    for h in horizons:
        base=downside_semideviation(log_returns,h).reindex(dates)
        sources={"":base,"_pct":k.cs_pct(base),"_dev":k.cs_robust_dev(base)}
        for suffix,df in sources.items():
            # Preserve declared original row ordering; no join expansions.
            df.columns.name=None
            values=df.stack(dropna=False).reindex(ids).to_numpy(dtype=float)
            z[f"downvol{h}{suffix}"]=values
    frozen=[col for col in original.columns if col not in expected]
    pd.testing.assert_frame_equal(z[frozen],original[frozen],check_exact=True)
    return z
