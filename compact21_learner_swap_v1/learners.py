"""Preregistered learner swap; all transforms are fitted on mature annual training.

BASE is the canonical isolated XGB worker with unchanged matrix/legacy labels.
RIDGE and LambdaRank reproduce PHASE_B parameters, without parameter search.
"""
from __future__ import annotations
import hashlib, json, subprocess, sys, time
from pathlib import Path
import numpy as np
import pandas as pd
from etf_trader.source_only import kernel as k

VARIANTS = ('BASE', 'RIDGE', 'LGBM_LAMBDARANK')
KEYS = ['signal_date', 'ticker']
LGBM_PARAMS = dict(objective='lambdarank', n_estimators=360, learning_rate=.035,
    max_depth=4, num_leaves=15, min_child_samples=40, subsample=.85,
    subsample_freq=1, colsample_bytree=.8, reg_lambda=8., reg_alpha=.1,
    n_jobs=1, deterministic=True, force_col_wise=True, verbosity=-1,
    label_gain=list(range(101)))
RIDGE_PARAMS = dict(imputer_strategy='median', scaler='StandardScaler', alpha=30.)

def array_hash(value):
    a=np.ascontiguousarray(value)
    h=hashlib.sha256(); h.update(str(a.dtype).encode()); h.update(str(a.shape).encode()); h.update(a.tobytes())
    return h.hexdigest()

def matrix(frame):
    return frame[k.F2D_FEATURES].replace([np.inf,-np.inf],np.nan)

def validate(train, tests, year):
    cutoff=pd.Timestamp(year,1,1)
    if train.empty or not tests or any(z.empty for z in tests): raise ValueError('Empty fit or inference')
    if train[KEYS].isna().any().any() or train.duplicated(KEYS).any(): raise ValueError('Invalid or duplicate training keys')
    if not train[KEYS].reset_index(drop=True).equals(train.sort_values(KEYS)[KEYS].reset_index(drop=True)): raise ValueError('Ungrouped rows')
    if not (train.signal_date.notna().all() and train.exit_date_21.notna().all() and
            (train.signal_date<cutoff).all() and (train.exit_date_21<cutoff).all()): raise ValueError('Immature training rows')
    y=train.target_rank_21.to_numpy(float)
    if not np.isfinite(y).all() or ((y<0)|(y>1)).any(): raise ValueError('Invalid continuous percentile target')
    for z in tests:
        if z[KEYS].isna().any().any() or z.duplicated(KEYS).any(): raise ValueError('Invalid or duplicate inference keys')
    return cutoff

def fit(train, tests, variant, year, tmp, tag):
    """Return (predictions per test frame, training audit, fitted labels, seconds).

    Caller selects native mature training. This rejects, rather than silently
    removes, future rows. Missing feature values follow canonical model handling.
    """
    if variant not in VARIANTS: raise ValueError(variant)
    cutoff=validate(train, tests, year)
    X=matrix(train); T=[matrix(z) for z in tests]
    y=(train.target_rank_21.clip(0,1)*100).round().astype(int).to_numpy()
    if variant=='RIDGE': y=train.target_rank_21.to_numpy(float)
    groups=train.groupby('signal_date',sort=True).size().to_numpy()
    if groups.sum()!=len(train) or (groups<=0).any(): raise ValueError('Invalid groups')
    tmp=Path(tmp); tmp.mkdir(parents=True,exist_ok=True)
    meta={'kind':variant, 'feature_transform':'identity' if variant!='RIDGE' else 'median_imputer_then_standard_scaler',
          'target':'continuous_percentile' if variant=='RIDGE' else 'canonical_round_rank_times_100',
          'train_matrix_sha256':array_hash(X.to_numpy()), 'train_labels_sha256':array_hash(y),
          'fit_matrix_sha256':array_hash(X.to_numpy()),
          'train_groups_sha256':array_hash(groups), 'train_rows':len(train),
          'test_matrix_sha256':[array_hash(t.to_numpy()) for t in T],
          'test_fit_matrix_sha256':[array_hash(t.to_numpy()) for t in T],
          'feature_names':list(k.F2D_FEATURES), 'cutoff':cutoff.isoformat(),
          'max_signal_date':train.signal_date.max().isoformat(), 'max_exit_date_21':train.exit_date_21.max().isoformat(),
          'maturity_PASS':True, 'learned_state_hashes':{}, 'seed_prediction_sha256':{}}
    start=time.perf_counter()
    if variant=='BASE':
        params=dict(k.COMPACT_PARAMS); rounds=int(params.pop('n_estimators')); params.pop('n_jobs',None)
        meta['model_params']=dict(params,n_estimators=rounds,threads=1,seeds=list(k.COMPACT_SEEDS))
        data=tmp/f'{tag}.npz'; np.savez(data,Xtr=X.to_numpy(),Xte=pd.concat(T).to_numpy(),y=y,groups=groups)
        byseed=[]
        for seed in k.COMPACT_SEEDS:
            out=tmp/f'{tag}_{seed}.npy'
            subprocess.run([sys.executable,str(Path(k.__file__).with_name('_xgb_worker.py')),
                           '--data',str(data),'--seed',str(seed),'--threads','1','--rounds',str(rounds),
                           '--params-json',json.dumps(params),'--output',str(out)],check=True,capture_output=True,text=True)
            p=np.load(out); byseed.append(p); meta['seed_prediction_sha256'][str(seed)]=array_hash(p)
        pred=np.mean(byseed,axis=0); sizes=[len(t) for t in T]; ans=[]; pos=0
        for n in sizes: ans.append(pred[pos:pos+n]); pos+=n
    elif variant=='RIDGE':
        from sklearn.impute import SimpleImputer
        from sklearn.preprocessing import StandardScaler
        from sklearn.linear_model import Ridge
        from sklearn.pipeline import make_pipeline
        m=make_pipeline(SimpleImputer(strategy='median'),StandardScaler(),Ridge(alpha=30.))
        m.fit(X,y); ans=[m.predict(t) for t in T]; meta['model_params']=dict(RIDGE_PARAMS)
        import joblib
        joblib.dump(m,tmp/f'{tag}_ridge.joblib')
        imputer,scaler,ridge=m.steps[0][1],m.steps[1][1],m.steps[2][1]
        meta['learned_state_hashes']={name:array_hash(value) for name,value in
            [('imputer_statistics',imputer.statistics_),('scaler_mean',scaler.mean_),('scaler_scale',scaler.scale_),
             ('scaler_variance',scaler.var_),('ridge_coef',ridge.coef_),('ridge_intercept',ridge.intercept_)]}
        meta['imputer_statistics']=[None if not np.isfinite(v) else float(v) for v in imputer.statistics_]
        meta['scaler_mean']=scaler.mean_.tolist(); meta['scaler_scale']=scaler.scale_.tolist()
        meta['fit_matrix_sha256']=array_hash(scaler.transform(imputer.transform(X)))
        meta['test_fit_matrix_sha256']=[array_hash(scaler.transform(imputer.transform(t))) for t in T]
    else:
        import lightgbm
        if lightgbm.__version__!='4.6.0': raise ValueError('Frozen LightGBM version must be 4.6.0')
        byseed=[]; meta['model_params']=dict(LGBM_PARAMS,seeds=list(k.COMPACT_SEEDS))
        for seed in k.COMPACT_SEEDS:
            m=lightgbm.LGBMRanker(**LGBM_PARAMS,random_state=seed); m.fit(X,y,group=groups)
            m.booster_.save_model(str(tmp/f'{tag}_lgbm_{seed}.txt'))
            p=[m.predict(t) for t in T]; byseed.append(p)
            meta['seed_prediction_sha256'][str(seed)]=array_hash(np.concatenate(p))
            meta['learned_state_hashes'][f'booster_{seed}']=hashlib.sha256(m.booster_.model_to_string().encode()).hexdigest()
        ans=[np.mean([p[j] for p in byseed],axis=0) for j in range(len(T))]
    if any(len(p)!=len(t) or not np.isfinite(p).all() for p,t in zip(ans,T)): raise ValueError('Invalid predictions')
    meta['prediction_sha256']=[array_hash(p) for p in ans]
    return ans, meta, y, time.perf_counter()-start
