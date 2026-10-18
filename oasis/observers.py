"""OASIS V1: completely price-only causal opportunity and crisis observations.

Prototype is not a verified point-in-time live ETF trading model.
No legacy ML predictions or trained ex-post price labels.
"""
from __future__ import annotations
import math
from statistics import NormalDist
import numpy as np
import pandas as pd

ONE_SIDED_ALPHA=.05
HORIZON=21
ASSUMED_SWITCH_LOG_HURDLE=.003
MIN_HOLD_DAYS=5
MAX_CANDIDATES_CHECKED=15

def prepare(close:pd.DataFrame):
    p=close.where(close>0).astype(float)
    ret=np.log(p/p.shift(1)).replace([np.inf,-np.inf],np.nan)
    mkt=ret.mean(axis=1).where(ret.count(axis=1)>=20)
    var=mkt.rolling(126,min_periods=90).var()
    beta=ret.rolling(126,min_periods=90).cov(mkt).div(var,axis=0).clip(-1.,3.)
    market63=mkt.rolling(63,min_periods=55).sum()
    market126=mkt.rolling(126,min_periods=105).sum()
    rel63=np.log(p/p.shift(63))-beta.mul(market63,axis=0)
    rel126=np.log(p/p.shift(126))-beta.mul(market126,axis=0)
    vol=ret.rolling(63,min_periods=50).std()
    # Future 21-session expected log relative growth from conservative,
    # one-sided factor-adjusted trailing momentum; not an exact posterior.
    score=.65*rel63/3. +.35*rel126/6. - .25*HORIZON*vol*vol
    recent21=np.log(p/p.shift(21))
    eligible=(p.notna() & (p.rolling(253,min_periods=220).count()>=220)
              & (vol>.0003) & (vol<.15)
              & (ret.abs().rolling(21,min_periods=15).max()<.5)
              & score.notna())
    score=score.where(eligible)
    return dict(price=p,ret=ret,mkt=mkt,beta=beta,score=score,
                vol=vol,ret21=recent21,eligible=eligible)

def ranks(observed,index):
    line=observed["score"].iloc[index].dropna()
    return sorted(line.index,key=lambda t:(-float(line[t]),str(t)))

def relative_lower_bound(observed,index,new:str,old:str,eligible_count:int):
    """Multiple-comparison-corrected credible-*proxy* margin, not validated coverage.

    SE inflated from 63-day paired realized volatility; this is an empirical
    uncertainty heuristic, NOT a posterior SE with proven frequentist coverage.
    """
    scores=observed["score"].iloc[index]
    diff=float(scores[new]-scores[old])
    if not np.isfinite(diff):return -math.inf
    recent=observed["ret21"].iloc[index]
    if not (np.isfinite(recent[new]) and np.isfinite(recent[old])):
        return -math.inf
    # Require the candidate's relative improvement to have a short-horizon leg.
    if float(recent[new]-recent[old])<=0:return -math.inf
    ret=observed["ret"].iloc[max(0,index-63):index+1]
    spread=(ret[new]-ret[old]).dropna().tail(63)
    if len(spread)<45:return -math.inf
    se=1.5*float(spread.std(ddof=1))*math.sqrt(HORIZON/len(spread))
    z=NormalDist().inv_cdf(1.-ONE_SIDED_ALPHA/max(1,eligible_count))
    # Include a conservative buy/sell/exit round-trip opportunity hurdle.
    return diff-z*se-ASSUMED_SWITCH_LOG_HURDLE

def observe_innovation(observed,index,name):
    r=observed["ret"].iloc[index]
    if name not in r.index or not np.isfinite(r[name]):return math.nan
    vol=observed["ret"][name].iloc[max(0,index-63):index].dropna()
    if len(vol)<45:return math.nan
    return float((r[name]-vol.median())/max(float(vol.std(ddof=1)),.001))

def switch_names(observed,index,held,age,policy,cp5=0.):
    """Pure as-of selector; held age measured in completed execution sessions."""
    ordered=ranks(observed,index)
    if len(ordered)<5:
        # A sparse as-of price panel on a cross-exchange holiday is NOT a
        # forecast that the missing ETFs suddenly became unattractive.
        # Retain existing holdings; never backfill with future prices.
        if held:return list(held),"SPARSE_ASOF_UNIVERSE_HOLD"
        if len(ordered)>=2:return ordered[:2],"SPARSE_ASOF_BOOTSTRAP"
        raise ValueError("fewer than two as-of eligible instruments")
    if policy=="P1_DAILY_GREEDY":
        return ordered[:2],"GREEDY"
    if policy=="P5_DAILY_TOP5_HYSTERESIS":
        prior=[t for t in held if t in ordered[:5]]
        return (prior+[t for t in ordered if t not in prior])[:2],"TOP5"
    if not held:
        return ordered[:2],"INITIAL_ENTRY"
    if len(held)!=2:
        # Partial fill recovery: preserve existing holdings; fill only vacancies.
        return (list(held)+[t for t in ordered if t not in held])[:2],"FILL_MISSING_POSITION"
    if any(t not in ordered for t in held):
        # A stale/missing as-of Close must not be interpreted as a rank loss.
        # Retain until an observed close proves a material opportunity change.
        # Missing *execution* Open is independently handled as an unfilled order.
        return list(held),"INCUMBENT_CLOSE_MISSING_HOLD"
    chosen=list(held)
    # Only one economically significant substitution per session.
    incumbent=min(chosen,key=lambda t:float(observed["score"].iloc[index][t]))
    if age.get(incumbent,0)<MIN_HOLD_DAYS:
        return chosen,"COOLDOWN"
    inspected=ordered[:MAX_CANDIDATES_CHECKED]
    neligible=len(ordered)
    best=None; margin=0.
    for candidate in inspected:
        if candidate in chosen:continue
        lb=relative_lower_bound(observed,index,candidate,incumbent,neligible)
        if policy=="P6_DAILY_ECONOMIC_HYSTERESIS_ONLY_CHANGEP":
            zin=observe_innovation(observed,index,candidate)
            if np.isfinite(zin) and abs(zin)>2.5 and cp5<.15:
                continue
        if lb>margin:
            margin=lb;best=candidate
    if best is None:return chosen,"HOLD_NO_NET_ECONOMIC_ADVANTAGE"
    return [best if t==incumbent else t for t in chosen],"CREDIBLE_OPPORTUNITY"

def _normal_pdf(x,mean,var):
    var=max(float(var),1e-6)
    return math.exp(-.5*(x-mean)**2/var)/math.sqrt(2*math.pi*var)

class ChangePointObserver:
    """Simple online Gaussian-mean BOCPD with new-regime predictive prior.

    Prior N(0,2), standardized return noise N(mu,1), hazard 1/80.
    90 truncated hypotheses. Its outputs are *causal approximations* only.
    """
    def __init__(self,max_run=90,hazard=1/80):
        self.p=np.zeros(max_run+1,float);self.p[0]=1.
        self.mu=np.zeros(max_run+1,float)
        self.precision=np.full(max_run+1,.5,float)
        self.hazard=hazard
    def update(self,x):
        if not math.isfinite(x):return float(sum(self.p[:5]))
        x=float(np.clip(x,-12,12))
        pred=np.array([_normal_pdf(x,m,1+1/v)
                       for m,v in zip(self.mu,self.precision)])
        cp=self.hazard*_normal_pdf(x,0,3.)
        growth=(1-self.hazard)*self.p*pred
        nxt=np.zeros_like(self.p)
        nxt[0]=cp
        nxt[1:]=growth[:-1]
        nxt[-1]+=growth[-1]
        denom=nxt.sum()
        if not np.isfinite(denom) or denom<=0:
            self.__init__()
            return .0
        nxt/=denom
        new_mu=np.zeros_like(self.mu);new_prec=np.zeros_like(self.precision)
        new_prec[0]=1.5;new_mu[0]=x/1.5
        new_prec[1:]=self.precision[:-1]+1
        new_mu[1:]=(self.precision[:-1]*self.mu[:-1]+x)/new_prec[1:]
        # Aging cap has an approximately merged state; use last hypothesis.
        self.p,self.mu,self.precision=nxt,new_mu,new_prec
        return float(nxt[:5].sum())

def market_states(features):
    mkt=features["mkt"].fillna(0.)
    idx=mkt.index
    rv21=mkt.rolling(21,min_periods=15).std()
    rv126=mkt.rolling(126,min_periods=95).std()
    trend21=mkt.rolling(21,min_periods=15).sum()
    trend10=mkt.rolling(10,min_periods=8).sum()
    # Share of the as-of universe delivering gains on the preceding 10 sessions.
    positive=(features["ret"].rolling(10,min_periods=8).sum()>0)
    breadth=positive.where(features["eligible"]).mean(axis=1,skipna=True)
    cp=ChangePointObserver()
    high=.2
    stress_history=0
    rows=[]
    for j in range(len(idx)):
        base_vol=rv126.iloc[j]
        x=float(mkt.iloc[j])
        if np.isfinite(base_vol) and base_vol>.0003:
            z=x/base_vol
            cp5=cp.update(z)
            pprior=.02*(1-high)+.91*high
            # HMM low vs high state with as-of standardized daily z.
            low=_normal_pdf(z,0,.75**2)*(1-pprior)
            hi=_normal_pdf(z,0,2.25**2)*pprior
            if low+hi>0:high=float(hi/(low+hi))
        else:
            z=0.;cp5=cp.update(0)
        m21=float(trend21.iloc[j]) if np.isfinite(trend21.iloc[j]) else 0.
        m10=float(trend10.iloc[j]) if np.isfinite(trend10.iloc[j]) else 0.
        b=float(breadth.iloc[j]) if np.isfinite(breadth.iloc[j]) else .5
        vol_ratio=float(rv21.iloc[j]/base_vol) if np.isfinite(base_vol) and base_vol>0 and np.isfinite(rv21.iloc[j]) else 1.
        shock=(m21<-.02 and b<.43 and (cp5>.3 or z< -2.75))
        ongoing=(m21<-.03 and b<.45 and (high>.70 or vol_ratio>1.35))
        if shock:
            state="SHOCK";stress_history=21
        elif ongoing:
            state="CONTINUATION";stress_history=21
        elif stress_history>0 and m10>.015 and b>.55:
            state="RECOVERY";stress_history-=1
        else:
            state="BREATHING"
            stress_history=max(0,stress_history-1)
        rows.append(dict(date=idx[j],state=state,crisis=state in ("SHOCK","CONTINUATION"),
                         cp_recent=float(cp5),hmm_high=float(high),
                         market21=m21,market10=m10,breadth10=b,
                         volatility_ratio=vol_ratio,z=float(z)))
    return pd.DataFrame(rows).set_index("date")
