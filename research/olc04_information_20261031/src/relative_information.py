"""Past-price representations, never new external economic data.

Historical baskets are valued with quantities implied by current known weights.
They are explanatory paths, not a claim about positions held in the past.
"""
from __future__ import annotations
import numpy as np
import pandas as pd

REL_NAMES=['rel5','rel21','rel63','rel_accel','rel_dd63','rel_ma20','rel_slope21','rel_efficiency63','rel_upfreq21','rel_marketup63','rel_marketdown63','rel_breakout63']
PEER_NAMES=['peer_resid21_z','peer_resid63_z','peer_accel21_z','peer_breadth21','peer_mom63','peer_correlation','market_resid21_z','market_resid63_z','peer_dd63']
EXTRA_NAMES=REL_NAMES+['old_'+n for n in PEER_NAMES]+['d_'+n for n in PEER_NAMES]

def history(close:pd.DataFrame,asof)->pd.DataFrame:
    if not close.index.is_monotonic_increasing or not close.index.is_unique:raise ValueError('Sorted unique dates required')
    f=close.loc[:pd.Timestamp(asof)].copy()
    return f.where(f>0).ffill(limit=3)

def relative_from_history(h,old_weights,new_weights):
    ow=np.asarray(old_weights,float);nw=np.asarray(new_weights,float)
    if len(ow)!=h.shape[1] or len(nw)!=h.shape[1] or min(ow.min(),nw.min())<0:raise ValueError('Invalid weights')
    if not np.isclose(ow.sum(),1) or not np.isclose(nw.sum(),1):raise ValueError('Weights must sum to one')
    active=(ow>1e-14)|(nw>1e-14);p=h.iloc[-64:].to_numpy(float)
    if len(p)<64 or not np.isfinite(p[:,active]).all():return np.full(12,np.nan)
    norm=p[:,active]/p[-1,active];old=norm@ow[active];new=norm@nw[active]
    z=np.log(new/old);dz=np.diff(z);market=np.nanmedian(np.diff(np.log(p),axis=0),axis=1)
    r5=z[-1]-z[-6];r21=z[-1]-z[-22];r63=z[-1]-z[0]
    t=np.arange(21,dtype=float);t-=t.mean()
    slope=float(np.dot(t,z[-21:]-z[-21:].mean())/np.dot(t,t)*21)
    result=[r5,r21,r63,r5-r21*5/21,z[-1]-np.max(z),z[-1]-z[-20:].mean(),slope,r63/max(np.sum(abs(dz)),1e-12),np.mean(dz[-21:]>1e-14),np.sum(dz[market>0]),np.sum(dz[market<0]),z[-1]-np.max(z[:-1])]
    return np.array(result,float)

def relative_path(close,asof,old_weights,new_weights):
    return relative_from_history(history(close,asof),old_weights,new_weights)

def _residual(y,x):
    valid=np.isfinite(y)&np.isfinite(x)
    if valid.sum()<84:return None
    xx=x[valid];yy=y[valid];var=float(np.var(xx))
    beta=float(np.dot(xx-xx.mean(),yy-yy.mean())/len(xx)/var) if var>1e-14 else 0.
    intercept=float(yy.mean()-beta*xx.mean())
    e=y-intercept-beta*x
    sigma=float(np.nanstd(e,ddof=1))
    if sigma<1e-10:sigma=1e-10
    def total(n):
        v=e[-n:];good=np.isfinite(v)
        if good.sum()<int(.8*n):return np.nan
        return float(np.sum(v[good])/sigma/np.sqrt(good.sum()))
    return total(21),total(63),e,sigma

def peer_from_history(h):
    n=h.shape[1];out=np.full((n,9),np.nan);peers=[[] for _ in range(n)]
    if len(h)<127:return out,peers
    r=np.log(h.iloc[-127:]).diff().iloc[1:];corr=r.corr(min_periods=84).to_numpy();ret=r.to_numpy();market=np.nanmedian(ret,axis=1)
    for j in range(n):
        candidates=np.flatnonzero(np.isfinite(corr[j])&(corr[j]>0)&(np.arange(n)!=j))
        ids=candidates[np.argsort(-corr[j,candidates],kind='stable')[:5]]
        if len(ids)<3:continue
        peers[j]=ids.tolist();peer=np.nanmean(ret[:,ids],axis=1)
        rs=_residual(ret[:,j],peer);ms=_residual(ret[:,j],market)
        if rs is None or ms is None:continue
        a,b,e,sigma=rs
        prior=e[-42:-21];acc=a-float(np.nansum(prior)/sigma/np.sqrt(np.isfinite(prior).sum())) if np.isfinite(prior).sum()>=17 else np.nan
        pr=np.nansum(ret[-21:,ids],axis=0);coverage=np.isfinite(ret[-21:,ids]).sum(axis=0)>=17
        breadth=float(np.mean(pr[coverage]>0)) if coverage.any() else np.nan
        mom=float(np.nansum(peer[-63:]))
        v=peer[-63:];curve=np.cumsum(np.where(np.isfinite(v),v,0.));dd=float(curve[-1]-max(0.,curve.max()))
        out[j]=[a,b,acc,breadth,mom,np.mean(corr[j,ids]),ms[0],ms[1],dd]
    return out,peers

def peer_context(close,asof):return peer_from_history(history(close,asof))

class Information:
    def __init__(self,close):self.close=close;self.cache={}
    def at(self,asof):
        key=pd.Timestamp(asof)
        if key not in self.cache:
            h=history(self.close,key).iloc[-127:]
            pc,peers=peer_from_history(h);self.cache[key]=(h,pc,peers)
        return self.cache[key]
    def values(self,asof,old_weights,new_weights):
        h,pc,_=self.at(asof);r=relative_from_history(h,old_weights,new_weights)
        def wmean(w):
            ids=w>1e-14
            return np.sum(pc[ids]*w[ids,None],axis=0)
        old=wmean(np.asarray(old_weights));new=wmean(np.asarray(new_weights))
        return np.r_[r,old,new-old]
