"""Causal context and a shared, regularized selector of existing formulas.

No function receives future market outcomes at prediction time. Gate weights
are signal mixture weights, not capital allocations or calibrated probabilities.
"""
from __future__ import annotations
import numpy as np
import pandas as pd
from scipy.special import expit
from scipy.stats import spearmanr

CONTEXT=['trend126','efficiency63','vol_ratio','drawdown126','leadership']

def benchmark_context(close:pd.Series)->pd.DataFrame:
    if close.index.has_duplicates or not close.index.is_monotonic_increasing:
        raise ValueError('Unique ordered observations required')
    c=pd.to_numeric(close,errors='coerce').where(close>0)
    log=np.log(c);r=log.diff();v126=r.rolling(126,min_periods=126).std(ddof=0)
    v21=r.rolling(21,min_periods=21).std(ddof=0)
    trend=r.rolling(126,min_periods=126).sum()/(v126.clip(lower=1e-12)*np.sqrt(126))
    denom=r.abs().rolling(63,min_periods=63).sum()
    efficiency=r.rolling(63,min_periods=63).sum().abs()/denom.replace(0,np.nan)
    efficiency=efficiency.where(denom!=0,0.)
    dd=c/c.rolling(126,min_periods=126).max()-1
    out=pd.DataFrame({'trend126':trend,'efficiency63':efficiency,'vol_ratio':np.log(v21.clip(lower=1e-12)/v126.clip(lower=1e-12)),'drawdown126':dd})
    return out.replace([np.inf,-np.inf],np.nan)

def leadership(current:pd.Series,previous:pd.Series)->float:
    p=pd.concat([current.rename('now'),previous.rename('before')],axis=1,join='inner').dropna()
    p=p[np.isfinite(p).all(axis=1)].drop_duplicates(['now','before'])
    if len(p)<3 or p.now.nunique()<2 or p.before.nunique()<2:return np.nan
    return float(spearmanr(p.now,p.before).statistic)

def mature_rows(frame:pd.DataFrame,cutoff)->pd.DataFrame:
    c=pd.Timestamp(cutoff)
    return frame[(pd.to_datetime(frame.date)<c)&(pd.to_datetime(frame.available)<c)&np.isfinite(frame.delta)].copy()

def recent_skill(history:pd.DataFrame,date,market:str)->tuple[float,int]:
    rows=mature_rows(history,date)
    rows=rows[rows.market.eq(market)&(pd.to_datetime(rows.date)>=pd.Timestamp('2021-01-01'))].sort_values('date').tail(12)
    return (float(rows.delta.mean()) if len(rows)>=3 else 0.,len(rows))

def market_weights(markets)->np.ndarray:
    m=np.asarray(markets);k=set(m.tolist())
    if k!={'EU','USA'}:raise ValueError('Both universes required')
    return np.asarray([.5/np.count_nonzero(m==v) for v in m],float)

def fit_gate(frame:pd.DataFrame,features:list[str],penalty:float)->dict:
    if penalty<0:raise ValueError('Nonnegative ridge penalty required')
    w=market_weights(frame.market);y=frame.delta.to_numpy(float)
    if not np.isfinite(y).all():raise ValueError('Only complete matured outcomes may train')
    X=frame[features].to_numpy(float)
    if np.isinf(X).any():raise ValueError('Infinite input')
    if features:
        med=np.nanmedian(X,axis=0)
        if not np.isfinite(med).all():raise ValueError('Entire feature missing in training')
        X=np.where(np.isnan(X),med,X);mean=w@X;sd=np.sqrt(w@((X-mean)**2));sd=np.where(sd>1e-12,sd,1.)
        Z=np.clip((X-mean)/sd,-5,5)
    else:med=mean=sd=np.array([]);Z=np.empty((len(y),0))
    scale=max(float(np.sqrt(w@(y*y))),1e-8);A=np.column_stack([np.ones(len(y)),Z])
    reg=np.diag([0.]+[penalty]*len(features))
    theta=np.linalg.solve(A.T@(w[:,None]*A)+reg,A.T@(w*y/scale))
    return dict(features=features,median=med.tolist(),mean=mean.tolist(),sd=sd.tolist(),coef=theta[1:].tolist(),intercept=float(theta[0]),scale=scale,penalty=float(penalty),counts={m:int((frame.market==m).sum()) for m in ['EU','USA']})

def predict_gate(model:dict,frame:pd.DataFrame)->dict:
    X=frame[model['features']].to_numpy(float)
    if model['features']:
        X=np.where(np.isnan(X),np.array(model['median']),X)
        Z=np.clip((X-np.array(model['mean']))/np.array(model['sd']),-5,5)
    else:Z=np.empty((len(frame),0))
    normalized=model['intercept']+Z@np.array(model['coef'])
    return {'delta':normalized*model['scale'],'g':expit(2*normalized)}

def mix_scores(fixed,fitted,weight):
    a=np.asarray(fixed,float);b=np.asarray(fitted,float);g=float(weight)
    if a.shape!=b.shape or not 0<=g<=1 or not np.isfinite(g):raise ValueError('Aligned scores and weight in[0,1] required')
    if g==0:return a.copy()
    if g==1:return b.copy()
    return (1-g)*a+g*b

def compose_current(return_rank,current):
    r=np.asarray(return_rank,float);c=np.asarray(current,float)
    if r.ndim!=2 or r.shape!=c.shape or not len(r):raise ValueError('Aligned monthly score matrices required')
    l1=c[np.maximum(np.arange(len(c))-1,0)];l2=c[np.maximum(np.arange(len(c))-2,0)]
    vals=np.stack([c,l1,l2]);weights=np.array([.4,.3,.3])[:,None,None];ok=np.isfinite(vals);den=(weights*ok).sum(0)
    avg=np.divide((np.where(ok,vals,0)*weights).sum(0),den,out=np.full_like(c,np.nan),where=den>0)
    avg=np.where(ok.all(0),.4*c+.3*l1+.3*l2,avg)
    smooth=np.where(np.isfinite(c),np.clip(avg,0,1)**1.1,np.nan)
    return smooth,.475*r+.525*smooth
