"""As-of-only risk observers; no future information, no refitted return labels."""
import math
import numpy as np
import pandas as pd
from research_bayes_europe.experiment import robust_kalman_score

def top(score,n=2):
    score=np.asarray(score,float)
    if np.isfinite(score).sum()<n:raise ValueError("insufficient ranks")
    return np.argsort(-np.where(np.isfinite(score),score,-1e18),kind="stable")[:n].tolist()

def invweights(a,b):
    if not (np.isfinite(a) and np.isfinite(b) and a>0 and b>0):return [.5,.5]
    q=1/np.array([a,b],float)
    q=np.clip(q/q.sum(),.2,.8)
    return (q/q.sum()).tolist()

def daily_asof(close,signal):
    h=close.loc[:signal]
    return np.log(h/h.shift()).replace([np.inf,-np.inf],np.nan)

def market(daily):
    r=daily.mean(axis=1).where(daily.count(axis=1)>=10).dropna().tail(270)
    if len(r)<225:return dict(shock=False,down=False,flag=False,vol21=None,vol126=None)
    v=r.to_numpy(float); index=np.exp(np.cumsum(v))
    down=bool(index[-1]<np.mean(index[-200:]))
    v21=float(np.std(v[-21:],ddof=1));v126=float(np.std(v[-126:],ddof=1))
    shock=bool(v21>v126>0)
    return dict(shock=shock,down=down,flag=shock and down,vol21=v21,vol126=v126)

def entropy(daily):
    # Shrunk eigenvalue entropy is a risk diagnostic, not predictive alpha.
    a=daily.tail(126).dropna(axis=1,thresh=110).to_numpy(float)
    if a.shape[0]<110 or a.shape[1]<8:return None
    means=np.nanmean(a,axis=0)
    for i in range(a.shape[1]):a[~np.isfinite(a[:,i]),i]=means[i]
    sd=np.std(a,axis=0,ddof=1);a=a[:,np.isfinite(sd)&(sd>1e-6)]
    if a.shape[1]<8:return None
    corr=np.corrcoef(a,rowvar=False)
    if not np.isfinite(corr).all():return None
    corr=.8*corr+.2*np.eye(corr.shape[0])
    eig=np.maximum(np.linalg.eigvalsh(corr),0)
    p=eig/eig.sum();ent=float(np.exp(-np.sum(p[p>0]*np.log(p[p>0]))))
    return dict(n=int(len(p)),n_eff=ent,fraction=ent/len(p),lambda1=float(eig[-1]/eig.sum()))

def observer(close,signal,picks,daily):
    vol={};kalm={}
    for t in picks:
        v=daily[t].dropna().tail(63).to_numpy(float)
        vol[t]=float(np.std(v,ddof=1)*np.sqrt(21)) if len(v)>=45 else float("nan")
        mu,pv,ov=robust_kalman_score(close[t],signal)
        kalm[t]=dict(mu=float(mu),unc=float(np.sqrt(pv+ov))
                     if np.isfinite(pv+ov) and pv+ov>0 else float("nan"))
    return vol,kalm

POLICIES=("H0_RH_5050","H1_HIST_INV_VOL","H2_KALMAN_UNCERTAINTY",
          "H3_MARKET_REGIME","H4_EIGEN_ENTROPY_GATE",
          "H5_RANK_HYSTERESIS","H6_KALMAN_AND_REGIME")

def allocate(policy,ordered,previous,vol,kalm,reg,ent):
    picks=list(ordered[:2])
    if policy=="H5_RANK_HYSTERESIS" and previous:
        retained=[t for t in previous if t in ordered[:5]]
        picks=(retained+[t for t in ordered if t not in retained])[:2]
    if policy=="H1_HIST_INV_VOL":weights=invweights(vol[picks[0]],vol[picks[1]])
    elif policy in ("H2_KALMAN_UNCERTAINTY","H6_KALMAN_AND_REGIME"):
        weights=invweights(kalm[picks[0]]["unc"],kalm[picks[1]]["unc"])
    else:weights=[.5,.5]
    scale=1.
    if policy in ("H3_MARKET_REGIME","H6_KALMAN_AND_REGIME") and reg["flag"]:
        scale=.5
    if policy=="H4_EIGEN_ENTROPY_GATE" and ent:
        if ent["fraction"]<.25 and reg["shock"]:scale=.5
    return picks,dict(zip(picks,[float(x*scale) for x in weights]))

def synthetic_gate():
    dates=pd.bdate_range("2015-01-02",periods=1200)
    p=np.exp(np.cumsum(np.sin(np.arange(len(dates))/25)*.006+.0002))
    s=pd.Series(p,index=dates);date=dates[1000]
    altered=s.copy();altered.loc[altered.index>date]*=1017.
    x=robust_kalman_score(s,date)
    assert np.allclose(x,robust_kalman_score(altered,date),equal_nan=True)
    a=pd.DataFrame({"a":s,"b":s*1.4})
    b=pd.DataFrame({"a":altered,"b":altered*1.4})
    assert market(daily_asof(a,date))==market(daily_asof(b,date))
    assert np.allclose(invweights(.02,.02),[.5,.5])
    assert np.allclose(invweights(.001,1.),[.8,.2])
    assert top([1.,2.,np.nan])==[1,0]
    print("ASOF_SYNTHETIC_GATE_PASS",flush=True)
