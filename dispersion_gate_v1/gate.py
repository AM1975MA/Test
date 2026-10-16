"""Causal cross-asset dispersion, with a frozen annual past-only median."""
import numpy as np
import pandas as pd

def historical_dispersion(close):
    x=close.loc[(close.index>='2011-01-01')&(close.index<='2026-06-30')].copy()
    if not x.index.is_unique or not x.index.is_monotonic_increasing:raise ValueError('Invalid calendar')
    old=x.shift(21)
    valid=np.isfinite(x)&np.isfinite(old)&(x>0)&(old>0)
    returns=(x/old-1).where(valid)
    dates=pd.Series(x.index,index=x.index).groupby(x.index.to_period('M')).last()
    out=[]
    for date in dates:
        row=returns.loc[date];n=int(row.notna().sum())
        if n<100:
            if date>=pd.Timestamp('2012-01-01'):raise ValueError('Insufficient dispersion universe')
            continue
        out.append(dict(signal_date=date,dispersion=float(row.std(ddof=1)),eligible=n))
    return pd.DataFrame(out)

def annual_gate(history,year):
    cutoff=pd.Timestamp(year,1,1)
    past=history[(history.signal_date>='2012-01-01')&(history.signal_date<cutoff)]
    if len(past)<12 or not np.isfinite(past.dispersion).all():raise ValueError('Insufficient threshold history')
    threshold=float(past.dispersion.median())
    out=history[history.signal_date.dt.year==year].copy()
    if out.empty or not np.isfinite(out.dispersion).all():raise ValueError('Missing current dispersion')
    out['threshold']=threshold;out['use_full']=out.dispersion>=threshold
    out['calibration_last_signal']=past.signal_date.max();out['calibration_queries']=len(past)
    if not (out.calibration_last_signal<cutoff).all():raise ValueError('Future calibration')
    return out.reset_index(drop=True)
