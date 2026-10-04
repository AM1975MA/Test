#!/usr/bin/env python3
"""Frozen annual Compact21 experiment; native training, common and native inference."""
from __future__ import annotations
import argparse, hashlib, importlib.metadata, json, subprocess, sys, tempfile, time
from pathlib import Path
import numpy as np
import pandas as pd
ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT),str(ROOT/'vendor/etf_trader_v2/src')]
from etf_trader.source_only import kernel as k
from ranker_stability_v1.run_ranker_benchmark_full import load, train_frame, align, stability, quality
from compact21_stability_v1.quantization import ScaleAwareQuantizer
from compact21_stability_v1.targets import training_labels
VARIANTS=('BASE','Q4','ORDINAL','ECON1BP','Q4_ECON1BP','SCALE','SCALE_ECON1BP')
KEYS=['signal_date','ticker']
PAIRS=((1,2),(1,3),(2,3))

def matrix(df):
    return df[k.F2D_FEATURES].replace([np.inf,-np.inf],np.nan)

def prepared(train,tests,variant,cutoff):
    X=matrix(train); T=[matrix(t) for t in tests]; audit={'kind':'identity'}
    if variant.startswith('Q4'):
        X=X.round(4); T=[z.round(4) for z in T]; audit={'kind':'Q4','decimals':4}
    elif variant.startswith('SCALE'):
        q=ScaleAwareQuantizer(k.F2D_FEATURES).fit(X)
        X=q.transform(X); T=[q.transform(z) for z in T]; audit=q.to_dict()
    mode='economic' if 'ECON1BP' in variant else ('ordinal' if variant=='ORDINAL' else 'legacy')
    y=training_labels(train,mode=mode,cutoff=cutoff)
    return X,T,y,audit

def fit(train,tests,variant,year,tmp,tag):
    cutoff=pd.Timestamp(year,1,1)
    X,T,y,audit=prepared(train,tests,variant,cutoff)
    params=dict(k.COMPACT_PARAMS); rounds=int(params.pop('n_estimators'));params.pop('n_jobs',None)
    groups=train.groupby('signal_date',sort=True).size().to_numpy()
    if not len(train) or not all(len(z) for z in tests): raise ValueError('Empty fit or inference')
    if not np.array_equal(train[KEYS].to_numpy(),train.sort_values(KEYS)[KEYS].to_numpy()): raise ValueError('Ungrouped rows')
    path=tmp/f'{tag}.npz'; np.savez(path,Xtr=X.to_numpy(),Xte=pd.concat(T).to_numpy(),y=y,groups=groups)
    predictions=[]; start=time.perf_counter()
    for seed in k.COMPACT_SEEDS:
        out=tmp/f'{tag}_{seed}.npy'
        subprocess.run([sys.executable,str(Path(k.__file__).with_name('_xgb_worker.py')),'--data',str(path),'--seed',str(seed),'--threads','1','--rounds',str(rounds),'--params-json',json.dumps(params),'--output',str(out)],check=True,capture_output=True,text=True)
        predictions.append(np.load(out))
    p=np.mean(predictions,axis=0)
    if not np.isfinite(p).all(): raise ValueError('Nonfinite predictions')
    pos=0; answer=[]
    for z in T: answer.append(p[pos:pos+len(z)]);pos+=len(z)
    return answer, audit, y, time.perf_counter()-start

def compare_native(tests,predictions):
    frames=[]
    for i in (1,2,3):
        z=tests[i][KEYS].copy();z['p']=predictions[i];frames.append(z)
    a=align(frames)
    return {f'{i}-{j}':stability(a[0][KEYS],a[i-1].p.to_numpy(),a[j-1].p.to_numpy()) for i,j in PAIRS}

def label_compare(trains,ys):
    # Label integer ids may shift when another distinct bin appears. Pairwise
    # relation flips and tie transitions identify the actual training changes.
    frames=[]
    for i in (1,2,3):
        z=trains[i][KEYS].copy();z['y']=ys[i];frames.append(z)
    a=align(frames);out={}
    for i,j in PAIRS:
        flips=[];total=0;changed=0
        for _,g in a[0].groupby('signal_date'):
            ix=g.index.to_numpy();va=a[i-1].loc[ix,'y'].to_numpy();vb=a[j-1].loc[ix,'y'].to_numpy()
            tri=np.triu_indices(len(ix),1)
            ca=np.sign(va[:,None]-va[None,:])[tri];cb=np.sign(vb[:,None]-vb[None,:])[tri]
            total+=len(ca);changed+=int(np.sum(ca!=cb))
        out[f'{i}-{j}']={'integer_id_disagreement':float(np.mean(a[i-1].y!=a[j-1].y)),'pair_relation_disagreement':changed/total if total else 0.0,'pairs':total}
    return out

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--variant',choices=VARIANTS,required=True)
    for i in (1,2,3): ap.add_argument(f'--r{i}',required=True)
    ap.add_argument('--out',required=True);ap.add_argument('--years',default=','.join(map(str,range(2017,2027))))
    a=ap.parse_args();years=list(map(int,a.years.split(',')))
    if not years or len(years)!=len(set(years)) or any(y not in range(2017,2027) for y in years): raise ValueError('Invalid annual folds')
    R={i:load(Path(getattr(a,f'r{i}'))) for i in (1,2,3)}
    out=Path(a.out);out.parent.mkdir(parents=True,exist_ok=True)
    res={'status':'RUNNING','variant':a.variant,'years':years,'per_year':{},'environment':{n:importlib.metadata.version(n) for n in ('numpy','pandas','scikit-learn','xgboost','scipy','pyarrow')},'input_sha256':{str(i):hashlib.sha256((Path(getattr(a,f'r{i}'))/'TI_COMPACT.parquet').read_bytes()).hexdigest() for i in (1,2,3)}}
    with tempfile.TemporaryDirectory() as td:
        for year in years:
            trains={i:train_frame(R[i],year) for i in (1,2,3)}
            tests={}
            for i in (1,2,3):
                f=R[i];valid=f[k.F2D_FEATURES].notna().sum(axis=1)>=30
                tests[i]=f[(f.signal_date.dt.year==year)&(f.signal_date<='2026-06-30')&valid].sort_values(KEYS).reset_index(drop=True)
                if tests[i].duplicated(KEYS).any() or trains[i].duplicated(KEYS).any():raise ValueError('Duplicate keys')
            common=align([tests[i] for i in (1,2,3)])[1]
            if common.empty: raise ValueError('No common evaluation rows')
            pcs={};pns={};ys={};audits={};times={}
            for i in (1,2,3):
                p,au,y,t=fit(trains[i],[common,tests[i]],a.variant,year,Path(td),f'{year}_{i}')
                pcs[i],pns[i]=p;ys[i]=y;audits[str(i)]=au;times[str(i)]=t
            pp,_,_,_=fit(trains[2],[common,tests[2]],a.variant,year,Path(td),f'{year}_det')
            delta=float(np.max(np.abs(pp[0]-pcs[2])))
            qualities={}
            for i in (1,2,3):
                eval_mask=(tests[i].target_rank_21.notna()&tests[i].exit_date_21.notna()&(tests[i].exit_date_21<=pd.Timestamp('2026-07-01'))).to_numpy()
                if not eval_mask.any(): raise ValueError('No mature quality rows')
                qualities[str(i)]=quality(tests[i].loc[eval_mask],pns[i][eval_mask])
            matpass=all(bool((trains[i].signal_date<pd.Timestamp(year,1,1)).all()&(trains[i].exit_date_21<pd.Timestamp(year,1,1)).all()) for i in (1,2,3))
            cell={'common_inference':{f'{i}-{j}':stability(common[KEYS],pcs[i],pcs[j]) for i,j in PAIRS},'native_inference':compare_native(tests,pns),'quality':qualities,'label_changes':label_compare(trains,ys),'transforms':audits,'train_rows':{str(i):len(trains[i]) for i in (1,2,3)},'test_rows':{str(i):len(tests[i]) for i in (1,2,3)},'common_test_rows':len(common),'maturity_PASS':matpass,'determinism':{'max_abs':delta,'PASS':delta==0.0},'fit_seconds':times}
            res['per_year'][str(year)]=cell;out.write_text(json.dumps(res,indent=2,allow_nan=False)+'\n')
            print(json.dumps({'year':year,'variant':a.variant,'rank_mad_mean':np.mean([q['rank_mean_abs'] for q in cell['common_inference'].values()]),'maturity':matpass,'determinism':delta}),flush=True)
    res['aggregate']={}
    for scope in ('common_inference','native_inference','quality'):
        rows=[q for y in res['per_year'].values() for q in y[scope].values()]
        res['aggregate'][scope]={f:float(np.mean([z[f] for z in rows])) for f in rows[0]}
    res['aggregate_by_pair']={scope:{pair:{f:float(np.mean([z[scope][pair][f] for z in res['per_year'].values()])) for f in next(iter(res['per_year'].values()))[scope][pair]} for pair in ('1-2','1-3','2-3')} for scope in ('common_inference','native_inference')}
    res['ALL_MATURITY_PASS']=all(z['maturity_PASS'] for z in res['per_year'].values())
    res['ALL_DETERMINISM_PASS']=all(z['determinism']['PASS'] for z in res['per_year'].values())
    res['status']='COMPACT21_STABILITY_V1_BENCHMARK_COMPLETE';out.write_text(json.dumps(res,indent=2,allow_nan=False)+'\n')
if __name__=='__main__':main()
