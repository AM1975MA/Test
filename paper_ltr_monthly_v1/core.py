"""Same LINEAR recipe with a monthly training cutoff; no portfolio changes."""
import copy
import hashlib
import json
import shutil
from pathlib import Path
import numpy as np
import pandas as pd
from paper_ltr_v1 import learner as v1
from paper_ltr_v2.diagnostics_solver import relative_curvature as solver
from paper_ltr_v2.diagnostics_solver.verify_linear_stationarity import independent_gradient

MONTHS=tuple(pd.period_range('2017-01','2026-06',freq='M').astype(str))
KEYS=v1.KEYS
VARIANT='LINEAR_MONTHLY'

def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()

def mature_frame(frame,cutoff):
    cutoff=pd.Timestamp(cutoff)
    valid=frame[v1.FEATURES].notna().sum(axis=1)>=30
    return frame[(frame.signal_date<cutoff)&(frame.exit_date_21<cutoff)&frame.target_rank_21.notna()&valid].sort_values(KEYS).reset_index(drop=True)

def split_at(train,cutoff):
    cutoff=pd.Timestamp(cutoff)
    if train.empty or train[KEYS].isna().any().any() or train.duplicated(KEYS).any():
        raise ValueError('Invalid training keys')
    if not train[KEYS].reset_index(drop=True).equals(train.sort_values(KEYS)[KEYS].reset_index(drop=True)):
        raise ValueError('Unsorted queries')
    if train.exit_date_21.isna().any() or not ((train.signal_date<cutoff)&(train.exit_date_21<cutoff)).all():
        raise ValueError('Immature labels')
    y=train.target_rank_21.to_numpy(float)
    if not np.isfinite(y).all() or ((y<0)|(y>1)).any():raise ValueError('Invalid target')
    dates=np.sort(train.signal_date.unique())
    if len(dates)<10:raise ValueError('Insufficient queries')
    start=pd.Timestamp(dates[-max(1,int(np.ceil(len(dates)*v1.RECIPE['validation_fraction'])))])
    exits=train.groupby('signal_date',sort=True).exit_date_21.max()
    safe=exits.index[(exits.index<start)&(exits<start)]
    sub=train[train.signal_date.isin(safe)].reset_index(drop=True)
    val=train[train.signal_date>=start].reset_index(drop=True)
    if sub.empty or val.empty:raise ValueError('Empty split')
    return sub,val,start

def fingerprints(train,sub,val):
    return dict(train_keys_sha256=v1.keys_hash(train),subtrain_keys_sha256=v1.keys_hash(sub),
        validation_keys_sha256=v1.keys_hash(val),train_matrix_sha256=v1.array_hash(v1.raw_matrix(train)),
        train_labels_sha256=v1.array_hash(v1.decile_labels(train)))

def fit_month(panel,tests,month,repeat,out,annual_root,annual,annual_predictions):
    cutoff=pd.Timestamp(month+'-01');year=cutoff.year
    train=mature_frame(panel,cutoff);sub,val,start=split_at(train,cutoff)
    path=Path(out)/'models'/f'{month}_{repeat}_linear.npz';path.parent.mkdir(parents=True,exist_ok=True)
    fp=fingerprints(train,sub,val)
    cached=cutoff.month==1
    if cached:
        old=annual['per_year'][str(year)]['transforms'][str(repeat)]
        if any(old[k]!=v for k,v in fp.items()):raise ValueError('January inputs differ from annual')
        source=Path(annual_root)/'models'/Path(old['saved_models'][0]).name
        if sha(source)!=annual['model_files_sha256'][source.relative_to(annual_root).as_posix()]:raise ValueError('Annual model changed')
        shutil.copyfile(source,path)
        with np.load(path,allow_pickle=False) as z:
            state={k:z[k].copy() for k in ('median','mean','scale')};w=z['w'].copy()
        for key,value in state.items():
            if v1.array_hash(value)!=old['learned_state_hashes'][key]:raise ValueError('Cached preprocessing changed')
        seed=copy.deepcopy(old['seeds'][0]);meta=copy.deepcopy(old)
    else:
        state=v1.fit_transform_state(v1.raw_matrix(sub))
        x=v1.transform(v1.raw_matrix(sub),state)
        w,seed=solver.solve_linear(x,v1.decile_labels(sub),v1.query_indices(sub))
        seed.update(seed=0,parameter_sha256={'w':v1.array_hash(w)},
            best_validation_loss=v1.listnet_loss_gradient(v1.transform(v1.raw_matrix(val),state)@w,v1.decile_labels(val),v1.query_indices(val))[0])
        np.savez(path,w=w,**state,feature_names=np.asarray(v1.FEATURES))
        meta={}
    x=v1.transform(v1.raw_matrix(sub),state);vx=v1.transform(v1.raw_matrix(val),state)
    residual=float(np.max(np.abs(independent_gradient(x,w,v1.decile_labels(sub),v1.query_indices(sub)))))
    if residual>1e-7 or abs(residual-seed['gradient_inf_norm'])>1e-12:raise ValueError('Independent gradient gate failed')
    transformed=[v1.transform(v1.raw_matrix(t),state) for t in tests]
    predictions=[t@w for t in transformed]
    if cached:
        for j,(test,pred) in enumerate(zip(tests,predictions)):
            f=annual_predictions[j]
            f=f[(f.vintage.astype(str)==str(repeat))&(pd.to_datetime(f.signal_date).dt.to_period('M').astype(str)==month)]
            f=f.sort_values(KEYS).reset_index(drop=True)
            if not f[KEYS].equals(test[KEYS].reset_index(drop=True)):raise ValueError('Cached January keys differ')
            values=f.pred.to_numpy(float)
            if not np.allclose(values,pred,rtol=0,atol=1e-12):raise ValueError('Cached January inference differs')
            predictions[j]=values.copy()
    if any(not np.isfinite(p).all() for p in predictions):raise ValueError('Invalid predictions')
    seed['prediction_sha256']=[v1.array_hash(p) for p in predictions]
    meta.update(kind='PAPER_LISTNET_LINEAR',period=month,cutoff=cutoff.isoformat(),validation_start=start.isoformat(),
        recipe=solver.RECIPE,**fp,
        fit_matrix_sha256=v1.array_hash(x),validation_matrix_sha256=v1.array_hash(vx),
        learned_state_hashes={k:v1.array_hash(v) for k,v in state.items()},
        test_fit_matrix_sha256=[v1.array_hash(t) for t in transformed],
        prediction_sha256=[v1.array_hash(p) for p in predictions],saved_models=[str(path)],seeds=[seed],
        solver_convergence_PASS=True,independent_gradient_inf=residual,
        maturity_PASS=True,purge_PASS=bool((sub.exit_date_21<start).all()),
        max_signal_date=train.signal_date.max().isoformat(),max_exit_date_21=train.exit_date_21.max().isoformat(),
        max_subtrain_exit_date_21=sub.exit_date_21.max().isoformat(),
        training_only_transform=True,full_training_refit=False,
        reused_annual_january=cached,new_seed_fits=int(not cached),reused_seeds=int(cached))
    return predictions,meta
