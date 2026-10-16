"""Causal supervised subspace extraction for frozen Compact21 annual ListNet."""
from pathlib import Path
import copy
import numpy as np
import pandas as pd
from sklearn.cross_decomposition import PLSRegression
from paper_ltr_v1 import learner as v1
from paper_ltr_monthly_v1.core import fingerprints
from paper_ltr_v2.diagnostics_solver import relative_curvature as solver
from paper_ltr_v2.diagnostics_solver.verify_linear_stationarity import independent_gradient
from paper_ltr_v2.replay import sha

K = 12
VARIANTS = ("SIGNAL_PLS12", "SIGNAL_PLS12_COHERENCE")

def date_ic(x, labels, groups):
    """Per-query Pearson IC. Equal weight per signal date, not per ETF."""
    values = np.empty((len(groups), x.shape[1]), float)
    for j, idx in enumerate(groups):
        xx = x[idx] - x[idx].mean(axis=0)
        yy = labels[idx].astype(float) - labels[idx].mean()
        den = np.sqrt(np.sum(xx*xx,axis=0)*np.sum(yy*yy))
        values[j] = np.divide(yy@xx, den, out=np.zeros(x.shape[1]), where=den>1e-14)
    if not np.isfinite(values).all(): raise ValueError("Nonfinite IC")
    return values

def coherence_weights(x, labels, groups, dates):
    """Training-only six-calendar-month block shrinkage, predetermined floor 0.25."""
    ic = date_ic(x, labels, groups)
    quarters = np.array([int(pd.Timestamp(d).year)*2+int(pd.Timestamp(d).month>6) for d in dates])
    blocks = np.stack([ic[quarters==b].mean(axis=0) for b in np.unique(quarters)])
    if len(blocks)<4: raise ValueError("Too few historic independent calendar blocks")
    mu = blocks.mean(axis=0)
    se = blocks.std(axis=0,ddof=1)/np.sqrt(len(blocks))
    conservative = np.maximum(0.0, np.abs(mu)-2.0*se)
    strength = np.divide(conservative, np.maximum(np.abs(mu), 1e-12))
    weights = np.clip(.25+.75*strength,.25,1.0)
    audit = dict(ic_mean=ic.mean(axis=0),block_ic_mean=mu,block_ic_se=se,
                 weights=weights,blocks=len(blocks),dates=len(groups),
                 active_above_floor=int(np.sum(weights>.250000001)),
                 mean_abs_ic=float(np.mean(np.abs(ic.mean(axis=0)))))
    return weights,audit

def supervised_basis(x, labels, groups, dates, variant, k=K):
    """PLS on date-centered inputs and targets with equal date influence."""
    if variant not in VARIANTS: raise ValueError("Unregistered variant")
    if x.ndim!=2 or x.shape[1]!=len(v1.FEATURES) or not np.isfinite(x).all():raise ValueError("Invalid X")
    if len(groups)!=len(dates):raise ValueError("Date/group mismatch")
    if not np.array_equal(np.sort(np.concatenate(groups)),np.arange(len(x))):raise ValueError("Groups not partition")
    weights,ic_audit=coherence_weights(x,labels,groups,dates)
    if variant=="SIGNAL_PLS12":weights=np.ones_like(weights)
    xx=np.empty_like(x,dtype=float);y=np.empty(len(x),dtype=float)
    for idx in groups:
        factor=1/np.sqrt(len(idx))
        xx[idx]=(x[idx]-x[idx].mean(axis=0))*weights*factor
        a=labels[idx].astype(float)
        y[idx]=(a-a.mean())*factor
    pls=PLSRegression(n_components=k,scale=False,max_iter=500,tol=1e-10)
    pls.fit(xx,y)
    projected=weights[:,None]*pls.x_rotations_
    q,r=np.linalg.qr(projected,mode="reduced")
    if q.shape!=(len(v1.FEATURES),k) or np.min(np.abs(np.diag(r)))<1e-9:
        raise ValueError("Degenerate supervised subspace")
    for i in range(k):
        if q[np.argmax(np.abs(q[:,i])),i]<0:q[:,i]*=-1
    np.testing.assert_allclose(q.T@q,np.eye(k),atol=1e-12,rtol=0)
    audit=dict(kind=variant,components=k,ic_blocks=ic_audit["blocks"],
               coherence_active=ic_audit["active_above_floor"],
               mean_abs_ic=ic_audit["mean_abs_ic"],
               weight_mean=float(weights.mean()),weight_min=float(weights.min()),
               weight_max=float(weights.max()),query_demeaned=True,
               equal_query_training_weight=True,rank_label_input=True,
               fitted_only_on_mature_subtrain=True)
    return q,weights,audit,ic_audit

def fit(train,tests,year,repeat,out,annual_root,annual,variant):
    """No mutation to the control recipe; frozen split and preprocessing parity."""
    sub,val,_=v1.split_training(train,year)
    old=annual['per_year'][str(year)]['transforms'][str(repeat)]
    fp=fingerprints(train,sub,val)
    if any(old.get(k)!=v for k,v in fp.items()):raise ValueError("Annual split drift")
    state=v1.fit_transform_state(v1.raw_matrix(sub))
    if any(v1.array_hash(v)!=old['learned_state_hashes'][k] for k,v in state.items()):raise ValueError("Preprocessing drift")
    x=v1.transform(v1.raw_matrix(sub),state)
    vx=v1.transform(v1.raw_matrix(val),state)
    if v1.array_hash(x)!=old['fit_matrix_sha256']:raise ValueError("Subtrain matrix mismatch")
    labels=v1.decile_labels(sub);groups=v1.query_indices(sub)
    dates=sorted(sub.signal_date.unique())
    q,weights,basis_audit,ic_audit=supervised_basis(x,labels,groups,dates,variant)
    z=x@q
    beta,opt=solver.solve_linear(z,labels,groups)
    grad=independent_gradient(z,beta,labels,groups)
    residual=float(np.max(np.abs(grad)))
    if residual>1e-7:raise ValueError("PLS constrained gradient not converged")
    w=q@beta
    predictions=[v1.transform(v1.raw_matrix(t),state)@w for t in tests]
    if not all(np.isfinite(p).all() for p in predictions):raise ValueError("Bad predictions")
    folder=Path(out);file=folder/'models'/f'{year}_{repeat}_{variant}.npz'
    file.parent.mkdir(parents=True,exist_ok=True)
    np.savez(file,w=w,w_pc=beta,supervised_basis=q,weights=weights,
             **state,feature_names=np.asarray(v1.FEATURES))
    opt.update(**basis_audit,projected_gradient_inf=residual,
               predictions_sha256=[v1.array_hash(p) for p in predictions],
               weights_sha256=v1.array_hash(weights),basis_sha256=v1.array_hash(q),
               new_fit_executed=True)
    meta=copy.deepcopy(old)
    meta.update(**fp,kind=variant,recipe=solver.RECIPE,saved_models=[str(file)],seeds=[opt],
                fit_matrix_sha256=v1.array_hash(x),validation_matrix_sha256=v1.array_hash(vx),
                learned_state_hashes={key:v1.array_hash(value) for key,value in state.items()},
                prediction_sha256=[v1.array_hash(p) for p in predictions],
                test_fit_matrix_sha256=[v1.array_hash(v1.transform(v1.raw_matrix(t),state)) for t in tests],
                supervised_basis_sha256=v1.array_hash(q),coherence_weights_sha256=v1.array_hash(weights),
                new_seed_fits=1,reused_seeds=0,training_only_transform=True,
                full_training_refit=False,projected_independent_gradient_inf=residual)
    if year==2026:
        audit=pd.DataFrame(dict(feature=v1.FEATURES,mean_query_ic=ic_audit["ic_mean"],
                block_mean_ic=ic_audit["block_ic_mean"],block_ic_se=ic_audit["block_ic_se"],
                coherence_weight=ic_audit["weights"]))
        return predictions,meta,audit
    return predictions,meta,None
