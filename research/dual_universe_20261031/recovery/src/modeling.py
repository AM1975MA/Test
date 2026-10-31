"""Atomic model/year checkpoints; no use of current-year outcomes in training."""
from pathlib import Path
import os,sys,json,pickle,io,gzip,time,hashlib
import numpy as np,pandas as pd
from common import mature_mask,return_grades,atomic_bytes,atomic_json,digest
ROOT=Path(__file__).resolve().parents[1]
MULTI=('BASE_MATURE63','MULTI_453520','CONSENSUS_MULTI')
MODELS=('BASE_D4','RETURN_D4','PAIR127','RIDGE125')+MULTI
SEEDS=(101,202,303)

def training_rows(panel,year,model):
    x=panel.loc[mature_mask(panel,year,model in MULTI)].copy()
    x=x[x.groupby('signal_date').ticker.transform('size')>=2]
    return x.sort_values(['signal_date','ticker']).reset_index(drop=True)

def target_values(train,model):
    if model=='RETURN_D4':
        parts=[return_grades(g.fwd_ret_21.to_numpy()) for _,g in train.groupby('signal_date',sort=True)]
        return np.concatenate(parts)
    if model=='MULTI_453520':v=.45*train.target_rank_21+.35*train.target_rank_42+.20*train.target_rank_63
    elif model=='CONSENSUS_MULTI':v=.35*train.target_rank_21+.30*train.target_rank_42+.20*train.target_rank_63+.15*train[['target_rank_21','target_rank_42','target_rank_63']].min(axis=1)
    else:v=train.target_rank_21
    return v.to_numpy(float) if model=='RIDGE125' else np.rint(v.to_numpy(float)*100).astype('int32')

def run_block(market,year,model):
    import xgboost as xgb
    from sklearn.pipeline import make_pipeline
    from sklearn.impute import SimpleImputer
    from sklearn.preprocessing import StandardScaler
    from sklearn.linear_model import Ridge
    sys.path.insert(0,str(ROOT.parent/'code'));import frozen_kernel as k
    t0=time.time();src=ROOT/'prepared'/f'{market}_panel.pkl';blob=src.read_bytes();p=pickle.loads(blob)
    sig=digest(blob+Path(__file__).read_bytes()+f'{market}:{year}:{model}'.encode())
    dest=ROOT/'checkpoints'/market/str(year);dest.mkdir(parents=True,exist_ok=True)
    datafile=dest/f'{model}.csv.gz';metafile=dest/f'{model}.json'
    if metafile.exists() and datafile.exists():
        meta=json.loads(metafile.read_text())
        if meta['signature']==sig and meta['output_sha256']==digest(datafile.read_bytes()):return {'cached':True,**meta}
        raise ValueError('Checkpoint digest changed; do not silently reuse or overwrite')
    train=training_rows(p,year,model);test=p.loc[p.eligible&(p.signal_date.dt.year==year)].copy().sort_values(['signal_date','ticker'])
    if not len(train) or not len(test):raise ValueError('Empty train or test')
    f=k.F2D_FEATURES;X=train[f].to_numpy('float32');Xt=test[f].to_numpy('float32');y=target_values(train,model)
    groups=train.groupby('signal_date',sort=True).size().to_numpy()
    parameters=dict(objective='rank:pairwise',eval_metric='ndcg@3',n_estimators=360,max_depth=4,learning_rate=.035,subsample=.85,colsample_bytree=.8,min_child_weight=8.,reg_lambda=8.,reg_alpha=.1,tree_method='hist',n_jobs=1,verbosity=0)
    if model=='PAIR127':parameters.update(max_depth=0,max_leaves=127,grow_policy='lossguide')
    if model=='RETURN_D4':parameters.update(objective='rank:ndcg',eval_metric='ndcg@5',ndcg_exp_gain=False,lambdarank_pair_method='topk',lambdarank_num_pair_per_sample=5)
    predictions=[];model_hashes=[]
    if model=='RIDGE125':
        est=make_pipeline(SimpleImputer(strategy='median',keep_empty_features=True),StandardScaler(),Ridge(alpha=30.))
        est.fit(X,y);predictions=[est.predict(Xt)];model_hashes=[digest(pickle.dumps(est,protocol=5))];parameters={'ridge_alpha':30.,'impute':'train median','scale':'train standard'}
    else:
        for seed in SEEDS:
            est=xgb.XGBRanker(**parameters,random_state=seed);est.fit(X,y,group=groups)
            predictions.append(est.predict(Xt));model_hashes.append(digest(bytes(est.get_booster().save_raw())))
    test=test[['signal_date','ticker']].copy();test['raw_score']=np.mean(predictions,axis=0);test['score']=test.groupby('signal_date').raw_score.rank(pct=True)
    assert np.isfinite(test.raw_score).all() and not test[['signal_date','ticker']].duplicated().any()
    content=gzip.compress(test.to_csv(index=False).encode(),mtime=0)
    maskhash=digest(train[['signal_date','ticker']].to_csv(index=False).encode())
    meta={'market':market,'year':year,'model':model,'signature':sig,'input_sha256':digest(blob),'output_sha256':digest(content),'training_rows':len(train),'prediction_rows':len(test),'training_months':len(groups),'last_train_signal':str(train.signal_date.max().date()),'max_label_exit':str(train[f'exit_date_{63 if model in MULTI else 21}'].max().date()),'cutoff':f'{year}-01-01','training_key_sha256':maskhash,'parameters':parameters,'seeds':list(SEEDS) if model!='RIDGE125' else [],'trained_model_hashes':model_hashes,'seconds':time.time()-t0,'status':'TRAINED_NOT_ECONOMICALLY_VALIDATED'}
    assert pd.Timestamp(meta['max_label_exit'])<pd.Timestamp(meta['cutoff'])
    atomic_bytes(datafile,content);atomic_json(metafile,meta)
    print(json.dumps({'market':market,'year':year,'model':model,'rows':len(train),'seconds':round(time.time()-t0,2)}),flush=True)
    return meta

if __name__=='__main__':
    import concurrent.futures,traceback
    jobs=[(m,y,model) for y in range(2019,2027) for m in ('USA','EU') for model in MODELS]
    workers=int(os.getenv('DUAL_WORKERS','4'))
    failed=[]
    with concurrent.futures.ProcessPoolExecutor(max_workers=workers) as pool:
        futs={pool.submit(run_block,*job):job for job in jobs}
        for n,fut in enumerate(concurrent.futures.as_completed(futs),1):
            try:out=fut.result()
            except Exception as e:
                failed.append({'job':futs[fut],'error':repr(e)});traceback.print_exc()
            atomic_json(ROOT/'TRAIN_PROGRESS.json',{'total':len(jobs),'completed':n-len(failed),'failed':failed,'pending':len(jobs)-n})
    if failed:raise RuntimeError(failed)
    print('ALL_MODEL_CHECKPOINTS_COMPLETE',len(jobs),flush=True)
