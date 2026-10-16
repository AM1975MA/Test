"""Training-only PCA; no whitening, no target-dependent selection."""
import numpy as np

def fit_basis(x,threshold=.95):
    if not 0<threshold<1:raise ValueError('Threshold must be in (0,1)')
    x=np.asarray(x,dtype=np.float64)
    if x.ndim!=2 or not np.isfinite(x).all() or len(x)<2:raise ValueError('Invalid PCA training matrix')
    covariance=x.T@x/(len(x)-1)
    values,q=np.linalg.eigh(covariance)
    order=np.argsort(values)[::-1];values=np.maximum(values[order],0.);q=q[:,order]
    if values.sum()<=0:raise ValueError('Zero training variance')
    # Canonical signs improve audit readability; predictions depend on the subspace.
    for j in range(q.shape[1]):
        if q[np.argmax(np.abs(q[:,j])),j]<0:q[:,j]*=-1
    k=int(np.searchsorted(np.cumsum(values)/values.sum(),threshold)+1)
    while k<len(values) and values[k-1]-values[k]<=1e-10*values[0]:k+=1
    return q,values,k

def project(x,q):return np.asarray(x,dtype=np.float64)@q

def select_basis(x,discarded=False):
    q,values,k=fit_basis(x)
    b=q[:,k:] if discarded else q[:,:k]
    if b.shape[1]==0:raise ValueError('Empty selected subspace')
    return b,values,k
