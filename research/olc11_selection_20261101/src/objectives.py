"""Native selection objectives; no labels can alter live prediction eligibility."""
from __future__ import annotations
import numpy as np
import pandas as pd
from scipy.stats import rankdata

def mature_months(frame:pd.DataFrame,cutoff:pd.Timestamp)->pd.DatetimeIndex:
    if frame.duplicated(['signal_date','ticker']).any():raise ValueError('Duplicate label keys')
    cutoff=pd.Timestamp(cutoff);available=[]
    for date,g in frame.groupby('signal_date',sort=True):
        if date>=cutoff:continue
        if np.isfinite(g['TARGET'].to_numpy(float)).all() and g.exit_date_63.notna().all() and g.exit_date_63.max()<cutoff:
            available.append(date)
    return pd.DatetimeIndex(available)

def finite_vector(y):
    x=np.asarray(y,float)
    if x.ndim!=1 or len(x)==0 or not np.isfinite(x).all():raise ValueError('Finite nonempty vector required')
    return x

def top_event(y)->np.ndarray:
    x=finite_vector(y)
    return (rankdata(x,method='average')/len(x)>.8).astype(np.int8)

def target_grades(y)->np.ndarray:
    x=finite_vector(y)
    if (x<0).any() or (x>1).any():raise ValueError('Native target must lie in [0,1]')
    return np.rint(15*x).astype(np.int32)

def query_sizes(dates)->np.ndarray:
    a=np.asarray(dates)
    if a.ndim!=1 or len(a)==0:raise ValueError('Dates required')
    starts=np.r_[0,np.flatnonzero(a[1:]!=a[:-1])+1]
    if len(pd.unique(a))!=len(starts):raise ValueError('Query rows must be contiguous')
    return np.diff(np.r_[starts,len(a)]).astype(np.uint32)

def probability_metrics(y,p,prior:float)->dict:
    y=finite_vector(y);p=finite_vector(p)
    if y.shape!=p.shape or not np.isin(y,[0,1]).all() or (p<0).any() or (p>1).any() or not 0<=prior<=1:raise ValueError('Invalid probability contract')
    p_clip=np.clip(p,1e-15,1-1e-15);q=np.clip(prior,1e-15,1-1e-15)
    return {'brier':float(np.mean((p-y)**2)),'logloss':float(-np.mean(y*np.log(p_clip)+(1-y)*np.log1p(-p_clip))),
            'prior_brier':float(np.mean((prior-y)**2)),'prior_logloss':float(-np.mean(y*np.log(q)+(1-y)*np.log1p(-q))),
            'mean_probability':float(p.mean()),'event_rate':float(y.mean())}
