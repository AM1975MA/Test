"""Pure frozen Tail-channel scoring, no Compact21 contribution."""
from __future__ import annotations
import numpy as np
import pandas as pd

def score_channel(ensemble,calendar,tickers,channel):
    dates=pd.DatetimeIndex(calendar.signal_date)
    if len(dates)!=114 or len(tickers)!=149:
        raise ValueError("Original monthly cohort changed")
    def matrix(column):
        out=ensemble.pivot(index="signal_date",columns="ticker",values=column).reindex(
            index=dates,columns=tickers).to_numpy(float)
        if out.shape!=(114,149) or not np.isfinite(out).all():
            raise ValueError("Missing frozen Tail source "+column)
        return out
    et=matrix("ET_TAIL");xb=matrix("XGB_TAIL")
    if channel=="HYBRID":
        raw=.60*et+.40*xb
    elif channel=="ET":
        raw=et
    elif channel=="XGB":
        raw=xb
    else:
        raise ValueError(channel)
    smoothed=.40*raw+.30*np.vstack((raw[:1],raw[:-1])) + .30*np.vstack((raw[:1],raw[:1],raw[:-2]))
    out=np.power(np.clip(smoothed,0.,1.),1.10)
    if not np.isfinite(out).all():raise ValueError("Nonfinite Tail-only")
    return out

def ridge_tail_only(annual,calendar,tickers):
    a=annual.copy()
    a["signal_date"]=pd.to_datetime(a.signal_date)
    if "tail" not in a:raise ValueError("Missing annual OOS Titanium Ridge Tail")
    ranks=a.groupby("signal_date")["tail"].rank(method="average",pct=True)
    a["pure_ridge_tail"]=ranks
    result=a.pivot(index="signal_date",columns="ticker",values="pure_ridge_tail").reindex(
        index=pd.DatetimeIndex(calendar.signal_date),columns=tickers).to_numpy(float)
    if result.shape!=(114,149) or not np.isfinite(result).all():
        raise ValueError("Ridge Tail pure full cohort unavailable")
    return result
