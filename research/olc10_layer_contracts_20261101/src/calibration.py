"""Small annual OOF target calibrators. Expected target is NOT a probability."""
from __future__ import annotations
import numpy as np
import pandas as pd
from scipy.optimize import lsq_linear

def month_weights(dates):
    dates=pd.Series(pd.to_datetime(dates)).reset_index(drop=True)
    counts=dates.groupby(dates).transform('size').to_numpy(float)
    w=1/counts;return w/w.sum()

def mature_history(frame,cutoff):
    cutoff=pd.Timestamp(cutoff)
    required=['TARGET','ET_RAW','XGB_RAW']
    mask=(pd.to_datetime(frame.signal_date)<cutoff)&(pd.to_datetime(frame.exit_date_63)<cutoff)
    mask &= np.isfinite(frame[required]).all(axis=1)
    return frame.loc[mask].sort_values(['signal_date','ticker'] if 'ticker' in frame else ['signal_date']).reset_index(drop=True)

def _checked(x,y,w):
    x=np.asarray(x,float);y=np.asarray(y,float);w=np.asarray(w,float)
    if len(x)!=len(y) or y.shape!=w.shape or not np.isfinite(x).all() or not np.isfinite(y).all() or not np.isfinite(w).all() or (w<0).any() or w.sum()<=0:raise ValueError('Invalid fit data')
    return x,y,w/w.sum()

def fit_affine(x,y,w):
    x,y,w=_checked(x,y,w);mx=np.dot(w,x);my=np.dot(w,y)
    variance=np.dot(w,(x-mx)**2);cov=np.dot(w,(x-mx)*(y-my))
    slope=float(np.clip(cov/(1.1*variance),0,2)) if variance>1e-16 else 0.
    return {'kind':'AFFINE','coef':[slope],'intercept':float(my-slope*mx),'penalty_fraction':.1}

def fit_stack(x,y,w):
    x,y,w=_checked(x,y,w)
    if x.ndim!=2 or x.shape[1]!=2:raise ValueError('Two raw experts required')
    mx=w@x;my=w@y;xc=x-mx;yc=y-my
    penalty=.1*float(np.mean(w@(xc**2)))
    a=np.vstack([xc*np.sqrt(w[:,None]),np.sqrt(penalty)*np.eye(2)])
    b=np.r_[yc*np.sqrt(w),np.sqrt(penalty)*np.array([.6,.4])]
    fit=lsq_linear(a,b,bounds=(0.,2.),tol=1e-12)
    if not fit.success:raise RuntimeError(fit.message)
    beta=fit.x
    return {'kind':'STACK2','coef':beta.tolist(),'intercept':float(my-mx@beta),'ridge_penalty':penalty}

def predict(model,x):
    x=np.asarray(x,float)
    if model['kind']=='AFFINE':return model['intercept']+model['coef'][0]*x
    return model['intercept']+x@np.asarray(model['coef'])
