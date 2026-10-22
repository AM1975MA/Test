"""L11 independent COMEX vs LME copper basis monitor, OBSERVE ONLY.

COMEX HG and LME 3m are distinct underlying copper markets.
WisdomTree COPA.L London-listed uses COMEX-linked Bloomberg copper prices.
The observer needs actual historical LME 3m quotes, never a London ETF proxy.
No price scraping, no invented series, no automatic trading decision.
"""
from __future__ import annotations
from dataclasses import dataclass
import numpy as np
import pandas as pd

LBS_PER_METRIC_TONNE=2204.6226218488
MARKETS={"COMEX_HG_USD_PER_LB_3M","LME_CU_USD_PER_TONNE_3M"}

@dataclass(frozen=True)
class BasisObservation:
    status: str
    asof_utc: str
    reason: str
    comex_quote_utc: str | None=None
    lme_quote_utc: str | None=None
    basis_pct: float | None=None
    basis_zscore_63: float | None=None
    prior_pairs: int=0
    divergence_alert: bool=False
    trading_action: str="NONE_OBSERVE_ONLY"

def _validate(q:pd.DataFrame)->pd.DataFrame:
    need={"quote_ts_utc","market","price"}
    if not need.issubset(q):raise ValueError("Missing quote_ts_utc, market or price")
    x=q[list(need)].copy()
    x.quote_ts_utc=pd.to_datetime(x.quote_ts_utc,utc=True,errors="raise")
    if x.quote_ts_utc.isna().any():raise ValueError("Unparseable UTC timestamps")
    if not x.market.isin(MARKETS).all():raise ValueError("Need actual underlying COMEX and LME 3m markets; no London ETC proxy")
    x.price=pd.to_numeric(x.price,errors="raise")
    if (x.price<=0).any() or not np.isfinite(x.price).all():raise ValueError("Invalid underlying price")
    if x.duplicated(["quote_ts_utc","market"]).any():raise ValueError("Duplicate timestamps; certify source before use")
    return x.sort_values("quote_ts_utc")

def monitor_weekly_basis(quotes:pd.DataFrame,cutoff_utc:str|pd.Timestamp,
    *,minimum_history:int=63,max_age:pd.Timedelta=pd.Timedelta("96h"),
    cross_lag:pd.Timedelta=pd.Timedelta("36h"),
    high_basis:float=.10,high_z:float=2.0)->BasisObservation:
    """As-of before weekly US open; quotes after cutoff NEVER used.
    Independent LME comparable 3m tenor/roll quality must be certified
    upstream. Not a CPER price forecast or investment/trading algorithm.
    """
    ts=pd.Timestamp(cutoff_utc)
    if ts.tzinfo is None:raise ValueError("UTC cutoff must be timezone aware")
    ts=ts.tz_convert("UTC")
    q=_validate(quotes)
    q=q[q.quote_ts_utc<=ts]
    a=q.loc[q.market=="COMEX_HG_USD_PER_LB_3M",["quote_ts_utc","price"]].rename(
        columns={"quote_ts_utc":"comex_ts","price":"comex_usd_lb"}).sort_values("comex_ts")
    b=q.loc[q.market=="LME_CU_USD_PER_TONNE_3M",["quote_ts_utc","price"]].rename(
        columns={"quote_ts_utc":"lme_ts","price":"lme_usd_tonne"}).sort_values("lme_ts")
    if a.empty or b.empty:return BasisObservation("ABSTAIN",ts.isoformat(),"MISSING_INDEPENDENT_MARKET")
    p=pd.merge_asof(a,b,left_on="comex_ts",right_on="lme_ts",
         direction="backward",tolerance=cross_lag).dropna()
    if p.empty:return BasisObservation("ABSTAIN",ts.isoformat(),"NO_CAUSAL_COMPARABLE_QUOTES")
    v=p.iloc[-1]
    if ts-v.comex_ts>max_age or ts-v.lme_ts>max_age:
        return BasisObservation("ABSTAIN",ts.isoformat(),"STALE_QUOTES",
          comex_quote_utc=v.comex_ts.isoformat(),lme_quote_utc=v.lme_ts.isoformat())
    if len(p)<=minimum_history:
        return BasisObservation("ABSTAIN",ts.isoformat(),"INSUFFICIENT_PRIOR_DAYS",
                prior_pairs=max(0,len(p)-1))
    basis=p.comex_usd_lb.to_numpy(float)*LBS_PER_METRIC_TONNE/p.lme_usd_tonne.to_numpy(float)-1
    previous=basis[-(minimum_history+1):-1]
    mean=float(np.mean(previous));sd=float(np.std(previous,ddof=1))
    if sd<=0:return BasisObservation("ABSTAIN",ts.isoformat(),"INSUFFICIENT_BASIS_VARIATION")
    today=float(basis[-1]);z=float((today-mean)/sd)
    return BasisObservation("OBSERVATION_ONLY",ts.isoformat(),
       "Market quote source and contract rolling must be validated before economic backtest",
       comex_quote_utc=v.comex_ts.isoformat(),lme_quote_utc=v.lme_ts.isoformat(),
       basis_pct=today*100,basis_zscore_63=z,prior_pairs=len(previous),
       divergence_alert=bool(today>=high_basis and z>=high_z))
