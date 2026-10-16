"""Frozen XGBRanker control and PLS-feature experiments on identical annual subtrain."""
from __future__ import annotations
import copy
import json
import subprocess
import sys
from pathlib import Path
import numpy as np
from paper_ltr_v1 import learner as v1
from paper_ltr_monthly_v1.core import fingerprints
from signal_lockin_v1.core import supervised_basis
from etf_trader.source_only import kernel as k

VARIANTS=('XGB125_MATCHED','XGB_PLS12','XGB_PLS12_COHERENCE')
PLS_MAP={'XGB_PLS12':'SIGNAL_PLS12','XGB_PLS12_COHERENCE':'SIGNAL_PLS12_COHERENCE'}

def fit(train,tests,year,repeat,folder,annual):
    """Uses same eligible rows and 10% holdout as certified LINEAR125."""
    sub,val,_=v1.split_training(train,year)
    old=annual['per_year'][str(year)]['transforms'][str(repeat)]
    fp=fingerprints(train,sub,val)
    if any(old.get(name)!=value for name,value in fp.items()):
        raise ValueError('Annual training keys or validation split changed')
    state=v1.fit_transform_state(v1.raw_matrix(sub))
    if any(v1.array_hash(state[name])!=old['learned_state_hashes'][name] for name in state):
        raise ValueError('Subtrain imputer or scaler differs from frozen LINEAR125')
    x=v1.transform(v1.raw_matrix(sub),state)
    if v1.array_hash(x)!=old['fit_matrix_sha256']: raise ValueError('Subtrain matrix changed')
    transformed=[v1.transform(v1.raw_matrix(t),state) for t in tests]
    dates=sorted(sub.signal_date.unique())
    labels=v1.decile_labels(sub)
    groups=v1.query_indices(sub)
    params=dict(k.COMPACT_PARAMS); rounds=int(params.pop('n_estimators'))
    params.pop('n_jobs',None)
    seeds=list(k.COMPACT_SEEDS)
    if rounds!=360 or seeds!=[101,202,303] or params.get('objective')!='rank:pairwise':
        raise ValueError('Published canonical XGBoost parameters changed')
    y=(sub.target_rank_21.clip(0,1)*100).round().astype(int).to_numpy()
    counts=sub.groupby('signal_date',sort=True).size().to_numpy()
    if len(counts)!=len(groups) or not np.array_equal(counts,[len(g) for g in groups]):
        raise ValueError('Unsorted ranker queries')
    original_worker=Path(k.__file__).with_name('_xgb_worker.py')
    root=Path(folder); temporary=root/'worker_cache';temporary.mkdir(parents=True,exist_ok=True)
    output={}
    for variant in VARIANTS:
        if variant=='XGB125_MATCHED':
            q=None;xx=x;te=transformed;features=125;weights=None;extraction=None
        else:
            q,weights,extraction,_=supervised_basis(x,labels,groups,dates,PLS_MAP[variant])
            xx=x@q;te=[z@q for z in transformed];features=q.shape[1]
            if features!=12: raise ValueError('PLS dimension changed')
            np.testing.assert_allclose(q.T@q,np.eye(12),atol=1e-12,rtol=0)
            np.testing.assert_allclose(xx,x@q,atol=0,rtol=0)
        stem=f'{year}_{repeat}_{variant}'
        data=temporary/(stem+'.npz')
        concat=np.concatenate(te,axis=0)
        np.savez(data,Xtr=xx,Xte=concat,y=y,groups=counts)
        byseed=[];hashes={}
        for seed in seeds:
            pred_file=temporary/(stem+f'_{seed}.npy')
            subprocess.run([sys.executable,str(original_worker),'--data',str(data),
                 '--seed',str(seed),'--threads','1','--rounds',str(rounds),
                 '--params-json',json.dumps(params,sort_keys=True),
                 '--output',str(pred_file)],check=True,capture_output=True,text=True)
            pred=np.load(pred_file,allow_pickle=False)
            if len(pred)!=len(concat) or not np.isfinite(pred).all():raise ValueError('Invalid XGB predictions')
            byseed.append(pred);hashes[str(seed)]=v1.array_hash(pred)
            pred_file.unlink()
        data.unlink()
        mean=np.mean(byseed,axis=0)
        preds=[];offset=0
        for part in te:
            preds.append(mean[offset:offset+len(part)])
            offset+=len(part)
        if offset!=len(mean) or any(not np.isfinite(p).all() for p in preds):raise ValueError('Invalid split predictions')
        path=root/'models'/f'{stem}.npz';path.parent.mkdir(exist_ok=True,parents=True)
        meta_values=dict(variant=np.array(variant),feature_names=np.array(v1.FEATURES),
                         xgb_seed=np.array(seeds),xgb_rounds=np.array(rounds),
                         xgb_model_params=np.array(json.dumps(params,sort_keys=True)),**state)
        if q is not None:
            meta_values.update(supervised_basis=q,coherence_weights=weights)
        np.savez(path,**meta_values)
        details=copy.deepcopy(old)
        details.update(**fp,kind=variant,recipe=dict(params,n_estimators=rounds,seeds=seeds),
                       learned_state_hashes={key:v1.array_hash(v) for key,v in state.items()},
                       fit_matrix_sha256=v1.array_hash(x),validation_matrix_sha256=v1.array_hash(v1.transform(v1.raw_matrix(val),state)),
                       train_labels_sha256=v1.array_hash(v1.decile_labels(train)),
                       new_seed_fits=3,reused_seeds=0,training_only_transform=True,full_training_refit=False,
                       test_fit_matrix_sha256=[v1.array_hash(t) for t in transformed],
                       transformed_fit_matrix_sha256=v1.array_hash(xx),
                       transformed_test_matrix_sha256=[v1.array_hash(t) for t in te],
                       supervised_basis_sha256=None if q is None else v1.array_hash(q),
                       extraction_audit=extraction,
                       prediction_sha256=[v1.array_hash(p) for p in preds],
                       seed_prediction_sha256=hashes,saved_models=[str(path)])
        output[variant]=(preds,details)
    return output
