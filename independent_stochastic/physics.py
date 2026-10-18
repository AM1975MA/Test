"""Self-contained numerical physics: robust latent drift, online market filter, no ML dependency."""
import numpy as np
import pandas as pd

def daily_asof(close,signal):
    h=close.loc[:signal]
    return np.log(h/h.shift()).replace([np.inf,-np.inf],np.nan)

def common_market_filter(daily):
    r=daily.mean(axis=1).where(daily.count(axis=1)>=10).dropna().tail(270)
    if len(r)<225:
        return {"shock":False,"down":False,"flag":False,
                "vol21":None,"vol126":None}
    v=r.to_numpy(float);index=np.exp(np.cumsum(v))
    down=bool(index[-1]<np.mean(index[-200:]))
    v21=float(np.std(v[-21:],ddof=1))
    v126=float(np.std(v[-126:],ddof=1))
    shock=bool(v21>v126>0)
    return {"shock":shock,"down":down,"flag":shock and down,
            "vol21":v21,"vol126":v126}

def robust_latent_drift(close,signal):
    """Approximate Student-t(5) two-speed causal Kalman observer; no training labels."""
    h=close.loc[:signal].dropna()
    h=h[h>0]
    if len(h)<253:return (float("nan"),)*3
    mon=h.resample("ME").last().dropna()
    rr=np.diff(np.log(mon.to_numpy(float)))
    rr=rr[np.isfinite(rr)][-60:]
    if len(rr)<36:return (float("nan"),)*3
    loc=float(np.median(rr))
    scale=1.4826*float(np.median(np.abs(rr-loc)))
    obs_var=max(scale*scale,.015**2)
    output=[]
    for ratio in (1./36.,1./9.):
        q=ratio*obs_var;mu=0.;variance=obs_var;loglike=0.
        for x in rr:
            predvar=variance+q
            innovation=float(x-mu)
            S=predvar+obs_var
            u=innovation*innovation/max(S,1e-12)
            weight=float(np.clip(6./(5.+u),.15,1.))
            gain=predvar/(predvar+obs_var/weight)
            mu+=gain*innovation
            variance=max((1.-gain)*predvar,1e-12)
            loglike+=-.5*np.log(S)-3.*np.log1p(u/5.)
        output.append((loglike,mu,variance+q))
    ll=np.array([v[0] for v in output])
    probs=np.exp(ll-np.max(ll));probs/=probs.sum()
    mu=float(sum(probs[i]*output[i][1] for i in range(2)))
    posterior_var=float(sum(probs[i]*(output[i][2]+(output[i][1]-mu)**2)
        for i in range(2)))
    return mu,posterior_var,obs_var
