"""Post-result same-dimension null-information test; no winner selection."""
from bootstrap import *
from train_pack import annual_inputs,enrich,new_panel,reference,arr_hash,key_hash
from feature_blocks import PATH
from diagnostic_primitives import permute_block,canonicalize,restore_columns
import pandas as pd,numpy as np,xgboost as xgb,joblib,json,hashlib,time,concurrent.futures
from sklearn.impute import SimpleImputer
from sklearn.ensemble import ExtraTreesRegressor
OUT=ROOT/'results';NULL=ROOT/'null_models';NULL.mkdir(exist_ok=True)
ALIASES={x+'_mean_rank':x+'_univ_rank' for x in ['cluster_acc_5_21','cluster_eff_63','cluster_ret_21']}

def one(task):
    market,seed,year=task;f=NULL/market/str(seed)/str(year);f.mkdir(parents=True,exist_ok=True)
    tr,pr,cols,y,groups,ht,pp,hc,horizon=annual_inputs(market,'R_RSI_DOMAIN',year)
    hc=[c for c in hc if c not in ALIASES];new=[c+'_pct' for c in PATH]
    extra=permute_block(new_panel(market,'HYBRID'),new,seed,market)
    ht=enrich(ht,extra,new);pp=enrich(pp,extra,new);hc=hc+new
    HX=ht[hc].to_numpy(float);HP=pp[hc].to_numpy(float);hy=ht.TARGET.to_numpy(float)
    a={'market':market,'permutation_seed':seed,'year':year,'columns':hc,'train_keys':key_hash(ht),'predict_keys':key_hash(pp),'matrices':[arr_hash(v) for v in [HX,HP,hy]],'last_label_exit':str(ht.exit_date_63.max()),'code':sha256(Path(__file__)),'primitives':sha256(ROOT/'src/diagnostic_primitives.py')}
    key=hashlib.sha256(json.dumps(a,sort_keys=True).encode()).hexdigest()
    if valid_checkpoint(f,key):return task
    imp=SimpleImputer(strategy='median',keep_empty_features=True);x=imp.fit_transform(HX);xp=imp.transform(HP)
    et=ExtraTreesRegressor(n_jobs=1,**ET_MODEL_KW).fit(x,hy);gb=xgb.XGBRegressor(n_jobs=1,**XGB_MODEL_KW).fit(x,hy)
    joblib.dump({'imputer':imp,'model':et},f/'ET.joblib',compress=3);gb.save_model(f/'HYBRID_XGB.ubj')
    ref=reference(market);p=ref[ref.signal_date.dt.year.eq(year)].copy()
    h=pp[['signal_date','ticker']].copy();h['ET_RAW']=et.predict(xp);h['XGB_RAW']=gb.predict(xp)
    h['ET']=h.groupby('signal_date').ET_RAW.rank(pct=True);h['XGB']=h.groupby('signal_date').XGB_RAW.rank(pct=True)
    p=p.drop(columns=['ET','ET_RAW','XGB','XGB_RAW']).merge(h,on=['signal_date','ticker'],how='outer',validate='one_to_one')
    p=canonical_forecasts(p.sort_values(['signal_date','ticker']).reset_index(drop=True));p.to_csv(f/'predictions.csv.gz',index=False,compression='gzip')
    atomic_json(f/'audit.json',a);complete_checkpoint(f,key,['ET.joblib','HYBRID_XGB.ubj','audit.json','predictions.csv.gz'],{'auxiliary_models':2})
    return task

if __name__=='__main__':
    start=time.time();storage=[]
    for market in ['EU','USA']:
        hp=pd.read_pickle(CAL/f'{market}_HYBRID.pkl')
        original=hp[list(FEATURES_42)];compressed,meta=canonicalize(original,ALIASES)
        pd.testing.assert_frame_equal(restore_columns(compressed,meta),original)
        compressed.to_pickle(ROOT/'inputs'/f'{market}_HYBRID39_CANONICAL.pkl');atomic_json(ROOT/'inputs'/f'{market}_HYBRID_ALIASES.json',meta)
        storage.append({'market':market,'rows':len(hp),'stored_columns':39,'learner_view_columns':42,'exact_reconstruction':True,'new_economic_effect':'none; lossless representation'})
    atomic_json(OUT/'LOSSLESS_DUPLICATE_CANONICALIZATION.json',{'checks':storage})
    tasks=[(m,s,y) for s in [7101,7102,7103] for y in range(2019,2027) for m in ['EU','USA']]
    with concurrent.futures.ProcessPoolExecutor(max_workers=4) as pool:
        for i,r in enumerate(pool.map(one,tasks)):
            print('NULL_FIT',i+1,r,'elapsed',round(time.time()-start,1),flush=True)
    for market in ['EU','USA']:
        for seed in [7101,7102,7103]:
            frames=[]
            for year in range(2019,2027):
                f=NULL/market/str(seed)/str(year);a=json.loads((f/'COMPLETE.json').read_text());assert valid_checkpoint(f,a['key'])
                frames.append(pd.read_csv(f/'predictions.csv.gz',parse_dates=['signal_date','source_date'],float_precision='round_trip'))
            pd.concat(frames,ignore_index=True).to_csv(OUT/f'{market}_H_NULL{seed}_FORECASTS.csv.gz',index=False,compression='gzip')
    atomic_json(OUT/'NULL_FIT_SUMMARY.json',{'auxiliary_models':96,'annual_batches':48,'permutation_seeds':[7101,7102,7103],'status':'fits complete; not main candidate models','elapsed':round(time.time()-start,1)})
    print('NULL_ALL_DONE',flush=True)
