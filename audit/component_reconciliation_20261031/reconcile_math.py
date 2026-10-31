"""Exact additive attribution for declared counterfactual portfolios, not future alpha."""
import math
import numpy as np

def log_returns(nav):
    nav=np.asarray(nav,dtype=float)
    if nav.ndim!=1 or not np.isfinite(nav).all() or (nav<=0).any():
        raise ValueError('NAV must be a positive finite one-dimensional array')
    return np.diff(np.log(np.r_[1.,nav]))

def shapley(values):
    values=np.asarray(values,dtype=float)
    if values.ndim<2 or not np.isfinite(values).all():
        raise ValueError('Expected finite coalition by observation values')
    count=len(values);n=int(math.log2(count))
    if n<1 or count!=2**n:raise ValueError('All 2**n coalitions are required')
    phi=np.zeros((n,)+values.shape[1:])
    for j in range(n):
        for s in range(count):
            if s&(1<<j):continue
            k=s.bit_count();w=math.factorial(k)*math.factorial(n-k-1)/math.factorial(n)
            phi[j]+=w*(values[s|(1<<j)]-values[s])
    if not np.allclose(phi.sum(axis=0),values[-1]-values[0],rtol=1e-10,atol=1e-12):
        raise AssertionError('Shapley efficiency identity failed')
    return phi

def mobius(values):
    out=np.array(values,dtype=float,copy=True)
    n=int(math.log2(len(out)))
    if len(out)!=2**n:raise ValueError('All 2**n coalitions are required')
    for j in range(n):
        for s in range(2**n):
            if s&(1<<j):out[s]-=out[s^(1<<j)]
    return out
