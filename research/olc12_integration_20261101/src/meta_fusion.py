"""Monotone, regularized, past-OOF-only event fusion. No portfolio target or weight tuning."""
from __future__ import annotations
import numpy as np,pandas as pd
from scipy.optimize import minimize
from scipy.special import expit

def mature_groups(frame,year):
    cutoff=pd.Timestamp(year,1,1)
    candidates=frame[frame.signal_date<cutoff].copy()
    groups=candidates.groupby('signal_date')
    ok=groups.apply(lambda g: g.TARGET.notna().all() and g.exit_date_63.notna().all() and g.exit_date_63.max()<cutoff,include_groups=False)
    return candidates[candidates.signal_date.isin(ok[ok].index)].copy()

def fit_meta(x,y,dates):
    x=np.asarray(x,float);y=np.asarray(y,float);dates=np.asarray(dates)
    if x.ndim!=2 or len(x)!=len(y) or len(dates)!=len(y) or not np.isfinite(x).all() or not np.isfinite(y).all() or not np.isin(y,[0,1]).all():raise ValueError('Invalid training rows')
    _,group,counts=np.unique(dates,return_inverse=True,return_counts=True);w=1./counts[group];w/=w.sum()
    mu=np.sum(w[:,None]*x,axis=0);scale=np.sqrt(np.sum(w[:,None]*(x-mu)**2,axis=0));scale=np.where(scale>1e-12,scale,1.)
    z=(x-mu)/scale;prior=float(np.dot(w,y));initial=np.r_[np.log(np.clip(prior,1e-6,1-1e-6)/(1-np.clip(prior,1e-6,1-1e-6))),np.zeros(x.shape[1])]
    def loss(b):
        eta=b[0]+z@b[1:];prob=expit(eta)
        objective=np.dot(w,np.logaddexp(0,eta)-y*eta)+.01*np.dot(b[1:],b[1:])
        diff=w*(prob-y);grad=np.r_[diff.sum(),z.T@diff+.02*b[1:]]
        return float(objective),grad
    res=minimize(loss,initial,jac=True,method='L-BFGS-B',bounds=[(None,None)]+[(0,None)]*x.shape[1],options={'maxiter':1000,'ftol':1e-12})
    if not res.success:raise RuntimeError(str(res.message))
    return {'intercept':float(res.x[0]),'coef':res.x[1:].tolist(),'mean':mu.tolist(),'scale':scale.tolist(),'months':int(len(counts)),'event_rate':prior,'loss':float(res.fun),'iterations':int(res.nit),'success':bool(res.success),'penalty':.01}

def predict_meta(model,x):
    x=np.asarray(x,float);z=(x-np.asarray(model['mean']))/np.asarray(model['scale'])
    return expit(model['intercept']+z@np.asarray(model['coef']))
