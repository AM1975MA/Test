"""Causal weekly market state features for Original149, 126-bar random matrix spectrum.

Feature engineering as-of close(t) only, unaffected by any future prices.
RMT here is a diagnostic of collective covariance, NOT predictive physics.
Requires 126 *complete* daily returns per name; never forward fills prices.
"""
from __future__ import annotations
import numpy as np
import pandas as pd
from tensor149_tcn5d.run import anchor_indices

BASE=("spy_mom21","spy_mom63","spy_vol21","breadth21","dispersion21","mean_corr126")
SPECTRAL=("lambda1_share126","effective_rank126","mp_lambda1_ratio126")
ALL=BASE+SPECTRAL
LOOKBACK=126

def weekly_regime_features(close,anchors=None):
    if "SPY" not in close:raise ValueError("SPY missing")
    names=list(close.columns);tindex=close.index
    r=close.pct_change(fill_method=None).to_numpy(dtype=float)
    mom21=close.pct_change(21,fill_method=None)
    mom63=close.pct_change(63,fill_method=None)
    spyid=names.index("SPY")
    if anchors is None:anchors=anchor_indices(tindex)
    output=[]
    for ti in anchors:
        t=int(ti)
        if t<LOOKBACK or t>=len(tindex):continue
        block=r[t-LOOKBACK+1:t+1,:]  # inclusive current day; no future values
        valid=np.isfinite(block).all(axis=0)
        zblock=block[:,valid]
        n=zblock.shape[1]
        if n<60:continue
        scale=zblock.std(axis=0,ddof=1)
        good=scale>1e-9
        z=(zblock[:,good]-zblock[:,good].mean(axis=0))/scale[good]
        n=z.shape[1]
        if n<60:continue
        # Same nonzero spectrum as 149x149 correlation matrix,
        # but faster Gram computation on 126 daily observations.
        eig=np.linalg.eigvalsh((z@z.T)/(LOOKBACK-1))
        eig=np.clip(eig,0,None)
        total=eig.sum()
        if total<=0:continue
        p=eig[eig>1e-10]/total
        lam=eig[-1]
        mp=(1+np.sqrt(n/LOOKBACK))**2  # iid MP upper edge only proxy for cross-linked ETFs
        mean_corr=(np.square(z.sum(axis=1)).sum()/(LOOKBACK-1)-n)/(n*(n-1))
        row21=mom21.iloc[t].to_numpy(float)
        group=row21[np.isfinite(row21)]
        if len(group)<60 or not np.isfinite(row21[spyid]):continue
        sr=r[max(0,t-20):t+1,spyid]
        if not np.isfinite(sr).all():continue
        feat=dict(date=str(tindex[t].date()),t_idx=t,eligible_spectral_n=int(n),
                  spy_mom21=float(row21[spyid]),
                  spy_mom63=float(mom63.iloc[t,spyid]),
                  spy_vol21=float(np.std(sr,ddof=0)*np.sqrt(252)),
                  breadth21=float(np.mean(group>0)),
                  dispersion21=float(np.std(group,ddof=0)),
                  mean_corr126=float(mean_corr),
                  lambda1_share126=float(lam/total),
                  effective_rank126=float(np.exp(-(p*np.log(p)).sum())/n),
                  mp_lambda1_ratio126=float(lam/mp))
        if np.isfinite([feat[k] for k in ALL]).all():output.append(feat)
    out=pd.DataFrame(output)
    if out.empty or out.date.duplicated().any():raise ValueError("Invalid regime history")
    return out.sort_values("date").reset_index(drop=True)

def forward_hmm_probabilities(model,X):
    """Hamilton filter, strictly forward in time, never smoothing (FB)."""
    from scipy.special import logsumexp
    X=np.asarray(X,dtype=float)
    if X.ndim!=2 or not np.isfinite(X).all():raise ValueError("nonfinite state features")
    start=np.asarray(model.startprob_,dtype=float)
    trans=np.asarray(model.transmat_,dtype=float)
    mean=np.asarray(model.means_,dtype=float)
    covariance=np.asarray(model.covars_,dtype=float)
    # hmmlearn diag covars_ often has shape [states,dim,dim].
    if covariance.ndim==3:covariance=np.diagonal(covariance,axis1=-2,axis2=-1)
    if mean.shape!=(len(start),X.shape[1]) or covariance.shape!=mean.shape:
        raise ValueError("HMM emission matrix dimensions invalid")
    covariance=np.maximum(covariance,1e-6)
    norm=-.5*(np.log(2*np.pi*covariance).sum(axis=1))
    log_trans=np.log(np.maximum(trans,1e-200))
    prior=np.log(np.maximum(start,1e-200))
    out=np.zeros((len(X),len(start)))
    for j,obs in enumerate(X):
        emit=norm-.5*(np.square(obs[None,:]-mean)/covariance).sum(axis=1)
        log_post=prior+emit
        log_post-=logsumexp(log_post)
        out[j]=np.exp(log_post)
        prior=logsumexp(log_post[:,None]+log_trans,axis=0)
    return out
