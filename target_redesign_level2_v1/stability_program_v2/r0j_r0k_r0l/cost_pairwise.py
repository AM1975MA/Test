"""RESEARCH-ONLY pairwise logistic objective with a fixed uncertainty band.

Proof of API feasibility, not an approved ETF Trader strategy.  Unlike native
rank:pairwise, it uses all eligible pairs and an approximate diagonal Hessian.
All returns passed to make_xgb_objective MUST be fully mature by fit cutoff.
"""
from __future__ import annotations
import numpy as np

def group_loss(scores, realized_returns, fee_band=.002):
    s=np.asarray(scores,dtype=float);r=np.asarray(realized_returns,dtype=float)
    if s.ndim!=1 or r.ndim!=1 or s.shape!=r.shape or len(s)<2 or not np.isfinite(s).all() or not np.isfinite(r).all() or fee_band<0:
        raise ValueError("invalid group scores/returns or negative band")
    n=len(s);i,j=np.triu_indices(n,1)
    sign=np.sign(r[i]-r[j]);valid=(np.abs(r[i]-r[j])>=fee_band)&(sign!=0)
    i=i[valid];j=j[valid];sgn=sign[valid]
    d=(s[i]-s[j])*sgn
    p=1/(1+np.exp(np.clip(d,-50,50)))
    g=np.zeros(n,dtype=float);h=np.full(n,1e-9,dtype=float)
    np.add.at(g,i,-sgn*p/n);np.add.at(g,j,+sgn*p/n)
    curv=p*(1-p)/n
    np.add.at(h,i,curv);np.add.at(h,j,curv)
    return g,h,{"included":len(i),"excluded":int(n*(n-1)//2-len(i))}

def make_xgb_objective(realized_returns, fee_band=.002,group_sizes=None):
    r=np.asarray(realized_returns,dtype=float)
    if group_sizes is None:raise ValueError("explicit group_sizes required")
    gs=np.asarray(group_sizes,dtype=int)
    if gs.ndim!=1 or any(gs<2) or sum(gs)!=len(r) or not np.isfinite(r).all():
        raise ValueError("invalid group manifest")
    edges=np.r_[0,np.cumsum(gs)]
    def objective(pred, dmatrix):
        qid=dmatrix.get_uint_info("group_ptr")
        if not np.array_equal(qid,edges):raise ValueError("group_ptr does not match audited group sizes")
        grad=np.zeros(len(r),dtype=float);hess=np.zeros(len(r),dtype=float)
        for a,b in zip(edges[:-1],edges[1:]):
            g,h,_=group_loss(pred[a:b],r[a:b],fee_band)
            grad[a:b]=g;hess[a:b]=h
        return grad.astype(np.float32),hess.astype(np.float32)
    return objective
