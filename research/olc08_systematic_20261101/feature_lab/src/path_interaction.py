"""Missing 2x2 cell: original Hybrid42 plus path6, registered after main/null results."""
from bootstrap import *
from train_pack import annual_inputs,enrich,new_panel,reference,arr_hash,key_hash
from feature_blocks import PATH
import numpy as np,pandas as pd,xgboost as xgb,joblib,json,hashlib,time,concurrent.futures
from sklearn.impute import SimpleImputer
from sklearn.ensemble import ExtraTreesRegressor
OUT=ROOT/'results'

def one(task):
    market,year=task;folder=ROOT/'interaction_models'/market/str(year);folder.mkdir(parents=True,exist_ok=True)
    tr,pr,cols,y,groups,ht,pp,hc,horizon=annual_inputs(market,'R_RSI_DOMAIN',year)
    new=[x+'_pct' for x in PATH];ht=enrich(ht,new_panel(market,'HYBRID'),new);pp=enrich(pp,new_panel(market,'HYBRID'),new);hc=hc+new
    X=ht[hc].to_numpy(float);XP=pp[hc].to_numpy(float);target=ht.TARGET.to_numpy(float)
    audit={'market':market,'year':year,'variant':'H_PATH_KEEP','features':hc,'train_keys':key_hash(ht),'predict_keys':key_hash(pp),'last_exit':str(ht.exit_date_63.max()),'matrices':[arr_hash(a) for a in [X,XP,target]],'code':sha256(Path(__file__)),'training_hyperparameters':'unchanged ET_MODEL_KW/XGB_MODEL_KW from immutable parent'}
    key=hashlib.sha256(json.dumps(audit,sort_keys=True).encode()).hexdigest()
    if valid_checkpoint(folder,key):return task
    imp=SimpleImputer(strategy='median',keep_empty_features=True);xx=imp.fit_transform(X);xp=imp.transform(XP)
    et=ExtraTreesRegressor(n_jobs=1,**ET_MODEL_KW).fit(xx,target);gb=xgb.XGBRegressor(n_jobs=1,**XGB_MODEL_KW).fit(xx,target)
    joblib.dump({'imputer':imp,'model':et},folder/'ET.joblib',compress=3);gb.save_model(folder/'HYBRID_XGB.ubj')
    p=reference(market);p=p[p.signal_date.dt.year.eq(year)].copy()
    h=pp[['signal_date','ticker']].copy();h['ET_RAW']=et.predict(xp);h['XGB_RAW']=gb.predict(xp)
    h['ET']=h.groupby('signal_date').ET_RAW.rank(pct=True);h['XGB']=h.groupby('signal_date').XGB_RAW.rank(pct=True)
    p=p.drop(columns=['ET','ET_RAW','XGB','XGB_RAW']).merge(h,on=['signal_date','ticker'],validate='one_to_one',how='outer')
    p=canonical_forecasts(p.sort_values(['signal_date','ticker']).reset_index(drop=True));p.to_csv(folder/'predictions.csv.gz',index=False,compression='gzip')
    atomic_json(folder/'audit.json',audit);complete_checkpoint(folder,key,['ET.joblib','HYBRID_XGB.ubj','audit.json','predictions.csv.gz'])
    return task

if __name__=='__main__':
    start=time.time();tasks=[(m,y) for y in range(2019,2027) for m in ['EU','USA']]
    with concurrent.futures.ProcessPoolExecutor(max_workers=4) as pool:
        for t in pool.map(one,tasks):print('INTERACTION',t,round(time.time()-start,1),flush=True)
    for market in ['EU','USA']:
        frames=[]
        for year in range(2019,2027):
            f=ROOT/'interaction_models'/market/str(year);c=json.loads((f/'COMPLETE.json').read_text());assert valid_checkpoint(f,c['key'])
            frames.append(pd.read_csv(f/'predictions.csv.gz',parse_dates=['signal_date','source_date'],float_precision='round_trip'))
        pd.concat(frames,ignore_index=True).to_csv(OUT/f'{market}_H_PATH_KEEP_FORECASTS.csv.gz',index=False,compression='gzip')
    atomic_json(OUT/'INTERACTION_FIT_SUMMARY.json',{'models':32,'annual_batches':16,'new_hybrid_inputs':48,'postresult_diagnostic':True,'elapsed':round(time.time()-start,1)})
    print('INTERACTION_FITS_DONE',flush=True)
