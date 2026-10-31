"""Economic helpers for OLC-01. No model probability claims."""
import numpy as np
import pandas as pd

def segments(open_prices, entry, horizons=(21,42,63)):
    a=np.asarray(open_prices,float);out=np.full((3,a.shape[1]),np.nan)
    ends=[entry]+[entry+h for h in horizons]
    for k in range(3):
        x,z=ends[k:k+2]
        if x<0 or z>=len(a):continue
        good=np.isfinite(a[x])&np.isfinite(a[z])&(a[x]>0)&(a[z]>0)
        out[k,good]=np.log(a[z,good]/a[x,good])
    return out

def mature_mask(signal_dates, exit_dates, labels, cutoff):
    s=pd.DatetimeIndex(signal_dates);e=pd.DatetimeIndex(exit_dates)
    return np.asarray((s<pd.Timestamp(cutoff))&(e<pd.Timestamp(cutoff))&np.isfinite(labels))

def risk_cov(returns):
    a=np.asarray(returns,float)
    if len(a)<2:return np.eye(a.shape[1])*.0001
    good=np.isfinite(a);count=good.sum(0)
    means=np.divide(np.nansum(a,0),count,out=np.zeros(a.shape[1]),where=count>0)
    z=np.where(good,a-means,0.)
    c=z.T@z/max(len(a)-1,1)
    return .8*c+.2*np.diag(np.diag(c))+np.eye(a.shape[1])*1e-12

def expected_growth(weights, mu_segments, covariance, profile=True):
    w=np.asarray(weights,float);m=np.cumsum(np.asarray(mu_segments,float),axis=0)
    if not np.isfinite(m[:,w>0]).all():return -np.inf
    m=np.where(np.isfinite(m),m,0.)
    # Second-order log-growth surrogate; m predicts mean log, not simple returns.
    diagonal=float(w@np.diag(covariance));var=float(w@covariance@w)
    utility=m@w+.5*np.array([21.,42.,63.])*(diagonal-var)
    return float(utility.mean() if profile else utility[0])

def trade_cost(old_weights, new_weights, cost):
    a=np.asarray(old_weights,float);b=np.asarray(new_weights,float)
    return float(cost*.5*(np.abs(a-b).sum()+abs((1-a.sum())-(1-b.sum()))))

def choose_best(current, alternatives, mu, covariance, fee, profile=True):
    base=expected_growth(current,mu,covariance,profile)
    if not np.isfinite(base):return -1,0.
    best=-1;improvement=0.
    for i,w in enumerate(alternatives):
        advantage=expected_growth(w,mu,covariance,profile)-trade_cost(current,w,fee)-base
        if np.isfinite(advantage) and advantage>improvement+1e-12:
            best=i;improvement=float(advantage)
    return best,improvement
