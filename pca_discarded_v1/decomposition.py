"""Descriptive orthogonal decomposition, with no learner fitting."""
import numpy as np

def split_weights(w,basis):
    np.testing.assert_allclose(basis.T@basis,np.eye(basis.shape[1]),rtol=0,atol=1e-12)
    retained=basis@(basis.T@w)
    return retained,w-retained

def energy_split(x,groups,basis):
    x=x-x.mean(axis=0)
    total=float(np.sum(x*x));retained_total=float(np.sum((x@basis)**2))
    within=between=retained_within=retained_between=0.
    for ix in groups:
        center=x[ix].mean(axis=0);residual=x[ix]-center
        within+=float(np.sum(residual**2));between+=len(ix)*float(center@center)
        retained_within+=float(np.sum((residual@basis)**2));retained_between+=len(ix)*float(np.sum((center@basis)**2))
    if abs(total-within-between)>1e-8*max(total,1.):raise ValueError('Energy decomposition fails')
    return dict(total=total,within=within,between=between,retained_total=retained_total,
                retained_within=retained_within,retained_between=retained_between,
                fraction_retained_total=retained_total/total,
                fraction_retained_within=retained_within/within if within>0 else None,
                fraction_retained_between=retained_between/between if between>0 else None)
