"""Controlled matched first-layer representation experiments. No outcome selection."""
from bridge import *
from schema import column_parameters
import numpy as np,pandas as pd,xgboost as xgb,sklearn,joblib,json,hashlib,time,argparse,concurrent.futures
from functools import lru_cache
from sklearn.impute import SimpleImputer
from sklearn.ensemble import ExtraTreesRegressor
OUT=ROOT/'results';MODELS=ROOT/'models';MODELS.mkdir(exist_ok=True)
PACKS=['CORE','PATH','NULL7101','NULL7102','NULL7103']
CONFIGS={f'{mode}_{pack}_S101':{'mode':mode,'pack':pack,'seed':101,'reverse':False} for mode in ['FIXED','ALL'] for pack in PACKS}
CONFIGS['REVERSE42_S101']={'mode':'LEGACY','pack':'REF42','seed':101,'reverse':True}
for seed in [211,307]:
    CONFIGS[f'REF42_S{seed}']={'mode':'LEGACY','pack':'REF42','seed':seed,'reverse':False}
    for pack in ['CORE','PATH']:
        CONFIGS[f'FIXED_{pack}_S{seed}']={'mode':'FIXED','pack':pack,'seed':seed,'reverse':False}
ENV={'numpy':np.__version__,'pandas':pd.__version__,'sklearn':sklearn.__version__,'xgboost':xgb.__version__}

@lru_cache(maxsize=2)
def get_inputs(market,year):return joblib.load(ROOT/'cache'/f'{market}_{year}.joblib')

def effective_parameters(conf,width):
    m,c=column_parameters(width,conf['mode'])
    return (dict(ET_MODEL_KW,max_features=m,random_state=conf['seed']),dict(XGB_MODEL_KW,colsample_bytree=c,random_state=conf['seed']))

def one(task):
    market,name,year=task;start=time.time();conf=CONFIGS[name];d=get_inputs(market,year)
    X,XP=d['matrices'][conf['pack']]
    columns=d['metadata']['columns42'] if conf['pack']=='REF42' else CORE+(PATH_COLS if conf['pack']!='CORE' else [])
    if conf['reverse']:X=X[:,::-1];XP=XP[:,::-1];columns=columns[::-1]
    par_et,par_xgb=effective_parameters(conf,X.shape[1]);y=d['y']
    a=dict(market=market,config=name,configuration=conf,year=year,input_metadata=d['metadata'],columns=columns,actual_input_hashes=[arr_hash(X),arr_hash(XP),arr_hash(y)],parameters_ET=par_et,parameters_XGB=par_xgb,nominal_ET_features=(int(X.shape[1]*par_et['max_features']) if isinstance(par_et['max_features'],float) else par_et['max_features']),nominal_XGB_features=int(np.floor(np.float32(par_xgb['colsample_bytree'])*X.shape[1])),environment=ENV,source_hashes={p.name:sha256(p) for p in [Path(__file__),ROOT/'src/schema.py',ROOT/'src/bridge.py']})
    key=hashlib.sha256(json.dumps(a,sort_keys=True).encode()).hexdigest();f=MODELS/market/name/str(year);f.mkdir(parents=True,exist_ok=True)
    if valid_checkpoint(f,key):return dict(market=market,config=name,year=year,state='verified_resume',seconds=round(time.time()-start,2))
    assert pd.to_datetime(d['train_exits']).max()<pd.Timestamp(year,1,1)
    imp=SimpleImputer(strategy='median',keep_empty_features=True);xx=imp.fit_transform(X);xp=imp.transform(XP)
    et=ExtraTreesRegressor(n_jobs=1,**par_et).fit(xx,y)
    gb=xgb.XGBRegressor(n_jobs=1,**par_xgb).fit(xx,y)
    assert all(t.max_features_==a['nominal_ET_features'] for t in et.estimators_)
    joblib.dump({'imputer':imp,'model':et},f/'ET.joblib',compress=3);joblib.dump(imp,f/'IMPUTER.joblib',compress=3);gb.save_model(f/'HYBRID_XGB.ubj')
    h=d['predict_keys'].copy();h['ET_RAW']=et.predict(xp);h['XGB_RAW']=gb.predict(xp)
    h['ET']=h.groupby('signal_date').ET_RAW.rank(pct=True);h['XGB']=h.groupby('signal_date').XGB_RAW.rank(pct=True)
    p=d['reference'].drop(columns=['ET','XGB','ET_RAW','XGB_RAW']).merge(h,on=['signal_date','ticker'],how='outer',validate='one_to_one')
    p=canonical_forecasts(p.sort_values(['signal_date','ticker']).reset_index(drop=True));ref=d['reference']
    assert p[['signal_date','ticker']].equals(ref[['signal_date','ticker']])
    for k in ['RETURN_RAW','RETURN']:np.testing.assert_allclose(p[k],ref[k],atol=0,rtol=0,equal_nan=True)
    for k in ['ET_RAW','ET','XGB_RAW','XGB']:assert np.array_equal(p[k].isna(),ref[k].isna())
    p.to_csv(f/'predictions.csv.gz',index=False,compression='gzip');a['seconds']=round(time.time()-start,2)
    atomic_json(f/'audit.json',a)
    complete_checkpoint(f,key,['ET.joblib','IMPUTER.joblib','HYBRID_XGB.ubj','predictions.csv.gz','audit.json'],{'models':2,'market':market,'config':name,'year':year})
    assert valid_checkpoint(f,key)
    return dict(market=market,config=name,year=year,state='complete',seconds=round(time.time()-start,2),features=X.shape[1])

def assemble(name):
    paths=[]
    for market in ['EU','USA']:
        frames=[]
        for year in range(2019,2027):
            f=MODELS/market/name/str(year)
            if not (f/'COMPLETE.json').exists():return False
            m=json.loads((f/'COMPLETE.json').read_text());assert valid_checkpoint(f,m['key'])
            frames.append(pd.read_csv(f/'predictions.csv.gz',parse_dates=['signal_date','source_date'],float_precision='round_trip'))
        p=pd.concat(frames,ignore_index=True);assert not p.duplicated(['signal_date','ticker']).any()
        out=OUT/f'{market}_{name}_FORECASTS.csv.gz';p.to_csv(out,index=False,compression='gzip');paths.append({'path':str(out.relative_to(ROOT)),'bytes':out.stat().st_size,'sha256':sha256(out)})
    atomic_json(ROOT/'checkpoints'/f'02_{name}.json',{'status':'complete','new_models':32,'annual_batches':16,'configuration':CONFIGS[name],'forecasts':paths})
    return True

if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('--configs',default=','.join(CONFIGS));ap.add_argument('--workers',type=int,default=4);args=ap.parse_args();names=args.configs.split(',');assert set(names)<=set(CONFIGS)
    tasks=[(m,n,y) for n in names for y in range(2019,2027) for m in ['EU','USA']]
    start=time.time();rows=[];done=set()
    with concurrent.futures.ProcessPoolExecutor(max_workers=args.workers) as pool:
        futs={pool.submit(one,t):t for t in tasks}
        for fut in concurrent.futures.as_completed(futs):
            r=fut.result();rows.append(r);print('FIT',json.dumps(r),'elapsed',round(time.time()-start,1),flush=True)
            atomic_json(OUT/'TRAIN_STATUS.json',{'completed':len(rows),'total':len(tasks),'elapsed_seconds':round(time.time()-start,1),'rows':rows})
            name=r['config']
            if name not in done and assemble(name):done.add(name);print('FAMILY_PERSISTED',name,flush=True)
    for name in names:assert assemble(name)
    print('ALL_DONE',len(tasks),'batches',len(tasks)*2,'models',round(time.time()-start,1),flush=True)
