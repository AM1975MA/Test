"""Annual matched first-layer experiments; immutable complete batches and no tuning."""
import os
for key in ['OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS']:os.environ[key]='1'
from bootstrap import *
from feature_blocks import PATH,SESSION,LEADERSHIP,prune_training
from train_variants import annual_inputs,arr_hash,key_hash
import numpy as np,pandas as pd,xgboost as xgb,sklearn,joblib
import hashlib,json,time,argparse,concurrent.futures
from functools import lru_cache
from sklearn.ensemble import ExtraTreesRegressor
from sklearn.impute import SimpleImputer
VARS=['R_NO_LIQ','R_RANK46','R_PRUNE','R_PATH','R_SESSION','R_LEADERSHIP','R_ALL','R_PRUNE_ALL','H_UNIQUE','H_PATH','H_SESSION']
OUT=ROOT/'results';FITS=ROOT/'models';FITS.mkdir(exist_ok=True)
ENV={'numpy':np.__version__,'pandas':pd.__version__,'sklearn':sklearn.__version__,'xgboost':xgb.__version__}

@lru_cache(maxsize=4)
def new_panel(market,block):return pd.read_pickle(ROOT/'inputs'/f'{market}_NEW_{block}.pkl')

@lru_cache(maxsize=2)
def reference(market):return pd.read_csv(PARENT/'results'/f'{market}_R_RSI_DOMAIN_FORECASTS.csv.gz',parse_dates=['signal_date','source_date'],float_precision='round_trip')

def enrich(frame,extra,columns):
    if not columns:return frame
    keys=['signal_date','ticker']
    out=frame.merge(extra[keys+columns],on=keys,how='left',validate='one_to_one',sort=False)
    assert frame[keys].reset_index(drop=True).equals(out[keys].reset_index(drop=True))
    return out

def run_one(task):
    market,variant,year=task;start=time.time()
    # Parent function asserts identical mature training keys against the frozen CL01 audits.
    tr,pr,cols,y,groups,ht,pp,hc,horizon=annual_inputs(market,'R_RSI_DOMAIN',year)
    baseline_cols=list(cols);pruning=[];new=[]
    if variant=='R_NO_LIQ':cols=[c for c in cols if not c.startswith(('log_adv63','volume_surprise21'))]
    if variant=='R_RANK46':cols=[c for c in cols if c.endswith('_pct')]
    if variant in ['R_PRUNE','R_PRUNE_ALL']:cols,pruning=prune_training(tr,cols)
    if variant=='R_PATH':new=PATH
    if variant=='R_SESSION':new=SESSION
    if variant=='R_LEADERSHIP':new=LEADERSHIP
    if variant in ['R_ALL','R_PRUNE_ALL']:new=PATH+SESSION+LEADERSHIP
    tr=enrich(tr,new_panel(market,'RETURN'),new);pr=enrich(pr,new_panel(market,'RETURN'),new);cols=cols+new
    if variant.startswith('H_'):
        drops=['cluster_acc_5_21_mean_rank','cluster_eff_63_mean_rank','cluster_ret_21_mean_rank']
        for d in drops:
            same=d.replace('_mean_rank','_univ_rank');assert ht[d].equals(ht[same]) and pp[d].equals(pp[same])
        hc=[c for c in hc if c not in drops]
        hnew=[x+'_pct' for x in (PATH if variant=='H_PATH' else SESSION if variant=='H_SESSION' else [])]
        ht=enrich(ht,new_panel(market,'HYBRID'),hnew);pp=enrich(pp,new_panel(market,'HYBRID'),hnew);hc=hc+hnew
    X=tr[cols].to_numpy(float);XP=pr[cols].to_numpy(float);X[~np.isfinite(X)]=np.nan;XP[~np.isfinite(XP)]=np.nan
    HX=ht[hc].to_numpy(float);HP=pp[hc].to_numpy(float);hy=ht.TARGET.to_numpy(float)
    audit={'market':market,'variant':variant,'year':year,'environment':ENV,'cutoff':str(pd.Timestamp(year,1,1)),'return_train_keys':key_hash(tr),'hybrid_train_keys':key_hash(ht),'return_predict_keys':key_hash(pr),'hybrid_predict_keys':key_hash(pp),'n_return_train':len(tr),'n_hybrid_train':len(ht),'return_columns':cols,'hybrid_columns':hc,'last_exit_return':str(tr.exit_date_21.max()),'last_exit_hybrid':str(ht.exit_date_63.max()),'return_input_hashes':[arr_hash(a) for a in [X,XP,y,groups]],'hybrid_input_hashes':[arr_hash(a) for a in [HX,HP,hy]],'pruning':pruning,'source_hashes':{p.name:sha256(p) for p in [Path(__file__),ROOT/'src/feature_blocks.py',ROOT/'src/build_features.py']}}
    key=hashlib.sha256(json.dumps(audit,sort_keys=True).encode()).hexdigest()
    folder=FITS/market/variant/str(year);folder.mkdir(parents=True,exist_ok=True)
    if valid_checkpoint(folder,key):return dict(market=market,variant=variant,year=year,state='verified_resume',seconds=round(time.time()-start,1))
    ref=reference(market);p=ref[ref.signal_date.dt.year.eq(year)].copy();trained=[]
    if variant.startswith('R_'):
        params,rounds,seeds=recipe('RETURN_RANK_NDCG')
        d=xgb.QuantileDMatrix(X,label=y,nthread=1);d.set_group(groups)
        dt=xgb.QuantileDMatrix(XP,ref=d,nthread=1);pred=[]
        for seed in seeds:
            model=xgb.train(dict(params,nthread=1,seed=seed),d,num_boost_round=rounds,verbose_eval=False)
            name=f'RETURN_{seed}.ubj';model.save_model(folder/name);trained.append(name);pred.append(model.predict(dt))
        r=pr[['signal_date','ticker']].copy();r['RETURN_RAW']=np.mean(pred,axis=0);r['RETURN']=r.groupby('signal_date').RETURN_RAW.rank(pct=True)
        p=p.drop(columns=['RETURN_RAW','RETURN']).merge(r,on=['signal_date','ticker'],how='outer',validate='one_to_one')
    else:
        imp=SimpleImputer(strategy='median',keep_empty_features=True);a=imp.fit_transform(HX);b=imp.transform(HP)
        et=ExtraTreesRegressor(n_jobs=1,**ET_MODEL_KW).fit(a,hy)
        gb=xgb.XGBRegressor(n_jobs=1,**XGB_MODEL_KW).fit(a,hy)
        joblib.dump({'imputer':imp,'model':et},folder/'ET.joblib',compress=3)
        joblib.dump(imp,folder/'IMPUTER.joblib',compress=3);gb.save_model(folder/'HYBRID_XGB.ubj');trained=['ET.joblib','HYBRID_XGB.ubj']
        h=pp[['signal_date','ticker']].copy();h['ET_RAW']=et.predict(b);h['XGB_RAW']=gb.predict(b)
        h['ET']=h.groupby('signal_date').ET_RAW.rank(pct=True);h['XGB']=h.groupby('signal_date').XGB_RAW.rank(pct=True)
        p=p.drop(columns=['ET_RAW','XGB_RAW','ET','XGB']).merge(h,on=['signal_date','ticker'],how='outer',validate='one_to_one')
    p=canonical_forecasts(p.sort_values(['signal_date','ticker']).reset_index(drop=True))
    r=ref[ref.signal_date.dt.year.eq(year)].sort_values(['signal_date','ticker']).reset_index(drop=True)
    assert p[['signal_date','ticker']].equals(r[['signal_date','ticker']])
    for c in ['RETURN_RAW','RETURN','ET_RAW','ET','XGB_RAW','XGB']:assert np.array_equal(p[c].isna(),r[c].isna()),(task,c)
    unchanged=['ET_RAW','ET','XGB_RAW','XGB'] if variant.startswith('R_') else ['RETURN_RAW','RETURN']
    for c in unchanged:np.testing.assert_allclose(p[c],r[c],rtol=0,atol=0,equal_nan=True)
    audit.update(trained_models=trained,seconds=time.time()-start)
    p.to_csv(folder/'predictions.csv.gz',index=False,compression='gzip');atomic_json(folder/'audit.json',audit)
    complete_checkpoint(folder,key,[x.name for x in folder.iterdir() if x.is_file() and x.name!='COMPLETE.json'],{'new_models':len(trained),'variant':variant,'market':market,'year':year})
    assert valid_checkpoint(folder,key)
    return dict(market=market,variant=variant,year=year,state='complete',new_models=len(trained),return_feature_count=len(cols),hybrid_feature_count=len(hc),seconds=round(time.time()-start,1))

def assemble(variant):
    paths=[]
    for market in ['EU','USA']:
        parts=[]
        for year in range(2019,2027):
            f=FITS/market/variant/str(year)
            if not (f/'COMPLETE.json').exists():return False
            key=json.loads((f/'COMPLETE.json').read_text())['key'];assert valid_checkpoint(f,key)
            parts.append(pd.read_csv(f/'predictions.csv.gz',parse_dates=['signal_date','source_date'],float_precision='round_trip'))
        p=pd.concat(parts,ignore_index=True);assert not p.duplicated(['signal_date','ticker']).any()
        path=OUT/f'{market}_{variant}_FORECASTS.csv.gz';p.to_csv(path,index=False,compression='gzip');paths.append(path)
    atomic_json(ROOT/'checkpoints'/f'02_{variant}.json',{'variant':variant,'annual_batches':16,'markets':['EU','USA'],'forecasts':[{'path':str(p.relative_to(ROOT)),'sha256':sha256(p),'bytes':p.stat().st_size} for p in paths]})
    return True

if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('--variants',default=','.join(VARS));ap.add_argument('--workers',type=int,default=4);a=ap.parse_args()
    vs=a.variants.split(',');assert set(vs)<=set(VARS)
    tasks=[(m,v,y) for v in vs for y in range(2019,2027) for m in ['EU','USA']]
    status=[];finished=set();start=time.time()
    with concurrent.futures.ProcessPoolExecutor(max_workers=a.workers) as pool:
        futures={pool.submit(run_one,t):t for t in tasks}
        for fut in concurrent.futures.as_completed(futures):
            row=fut.result();status.append(row);print('FIT',json.dumps(row),flush=True)
            atomic_json(OUT/'TRAIN_STATUS.json',{'completed':len(status),'total':len(tasks),'elapsed':round(time.time()-start,1),'rows':status})
            v=row['variant']
            if v not in finished and assemble(v):finished.add(v);print('FAMILY_COMPLETE',v,flush=True)
    for v in vs:assert assemble(v)
    print('ALL_DONE',len(tasks),'batches','seconds',round(time.time()-start,1),flush=True)
