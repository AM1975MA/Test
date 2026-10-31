"""Chronological, month-weighted generalized Bayesian forecast calibration.

The Student-t is conditional on this small linear model and its likelihood.
It is not an empirically certified probability of future investment success.
"""
from __future__ import annotations
import numpy as np
import pandas as pd
from scipy.stats import t


def monthly_weights(dates):
    d=pd.Series(pd.to_datetime(dates)).reset_index(drop=True)
    return (1./d.groupby(d).transform('size')).to_numpy(float)


def mature_frame(frame: pd.DataFrame, asof, horizon: str) -> pd.DataFrame:
    if horizon not in ('21','PROFILE'):
        raise ValueError('Unsupported horizon')
    heads=[21] if horizon=='21' else [21,42,63]
    f=frame.copy()
    dates=pd.to_datetime(f['signal_date'])
    exits=pd.concat([pd.to_datetime(f['exit'+str(h)]) for h in heads],axis=1)
    predictions=f[['pred'+str(h) for h in heads]].to_numpy(float)
    outcomes=f[['y'+str(h) for h in heads]].to_numpy(float)
    cut=pd.Timestamp(asof)
    mask=(dates<cut)&exits.notna().all(axis=1)&(exits<cut).all(axis=1)
    mask &= np.isfinite(predictions).all(axis=1)&np.isfinite(outcomes).all(axis=1)
    f['raw_prediction']=predictions.mean(axis=1)
    f['outcome']=outcomes.mean(axis=1)
    f['last_exit']=exits.max(axis=1)
    f['signal_date']=dates
    return f.loc[mask].reset_index(drop=True)


def fit_posterior(frame, asof, horizon='21', scale=.05, min_months=12):
    if scale<=0: raise ValueError('Scale must be positive')
    f=mature_frame(frame,asof,horizon)
    n=f.signal_date.nunique()
    if n<min_months: return None
    w=monthly_weights(f.signal_date)
    assert abs(w.sum()-n)<1e-10
    x=np.column_stack([np.ones(len(f)),f.raw_prediction.to_numpy()/scale])
    y=f.outcome.to_numpy()/scale
    precision=np.eye(2)+(x.T*w)@x
    V=np.linalg.inv(precision)
    beta=V@(x.T@(w*y))
    a=3.+.5*n
    b=2.+.5*(np.dot(w,y*y)-beta@precision@beta)
    if b<=0 or not np.isfinite(b):raise ValueError('Invalid posterior variance')
    return dict(mean_beta=beta,V=V,a=float(a),b=float(b),scale=float(scale),months=int(n),rows=len(f),
                min_raw=float(f.raw_prediction.min()),max_raw=float(f.raw_prediction.max()),
                last_exit=str(f.last_exit.max()),asof=str(pd.Timestamp(asof)))


def forecast(posterior, raw_prediction, cost=0.):
    if not np.isfinite(raw_prediction) or cost<0 or not np.isfinite(cost):
        raise ValueError('Invalid prediction or cost')
    p=posterior;sc=p['scale'];x=np.array([1.,raw_prediction/sc])
    gross=float(sc*x@p['mean_beta'])
    parameter=float(x@p['V']@x)
    scale=float(sc*np.sqrt(p['b']/p['a']*(1.+parameter)))
    mean_scale=float(sc*np.sqrt(p['b']/p['a']*parameter))
    nu=2*p['a'];m=gross-cost
    pos,neg=positive_parts(m,scale,nu)
    return dict(mean=m,gross_mean=gross,scale=scale,mean_scale=mean_scale,df=nu,
                p_switch_positive=float(t.cdf(m/scale,nu)),missed_opportunity=pos,avoided_loss=neg,
                inside_support=p['min_raw']<=raw_prediction<=p['max_raw'])


def positive_parts(mean, scale, df):
    if not np.isfinite([mean,scale,df]).all() or scale<=0 or df<=1:
        raise ValueError('Finite mean, positive scale and Student degrees >1 required')
    z=mean/scale
    positive=float(mean*t.cdf(z,df)+scale*(df+z*z)/(df-1)*t.pdf(z,df))
    negative=positive-mean
    return max(0.,positive),max(0.,negative)


def should_veto(mean, scale, df, missed_weight=2.):
    if missed_weight<1: raise ValueError('Missed-opportunity loss weight must be >=1')
    pos,neg=positive_parts(mean,scale,df)
    return bool(neg>missed_weight*pos)
