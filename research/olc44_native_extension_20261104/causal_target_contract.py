"""OLC44-N2: controlled point-in-time universe eligibility and target rebuild.

Training target is per-date cross-sectional.  Future returns and outcome
maturity are NEVER used to decide whether an ETF is eligible for scoring.
Original-only replay must be exact before a new roster is allowed. Once the
training roster changes, its old tickers' percentile ranks need NOT be equal.
"""
from __future__ import annotations
import numpy as np
import pandas as pd

HORIZONS=(21,42,63)
TARGET_WEIGHTS=(0.45,0.35,0.20)

def signal_eligible(prices:pd.DataFrame,signal_date,lookback:int=252,min_opens:int=500):
    """Eligibility from observed price dates only, no future information.

    Do not use a 2026-fund lookup to backfill price availability before its
    inception; the caller must supply contemporaneously traded line identity.
    """
    required={"date","open","high","low","close"}
    if not required.issubset(prices.columns):raise ValueError("Missing OHLC field(s)")
    d=prices.copy()
    d["date"]=pd.to_datetime(d["date"])
    if d.date.duplicated().any():raise ValueError("Duplicate observation dates")
    dt=pd.Timestamp(signal_date)
    q=d.loc[d.date.lt(dt)].sort_values("date")
    valid=q.open.gt(0)&q.close.gt(0)&np.isfinite(q.open)&np.isfinite(q.close)
    q=q.loc[valid]
    if len(q)<max(lookback,min_opens):
        return False
    tail=q.tail(lookback)
    if (dt-tail.date.iloc[-1]).days>7:
        return False
    hl=(np.isfinite(tail.high)&np.isfinite(tail.low)
        & tail.high.ge(tail[["open","close"]].max(axis=1))
        & tail.low.le(tail[["open","close"]].min(axis=1))
        & tail.high.ge(tail.low))
    return bool(hl.all())

def original_relative_target(group:pd.DataFrame):
    """Return OLC11/OLC14-style relative target for a *complete* date cohort.

    The target is only legal for training after the longest of the three
    holding-period labels has fully matured.
    """
    required={"signal_date","ticker","fwd_ret_21","fwd_ret_42","fwd_ret_63"}
    if not required.issubset(group.columns):
        raise ValueError("Missing forward return column")
    if group.signal_date.nunique()!=1:
        raise ValueError("Expected exactly one signal date")
    if group.ticker.duplicated().any() or len(group)<2:
        raise ValueError("Duplicate/small group")
    future=group[[f"fwd_ret_{h}" for h in HORIZONS]].astype(float)
    if not np.isfinite(future.to_numpy()).all():
        raise ValueError("Incomplete target cohort: do not drop missing members")
    if (future<=-1).any().any():
        raise ValueError("Impossible next-open wealth return")
    pct=future.rank(axis=0,method="average",pct=True)
    res=sum(w*pct[f"fwd_ret_{h}"].pow(1.5)
            for w,h in zip(TARGET_WEIGHTS,HORIZONS))
    out=group[["signal_date","ticker"]].copy()
    for h in HORIZONS:
        out[f"target_rank_{h}"]=pct[f"fwd_ret_{h}"].to_numpy()
    out["TARGET"]=res.to_numpy()
    return out

def mature_groups_only(labels:pd.DataFrame,cutoff):
    """Whole-month maturity: no partial cohort or leakage of future 63-day labels."""
    req={"signal_date","ticker","exit_date_63","fwd_ret_21","fwd_ret_42","fwd_ret_63"}
    if not req.issubset(labels.columns):
        raise ValueError("Missing maturity fields")
    df=labels.copy()
    for col in ("signal_date","exit_date_63"):
        df[col]=pd.to_datetime(df[col])
    cut=pd.Timestamp(cutoff)
    out=[]
    for date,group in df.groupby("signal_date",sort=True):
        if date>=cut:
            continue
        if group.exit_date_63.isna().any() or not bool(group.exit_date_63.lt(cut).all()):
            continue
        if not np.isfinite(group[[f"fwd_ret_{h}" for h in HORIZONS]].to_numpy(float)).all():
            continue
        out.append(original_relative_target(group))
    return pd.concat(out,ignore_index=True) if out else pd.DataFrame(
        columns=["signal_date","ticker","target_rank_21","target_rank_42","target_rank_63","TARGET"])

def compare_base_and_extended(base:pd.DataFrame,extended:pd.DataFrame):
    """Show base old-ticker score/target rank shift caused ONLY by cohort membership.

    Requires identical old returns for matching ticker/date. Rank changes
    are expected in extended training: we must not demand equality.
    """
    key=["signal_date","ticker"];forward=[f"fwd_ret_{h}" for h in HORIZONS]
    if base.duplicated(key).any() or extended.duplicated(key).any():
        raise ValueError("Non-unique ticker/date in source panel")
    verify=base[key+forward].merge(extended[key+forward],on=key,how="left",validate="one_to_one",indicator=True,suffixes=("_base","_ext"))
    if not verify._merge.eq("both").all():
        raise ValueError("Base universe not preserved in expanded panel")
    for c in forward:
        if not np.allclose(verify[c+"_base"],verify[c+"_ext"],atol=0,rtol=0,equal_nan=True):
            raise ValueError("Old ETF forward return was modified in expanded input")
    a=pd.concat([original_relative_target(g) for _,g in base.groupby("signal_date",sort=True)],ignore_index=True)
    b=pd.concat([original_relative_target(g) for _,g in extended.groupby("signal_date",sort=True)],ignore_index=True)
    joined=a.merge(b,on=key,how="inner",validate="one_to_one",suffixes=("_old","_ext"))
    joined["delta_target"]=joined.TARGET_ext-joined.TARGET_old
    joined["changed"]=np.abs(joined.delta_target)>1e-14
    return joined
