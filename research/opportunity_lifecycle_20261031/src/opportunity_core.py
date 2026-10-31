"""Small independent helpers for descriptive opportunity diagnostics.
No rule in this module selects from future returns.
"""
from collections.abc import Sequence
import numpy as np

def topk(scores: np.ndarray, k: int) -> list[int]:
    a=np.asarray(scores,dtype=float)
    if a.ndim!=1 or k<0:raise ValueError('Expected 1D scores and nonnegative k')
    ids=np.flatnonzero(np.isfinite(a))
    return ids[np.argsort(-a[ids],kind='stable')[:k]].astype(int).tolist()

def shortlist(scores: Sequence[np.ndarray], support: np.ndarray,k: int=5) -> list[int]:
    support=np.asarray(support,bool);out=set()
    for s in scores:
        s=np.asarray(s,float)
        if s.shape!=support.shape:raise ValueError('Unaligned candidates')
        out.update(topk(np.where(support,s,np.nan),k))
    return sorted(out)

def horizon_returns(opens: np.ndarray, entry: int, horizon: int) -> np.ndarray:
    o=np.asarray(opens,float)
    if o.ndim!=2 or entry<0 or horizon<1:raise ValueError('Invalid horizon/price input')
    out=np.full(o.shape[1],np.nan)
    if entry+horizon>=len(o) or entry>=len(o):return out
    a,b=o[entry],o[entry+horizon];ok=np.isfinite(a)&np.isfinite(b)&(a>0)&(b>0)
    out[ok]=b[ok]/a[ok]-1
    return out

def switch_gain(new_return: float, old_return: float, cost_per_side: float) -> float:
    if not 0<=cost_per_side<1:raise ValueError('Invalid cost')
    if new_return<=-1 or old_return<=-1:raise ValueError('Invalid simple return')
    return (1-cost_per_side)/(1+cost_per_side)*(1+new_return)-(1+old_return)

def actual_incumbents(previous_ledger: np.ndarray) -> list[int]:
    row=np.asarray(previous_ledger,float)
    if len(row)<48:raise ValueError('Expected original 48-column ledger')
    return list(dict.fromkeys(int(row[ix]) for ix,v in [(25,11),(26,12)] if row[ix]>=0 and row[v]>1e-12))
