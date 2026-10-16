"""Frozen XGB125 2x2: train support (full/reduced) x preprocessing (native/median+scale)."""
from __future__ import annotations
import json, subprocess, sys, copy
from pathlib import Path
import numpy as np
import pandas as pd
from etf_trader.source_only import kernel as k
from paper_ltr_v1 import learner as v1
from paper_ltr_monthly_v1.core import fingerprints

NEW_VARIANTS=("XGB_FULL_PREP","XGB_REDUCED_NATIVE")
ALL_VARIANTS=("BASE","XGB_FULL_PREP","XGB_REDUCED_NATIVE","XGB125_MATCHED")

def select_matrices(train,sub,tests,variant):
    if variant not in NEW_VARIANTS:raise ValueError("Unregistered factorial variant")
    if variant=="XGB_FULL_PREP":
        fitted=train
        state=v1.fit_transform_state(v1.raw_matrix(fitted))
        x=v1.transform(v1.raw_matrix(fitted),state)
        te=[v1.transform(v1.raw_matrix(t),state) for t in tests]
        policy="median+standardization";support="full"
    else:
        fitted=sub
        state={}
        x=v1.raw_matrix(fitted)
        te=[v1.raw_matrix(t) for t in tests]
        x=np.where(np.isfinite(x),x,np.nan)
        te=[np.where(np.isfinite(t),t,np.nan) for t in te]
        policy="native_NaN";support="reduced"
    if x.shape[1]!=len(v1.FEATURES) or any(t.shape[1]!=len(v1.FEATURES) for t in te):
        raise ValueError("Feature count changed")
    if not np.isfinite(x).any() or any(not np.isfinite(t).any() for t in te):
        raise ValueError("All input values missing")
    if policy=="median+standardization" and (not np.isfinite(x).all() or any(not np.isfinite(t).all() for t in te)):
        raise ValueError("Nonfinite imputed matrices")
    return fitted,x,te,state,dict(support=support,policy=policy)

def fit_two(train,tests,year,repeat,root,annual):
    sub,val,start=v1.split_training(train,year)
    old=annual["per_year"][str(year)]["transforms"][str(repeat)]
    fp=fingerprints(train,sub,val)
    if any(old.get(key)!=value for key,value in fp.items()):
        raise ValueError("LINEAR annual subtrain/train fingerprints changed")
    cut=pd.Timestamp(year,1,1)
    if not ((train.signal_date<cut)&(train.exit_date_21<cut)).all():
        raise ValueError("Not mature as of annual fit")
    if (sub.exit_date_21 >= start).any():
        raise ValueError("Purge failed")
    fullstate=v1.fit_transform_state(v1.raw_matrix(sub))
    xx=v1.transform(v1.raw_matrix(sub),fullstate)
    if v1.array_hash(xx)!=old["fit_matrix_sha256"]:
        raise ValueError("LINEAR subtrain matrix changed")
    for key,valstate in fullstate.items():
        if v1.array_hash(valstate)!=old["learned_state_hashes"][key]:
            raise ValueError("LINEAR preprocessing state changed")
    recipe=dict(k.COMPACT_PARAMS)
    rounds=recipe.pop("n_estimators")
    recipe.pop("n_jobs",None)
    seeds=list(k.COMPACT_SEEDS)
    if rounds!=360 or seeds!=[101,202,303] or recipe["objective"]!="rank:pairwise":
        raise ValueError("Canonical XGB recipe changed")
    worker=Path(k.__file__).with_name("_xgb_worker.py")
    root=Path(root)
    scratch=root/"tmp_workers";scratch.mkdir(parents=True,exist_ok=True)
    output={}
    for variant in NEW_VARIANTS:
        fitted,x,te,state,policy=select_matrices(train,sub,tests,variant)
        groups=fitted.groupby("signal_date",sort=True).size().to_numpy()
        if not np.array_equal(fitted[["signal_date","ticker"]].to_numpy(),fitted.sort_values(["signal_date","ticker"])[["signal_date","ticker"]].to_numpy()):
            raise ValueError("Queries not grouped")
        if groups.sum()!=len(fitted) or (groups<=0).any():raise ValueError("Invalid query grouping")
        y=(fitted.target_rank_21.clip(0,1)*100).round().astype(int).to_numpy()
        stem=f"{year}_{repeat}_{variant}"
        cache=scratch/f"{stem}.npz"
        np.savez(cache,Xtr=x,Xte=np.concatenate(te,axis=0),y=y,groups=groups)
        each=[];seed_hashes={}
        for seed in seeds:
            location=scratch/f"{stem}_{seed}.npy"
            cmd=[sys.executable,str(worker),"--data",str(cache),"--seed",str(seed),
                 "--threads","1","--rounds",str(rounds),"--params-json",json.dumps(recipe,sort_keys=True),
                 "--output",str(location)]
            result=subprocess.run(cmd,capture_output=True,text=True)
            if result.returncode:
                raise RuntimeError(f"XGB worker failed {stem}/{seed}: {result.stderr[-3500:]}")
            pred=np.load(location,allow_pickle=False)
            if not np.isfinite(pred).all() or pred.shape!=(sum(len(t) for t in te),):
                raise ValueError("Nonfinite/unaligned predictions")
            each.append(pred);seed_hashes[str(seed)]=v1.array_hash(pred)
            location.unlink()
        cache.unlink()
        ensemble=np.mean(each,axis=0)
        preds=[];offset=0
        for part in te:
            preds.append(ensemble[offset:offset+len(part)])
            offset+=len(part)
        if offset!=len(ensemble):raise ValueError("Split mismatch")
        meta=copy.deepcopy(old)
        meta.update(fp)
        meta.update(kind=variant,recipe=dict(recipe,n_estimators=rounds,seeds=seeds),
            fit_support=policy["support"],preprocessing=policy["policy"],
            xgb_train_rows=len(fitted),xgb_train_queries=len(groups),
            xgb_train_max_signal_date=fitted.signal_date.max().isoformat(),
            xgb_train_max_exit_date=fitted.exit_date_21.max().isoformat(),
            xgb_actual_matrix_sha256=v1.array_hash(x),
            xgb_actual_labels_sha256=v1.array_hash(y),
            xgb_actual_groups_sha256=v1.array_hash(groups),
            xgb_actual_test_matrix_sha256=[v1.array_hash(t) for t in te],
            xgb_learned_state_sha256={n:v1.array_hash(t) for n,t in state.items()},
            full_train_includes_validation=(variant=="XGB_FULL_PREP"),
            train_split_certified_with_LINE125=True,
            saved_models=[],models_not_persisted=True,
            prediction_sha256=[v1.array_hash(p) for p in preds],
            seed_prediction_sha256=seed_hashes,
            mature_only_training=True,no_production_adoption=True,new_seed_fits=3)
        output[variant]=(preds,meta)
    return output
