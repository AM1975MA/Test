"""Matched annual objectives. All variants/seeds are fixed before outcomes."""
from __future__ import annotations
import os
for key in ['OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS']:os.environ[key]='1'
from pathlib import Path
import json,time,hashlib,argparse,concurrent.futures
import numpy as np,pandas as pd,joblib,xgboost as xgb,sklearn
from sklearn.impute import SimpleImputer
from sklearn.ensemble import ExtraTreesRegressor,ExtraTreesClassifier
from recovery_core import sha256,atomic_json,complete_checkpoint,valid_checkpoint,canonical_forecasts
from objectives import target_grades
ROOT=Path(__file__).resolve().parents[1]
FAMILIES=['ET_REG','XGB_REG','ET_CLASS','XGB_CLASS','XGB_RANK']
SEEDS=[101,211,307]
ENV={'numpy':np.__version__,'pandas':pd.__version__,'sklearn':sklearn.__version__,'xgboost':xgb.__version__}

def parameters(family:str,seed:int)->dict:
    if family not in FAMILIES:raise ValueError(family)
    p=json.loads((ROOT/'inputs/PARENT_PARAMETERS.json').read_text())['ET' if family.startswith('ET') else 'XGB']
    p['random_state']=seed
    if family=='XGB_CLASS':p['objective']='binary:logistic';p['eval_metric']='logloss'
    if family=='XGB_RANK':
        p.update(objective='rank:ndcg',lambdarank_pair_method='topk',lambdarank_num_pair_per_sample=4,ndcg_exp_gain=False,eval_metric='ndcg@2')
    return p

def fit_one(family,X,d,seed):
    p=parameters(family,seed)
    if family=='ET_REG':return ExtraTreesRegressor(n_jobs=1,**p).fit(X,d['y'])
    if family=='ET_CLASS':return ExtraTreesClassifier(n_jobs=1,**p).fit(X,d['binary'])
    if family=='XGB_REG':return xgb.XGBRegressor(n_jobs=1,**p).fit(X,d['y'])
    if family=='XGB_CLASS':return xgb.XGBClassifier(n_jobs=1,**p).fit(X,d['binary'])
    return xgb.XGBRanker(n_jobs=1,**p).fit(X,target_grades(d['y']),group=d['groups'])

def predict(model,family,X):
    if family.endswith('CLASS'):return model.predict_proba(X)[:,1]
    return model.predict(X)

def original_parity():
    records=[]
    for market in ['EU','USA']:
        d=joblib.load(ROOT/'inputs/annual'/f'{market}_2022.joblib')
        imp=SimpleImputer(strategy='median',keep_empty_features=True);X=imp.fit_transform(d['X_original']);XP=imp.transform(d['XP'])
        old=dict(d,y=d['y_original'])
        out=d['predict_keys'].copy()
        for family,col in [('ET_REG','ET_RAW'),('XGB_REG','XGB_RAW')]:
            mod=fit_one(family,X,old,101);out[col]=predict(mod,family,XP)
        out=canonical_forecasts(out)
        merged=d['reference'].merge(out,on=['signal_date','ticker'],how='left',suffixes=('_reference',''),validate='one_to_one')
        errors={}
        for col in ['ET_RAW','XGB_RAW']:
            assert np.array_equal(merged[col].isna(),merged[col+'_reference'].isna())
            errors[col]=float(np.nanmax(abs(merged[col]-merged[col+'_reference'])))
            assert errors[col]==0,(market,col,errors[col])
        records.append({'market':market,'year':2022,'models_refitted':2,'errors':errors})
        print('ORIGINAL_PARITY',market,errors,flush=True)
    atomic_json(ROOT/'results/ORIGINAL_PARITY.json',records)

def batch(task):
    market,year,seed=task;start=time.time();p=ROOT/'inputs/annual'/f'{market}_{year}.joblib'
    known={f"{r['market']}_{r['year']}":r for r in json.loads((ROOT/'results/INPUT_AUDIT.json').read_text())}
    assert sha256(p)==known[f'{market}_{year}']['prepared_sha256']
    d=joblib.load(p);assert d['train_keys'].exit_date_63.max()<pd.Timestamp(year,1,1)
    assert set(np.unique(d['binary']))=={0,1}
    meta={'market':market,'year':year,'seed':seed,'input_sha256':sha256(p),'input_audit':d['metadata'],'parameters':{f:parameters(f,seed) for f in FAMILIES},'environment':ENV,'code_sha256':{p.name:sha256(p) for p in [Path(__file__),ROOT/'src/objectives.py']}}
    key=hashlib.sha256(json.dumps(meta,sort_keys=True).encode()).hexdigest()
    dest=ROOT/'models'/market/str(year)/str(seed);dest.mkdir(parents=True,exist_ok=True)
    if valid_checkpoint(dest,key):return {'market':market,'year':year,'seed':seed,'state':'verified_resume','seconds':0}
    imp=SimpleImputer(strategy='median',keep_empty_features=True);X=imp.fit_transform(d['X']);XP=imp.transform(d['XP'])
    joblib.dump(imp,dest/'IMPUTER.joblib',compress=3);out=d['predict_keys'].copy();names=['IMPUTER.joblib']
    for family in FAMILIES:
        model=fit_one(family,X,d,seed);out[family]=predict(model,family,XP)
        assert np.isfinite(out[family]).all()
        if family.endswith('CLASS'):assert out[family].between(0,1).all()
        if family.startswith('ET'):
            name=family+'.joblib';joblib.dump(model,dest/name,compress=3)
        else:
            name=family+'.ubj';model.save_model(dest/name)
        names.append(name)
    out=canonical_forecasts(out);out.to_csv(dest/'predictions.csv.gz',index=False,compression='gzip')
    meta['seconds']=round(time.time()-start,2);atomic_json(dest/'audit.json',meta)
    complete_checkpoint(dest,key,names+['predictions.csv.gz','audit.json'],{'models':len(FAMILIES),'rows':len(out)})
    assert valid_checkpoint(dest,key)
    return {'market':market,'year':year,'seed':seed,'state':'complete','seconds':meta['seconds'],'training_rows':len(X),'predict_rows':len(XP)}

def assemble():
    parts=[]
    for m in ['EU','USA']:
        for seed in SEEDS:
            frames=[]
            for year in range(2019,2027):
                path=ROOT/'models'/m/str(year)/str(seed);meta=json.loads((path/'COMPLETE.json').read_text());assert valid_checkpoint(path,meta['key'])
                f=pd.read_csv(path/'predictions.csv.gz',parse_dates=['signal_date'],float_precision='round_trip');f['year']=year;frames.append(f)
            out=pd.concat(frames,ignore_index=True);assert not out.duplicated(['signal_date','ticker']).any()
            out.to_csv(ROOT/'results'/f'{m}_S{seed}_PREDICTIONS.csv.gz',index=False,compression='gzip')
            parts.append({'market':m,'seed':seed,'rows':len(out)})
    atomic_json(ROOT/'results/TRAINING_COMPLETE.json',{'new_models':240,'annual_seed_batches':48,'original_parity_refits':4,'families':FAMILIES,'seeds':SEEDS,'forecasts':parts})

if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('--parity-only',action='store_true');ap.add_argument('--workers',type=int,default=3);args=ap.parse_args()
    if args.parity_only:original_parity()
    else:
        if not (ROOT/'results/ORIGINAL_PARITY.json').is_file():raise RuntimeError('Run original parity first')
        tasks=[(m,y,s) for s in SEEDS for y in range(2019,2027) for m in ['EU','USA']];rows=[];t=time.time()
        with concurrent.futures.ProcessPoolExecutor(max_workers=args.workers) as pool:
            futures={pool.submit(batch,z):z for z in tasks}
            for f in concurrent.futures.as_completed(futures):
                z=f.result();rows.append(z);atomic_json(ROOT/'results/TRAIN_PROGRESS.json',{'done':len(rows),'total':len(tasks),'rows':rows});print('BATCH',len(rows),json.dumps(z),'elapsed',round(time.time()-t,1),flush=True)
        assemble();print('DONE',len(rows)*5,'models',round(time.time()-t,1),flush=True)
