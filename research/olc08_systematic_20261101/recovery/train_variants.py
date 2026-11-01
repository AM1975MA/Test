"""Paired annual first-layer ablations, resumable by authenticated batch key.
Run BASE first. Every annual batch is atomic at the completion-marker boundary.
"""
import os
for key in ['OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS']:os.environ[key]='1'
from context import *
from recovery_core import *
import numpy as np,pandas as pd,xgboost as xgb,sklearn,joblib,time,argparse,concurrent.futures
from sklearn.ensemble import ExtraTreesRegressor
from sklearn.impute import SimpleImputer
OUT=ROOT/'results';FITS=ROOT/'fits';FITS.mkdir(exist_ok=True)
VARS=['BASE','R_RSI_DOMAIN','R_DOWN_SEMIDEV','R_NO_LIQUIDITY','R_PERCENTILE_ONLY','R_ORDINAL_LABEL','H_UNIQUE','H_NO_CONTEXT','H_TARGET21_MATCHED','H_TARGET21_FRESH']
ENV={'numpy':np.__version__,'pandas':pd.__version__,'sklearn':sklearn.__version__,'xgboost':xgb.__version__}
def arr_hash(a):
    a=np.ascontiguousarray(a);return hashlib.sha256(str(a.dtype).encode()+str(a.shape).encode()+a.tobytes()).hexdigest()
def key_hash(f):return hashlib.sha256(f[['signal_date','ticker']].to_csv(index=False).encode()).hexdigest()
def annual_inputs(market,variant,year):
    cutoff=pd.Timestamp(year,1,1);end=pd.Timestamp(year+1,1,1)
    cp=pd.read_pickle(CAL/f'{market}_COMPACT.pkl');hp=pd.read_pickle(CAL/f'{market}_HYBRID.pkl')
    if variant.startswith('R_') and variant in ['R_RSI_DOMAIN','R_DOWN_SEMIDEV']:
        patch=pd.read_pickle(ROOT/'inputs'/f'{market}_PATCH.pkl')
        assert cp[['signal_date','ticker']].equals(patch[['signal_date','ticker']])
        names=['rsi14','rsi14_pct'] if variant=='R_RSI_DOMAIN' else [f'downvol{h}{suffix}' for h in [21,63,126] for suffix in ['','_pct','_dev']]
        cp[names]=patch[names]
    cols=list(kernel.F2D_FEATURES)
    if variant=='R_NO_LIQUIDITY':cols=[c for c in cols if not c.startswith(('log_adv63','volume_surprise21'))]
    if variant=='R_PERCENTILE_ONLY':cols=[c for c in cols if c.endswith('_pct')]
    tr=cp[(cp.signal_date<cutoff)&(cp.exit_date_21<cutoff)&cp.fwd_ret_21.notna()&cp.eligible].sort_values(['signal_date','ticker'])
    tr=tr[tr.groupby('signal_date').ticker.transform('size')>=2].copy()
    pr=cp[(cp.signal_date>=cutoff)&(cp.signal_date<end)&cp.eligible].sort_values(['signal_date','ticker']).copy()
    labels,groups,meta=prepare_targets(tr,'RETURN_RANK_NDCG')
    if variant=='R_ORDINAL_LABEL':labels=np.rint(15*tr.groupby('signal_date').fwd_ret_21.rank(pct=True).to_numpy()).astype(np.int32)
    hp['TARGET']=corrected_target(hp)
    horizon=21 if variant=='H_TARGET21_FRESH' else 63
    if variant.startswith('H_TARGET21'):hp['TARGET']=hp.target_rank_21.astype(float).pow(1.5)
    ht=hp[(hp.signal_date<cutoff)&(hp[f'exit_date_{horizon}']<cutoff)&hp.TARGET.notna()].sort_values(['signal_date','ticker'])
    pp=hp[(hp.signal_date>=cutoff)&(hp.signal_date<end)].sort_values(['signal_date','ticker']).copy()
    hc=list(FEATURES_42)
    if variant=='H_UNIQUE':hc=json.loads((OUT/'DUPLICATES.json').read_text())['hybrid_unique_columns']
    if variant=='H_NO_CONTEXT':hc=[c for c in hc if not (c.startswith('cluster_') or '_vs_cluster' in c or '_cluster_rank' in c)]
    oldaudit=json.loads((CAL/f'{market}_FIT_AUDIT.json').read_text())
    for model,df,exitcol in [('RETURN',tr,'exit_date_21'),('HYBRID_ET_XGB',ht,f'exit_date_{horizon}')]:
        assert df[exitcol].max()<cutoff and df.signal_date.max()<cutoff
        expected=next(a for a in oldaudit if a['year']==year and a['model']==model)
        if not (model=='HYBRID_ET_XGB' and variant=='H_TARGET21_FRESH'):
            assert key_hash(df)==expected['training_keys_sha256'],(variant,market,year,model,'keys')
    return tr,pr,cols,labels,groups,ht,pp,hc,horizon

def run_one(task):
    market,variant,year=task;t=time.time()
    folder=FITS/market/variant/str(year);folder.mkdir(parents=True,exist_ok=True)
    tr,pr,cols,y,groups,ht,pp,hc,horizon=annual_inputs(*task)
    do_r=variant=='BASE' or variant.startswith('R_');do_h=variant=='BASE' or variant.startswith('H_')
    X=tr[cols].to_numpy(float);XP=pr[cols].to_numpy(float)
    X[~np.isfinite(X)]=np.nan;XP[~np.isfinite(XP)]=np.nan
    HX0=ht[hc].to_numpy(float);HP0=pp[hc].to_numpy(float)
    hy=ht.TARGET.to_numpy(float)
    sourcehash=sha256(Path(__file__))
    audit={'market':market,'variant':variant,'year':year,'environment':ENV,'source_sha256':sourcehash,'train_keys_return':key_hash(tr),'train_keys_hybrid':key_hash(ht),'n_return_train':len(tr),'n_hybrid_train':len(ht),'last_exit_return':str(tr.exit_date_21.max()),'last_exit_hybrid':str(ht[f'exit_date_{horizon}'].max()),'return_features':cols,'hybrid_features':hc,'prediction_keys_return':key_hash(pr),'prediction_keys_hybrid':key_hash(pp),'return_matrices':[arr_hash(a) for a in [X,XP,y,groups]],'hybrid_matrices':[arr_hash(a) for a in [HX0,HP0,hy]],'cutoff':str(pd.Timestamp(year,1,1))}
    key=hashlib.sha256(json.dumps(audit,sort_keys=True).encode()).hexdigest()
    if valid_checkpoint(folder,key):return {'market':market,'variant':variant,'year':year,'state':'verified_resume_skip','seconds':time.time()-t}
    if variant!='BASE':
        base=FITS/market/'BASE'/str(year)
        bm=json.loads((base/'COMPLETE.json').read_text());assert valid_checkpoint(base,bm['key'])
        p=pd.read_csv(base/'predictions.csv.gz',parse_dates=['signal_date','source_date'],float_precision='round_trip')
    else:p=pr[['signal_date','ticker','source_date']].copy()
    trained=[];reuse=False
    if do_r:
        if variant!='BASE':
            ba=json.loads((FITS/market/'BASE'/str(year)/'audit.json').read_text())
            reuse=audit['return_matrices']==ba['return_matrices'] and cols==ba['return_features']
        if not reuse:
            params,rounds,seeds=recipe('RETURN_RANK_NDCG');d=xgb.QuantileDMatrix(X,label=y,nthread=1);d.set_group(groups);test=xgb.QuantileDMatrix(XP,ref=d,nthread=1);preds=[]
            for seed in seeds:
                model=xgb.train(dict(params,nthread=1,seed=seed),d,num_boost_round=rounds,verbose_eval=False)
                name=f'RETURN_{seed}.ubj';model.save_model(folder/name);trained.append(name);preds.append(model.predict(test))
            rp=pr[['signal_date','ticker']].copy();rp['RETURN_RAW']=np.mean(preds,axis=0);rp['RETURN']=rp.groupby('signal_date').RETURN_RAW.rank(pct=True)
            p=p.drop(columns=['RETURN','RETURN_RAW'],errors='ignore').merge(rp,on=['signal_date','ticker'],how='outer',validate='one_to_one')
    if do_h:
        imp=SimpleImputer(strategy='median',keep_empty_features=True);HX=imp.fit_transform(HX0);HP=imp.transform(HP0)
        et=ExtraTreesRegressor(n_jobs=1,**ET_MODEL_KW).fit(HX,hy)
        gb=xgb.XGBRegressor(n_jobs=1,**XGB_MODEL_KW).fit(HX,hy)
        joblib.dump({'imputer':imp,'model':et},folder/'ET.joblib',compress=3);joblib.dump(imp,folder/'IMPUTER.joblib',compress=3);gb.save_model(folder/'HYBRID_XGB.ubj')
        trained+=['ET.joblib','HYBRID_XGB.ubj']
        hp=pp[['signal_date','ticker']].copy();hp['ET_RAW']=et.predict(HP);hp['XGB_RAW']=gb.predict(HP)
        hp['ET']=hp.groupby('signal_date').ET_RAW.rank(pct=True);hp['XGB']=hp.groupby('signal_date').XGB_RAW.rank(pct=True)
        p=p.drop(columns=['ET','XGB','ET_RAW','XGB_RAW'],errors='ignore').merge(hp,on=['signal_date','ticker'],how='outer',validate='one_to_one')
    p=p.sort_values(['signal_date','ticker']).reset_index(drop=True)
    p=canonical_forecasts(p)
    audit.update(trained_models=trained,exact_input_equivalent_to_baseline=reuse,seconds=time.time()-t,return_target_min=float(np.min(y)),return_target_max=float(np.max(y)))
    if variant=='BASE':
        ref=pd.read_csv(CAL/f'{market}_FORECASTS.csv.gz',parse_dates=['signal_date'],float_precision='round_trip')
        ref=ref[ref.signal_date.dt.year.eq(year)].sort_values(['signal_date','ticker']).reset_index(drop=True)
        assert ref[['signal_date','ticker']].equals(p[['signal_date','ticker']])
        errs={}
        for name in ['RETURN_RAW','RETURN','ET_RAW','ET','XGB_RAW','XGB']:
            a=p[name].to_numpy();b=ref[name].to_numpy();assert np.array_equal(np.isnan(a),np.isnan(b)),name
            err=float(np.nanmax(abs(a-b)));errs[name]=err;assert err==0,(task,name,err)
        audit['archived_prediction_parity']=errs
    p.to_csv(folder/'predictions.csv.gz',index=False,compression='gzip')
    atomic_json(folder/'audit.json',audit)
    names=[str(a.name) for a in folder.iterdir() if a.is_file() and a.name!='COMPLETE.json']
    complete_checkpoint(folder,key,names,{'trained_models':len(trained),'market':market,'variant':variant,'year':year})
    assert valid_checkpoint(folder,key)
    return {'market':market,'variant':variant,'year':year,'state':'complete','new_models':len(trained),'input_identity_reuse':reuse,'seconds':round(time.time()-t,2)}

def assemble(variants):
    for market in ['EU','USA']:
      for variant in variants:
        parts=[]
        for year in range(2019,2027):
            f=FITS/market/variant/str(year);m=json.loads((f/'COMPLETE.json').read_text());assert valid_checkpoint(f,m['key'])
            parts.append(pd.read_csv(f/'predictions.csv.gz',parse_dates=['signal_date'],float_precision='round_trip'))
        p=pd.concat(parts,ignore_index=True)
        assert not p.duplicated(['signal_date','ticker']).any()
        p.to_csv(OUT/f'{market}_{variant}_FORECASTS.csv.gz',index=False,compression='gzip')

if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('--variants',default='BASE');ap.add_argument('--workers',type=int,default=4);args=ap.parse_args()
    variants=args.variants.split(',');assert set(variants)<=set(VARS)
    tasks=[(m,v,y) for v in variants for y in range(2019,2027) for m in ['EU','USA']]
    start=time.time();status=[]
    with concurrent.futures.ProcessPoolExecutor(max_workers=args.workers) as pool:
        futures={pool.submit(run_one,t):t for t in tasks}
        for future in concurrent.futures.as_completed(futures):
            row=future.result();status.append(row);print('BATCH',json.dumps(row),flush=True)
            atomic_json(OUT/('FIT_STATUS_'+str(variants[0])+'.json'),{'complete_tasks':len(status),'total_tasks':len(tasks),'rows':status,'elapsed':time.time()-start})
    assemble(variants);print('ALL_DONE',variants,'tasks',len(tasks),'seconds',round(time.time()-start),flush=True)
