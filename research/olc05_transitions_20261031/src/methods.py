"""Finite, declared interventions; not a strategy optimizer."""
import numpy as np

def collapse_columns(x, identities):
    x=np.asarray(x,float)
    if x.ndim!=2 or x.shape[1]!=len(identities):raise ValueError('Unaligned identities')
    ordered=list(dict.fromkeys(identities));cols=[]
    for name in ordered:
        jj=[i for i,v in enumerate(identities) if v==name]
        if any(not np.array_equal(x[:,jj[0]],x[:,j],equal_nan=True) for j in jj[1:]):
            raise ValueError('Identity map conflicts with known identical aliases')
        cols.append(jj[0])
    return x[:,cols].copy(),ordered

def blend_forecasts(r, et, x):
    r,et,x=[np.asarray(a,float) for a in (r,et,x)]
    if not(r.shape==et.shape==x.shape) or r.ndim!=2 or len(r)<1:raise ValueError('Unaligned monthly arrays')
    t=.6*et+.4*x
    l1=np.concatenate([t[:1],t[:-1]],axis=0)
    l2=np.concatenate([t[:1],t[:1],t[:-2]],axis=0)[:len(t)]
    a=np.stack([t,l1,l2]);w=np.array([.4,.3,.3])[:,None,None];ok=np.isfinite(a)
    den=(w*ok).sum(0);num=(np.where(ok,a,0.)*w).sum(0)
    sm=np.divide(num,den,out=np.full_like(t,np.nan),where=den>0)
    sm=np.where(ok.all(0),.4*t+.3*l1+.3*l2,sm)
    h=np.where(np.isfinite(t),np.clip(sm,0,1)**1.1,np.nan)
    return .475*r+.525*h

def transition_weights(units, prior_close, proposed, fraction):
    if not 0<=fraction<=1:raise ValueError('Fraction outside [0,1]')
    u,c,p=[np.asarray(a,float) for a in (units,prior_close,proposed)]
    if u.shape!=c.shape or p.shape!=u.shape:raise ValueError('Unaligned holdings')
    if not np.isfinite(p).all() or (p<0).any() or not np.isclose(p.sum(),1.):raise ValueError('Proposal must sum to 1')
    if (u<0).any() or np.any((u>0)&(~np.isfinite(c)|(c<=0))):raise ValueError('Invalid valuation')
    v=np.where(u>0,u*np.nan_to_num(c,nan=0.),0.);total=v.sum()
    if total<=1e-14 or fraction==1:return p.copy()
    return (1-fraction)*v/total+fraction*p

def main_turnover(old_values, new_weights, value):
    if value<=0:raise ValueError('Positive NAV required')
    return .5*np.abs(np.asarray(old_values,float)/value-np.asarray(new_weights,float)).sum()
