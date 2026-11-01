"""Frozen base learners with separate cumulative and incremental outcome heads."""
from __future__ import annotations
import os
for k in ('OMP_NUM_THREADS','MKL_NUM_THREADS','OPENBLAS_NUM_THREADS','NUMEXPR_NUM_THREADS'):os.environ[k]='1'
import json,time,hashlib,argparse,concurrent.futures
from pathlib import Path
import numpy as np,pandas as pd,joblib,sklearn,xgboost as xgb
from sklearn.impute import SimpleImputer
from sklearn.ensemble import ExtraTreesRegressor
from common import ROOT,P11,HEADS,SEEDS,MARKETS,PROTOCOL,readcsv
from ranking_core import horizon_labels
from recovery_core import sha256,atomic_json,complete_checkpoint,valid_checkpoint,canonical_forecasts
ENV={'numpy':np.__version__,'pandas':pd.__version__,'sklearn':sklearn.__version__,'xgboost':xgb.__version__}

def parameters(family,seed):
 if family not in ('ET','XGB') or seed not in SEEDS:raise ValueError('Undeclared family/seed')
 p=json.loads((P11/'inputs/PARENT_PARAMETERS.json').read_text())[family]
 return dict(p,random_state=seed)

def model(fam,X,y,seed):
 p=parameters(fam,seed)
 if fam=='ET':return ExtraTreesRegressor(n_jobs=1,**p).fit(X,y)
 return xgb.XGBRegressor(n_jobs=1,**p).fit(X,y)

def prepare():
 known={(r['market'],r['year']):r for r in json.loads((P11/'results/INPUT_AUDIT.json').read_text())};audit=[]
 for market in MARKETS:
  labels=readcsv(P11/f'inputs/{market}_LAYER_LABELS.csv.gz');ks=['signal_date','ticker']
  for year in range(2019,2027):
   p=P11/f'inputs/annual/{market}_{year}.joblib';assert sha256(p)==known[(market,year)]['prepared_sha256']
   d=joblib.load(p);f=d['train_keys'][ks].merge(labels,on=ks,sort=False,validate='one_to_one')
   pd.testing.assert_frame_equal(f[ks],d['train_keys'][ks].reset_index(drop=True))
   assert len(labels[labels.signal_date.isin(f.signal_date.unique())])==len(f)
   assert f.exit_date_63.notna().all() and f.exit_date_63.max()<pd.Timestamp(year,1,1)
   np.testing.assert_array_equal(.45*f.target_rank_21.to_numpy()**1.5+.35*f.target_rank_42.to_numpy()**1.5+.2*f.target_rank_63.to_numpy()**1.5,d['y'])
   ys=horizon_labels(f);dest=ROOT/f'inputs/{market}_{year}_HEADS.npz';np.savez_compressed(dest,**ys)
   assert all(np.isfinite(y).all() and len(y)==len(d['X']) for y in ys.values())
   audit.append(dict(market=market,year=year,source_sha256=sha256(p),heads_sha256=sha256(dest),rows=len(f),months=f.signal_date.nunique(),max_exit=str(f.exit_date_63.max()),cutoff=str(pd.Timestamp(year,1,1)),columns=d['columns']))
 atomic_json(ROOT/'results/INPUT_AUDIT.json',audit);print('PREPARED',len(audit),flush=True)

def parity():
 out=[]
 for market in MARKETS:
  d=joblib.load(P11/f'inputs/annual/{market}_2022.joblib');ref=readcsv(P11/f'models/{market}/2022/101/predictions.csv.gz')
  imp=SimpleImputer(strategy='median',keep_empty_features=True);X=imp.fit_transform(d['X']);XP=imp.transform(d['XP'])
  for fam in ['ET','XGB']:
   mod=model(fam,X,d['y'],101);pred=d['predict_keys'].copy();pred['p']=mod.predict(XP);pred=canonical_forecasts(pred)
   z=pred.merge(ref,on=['signal_date','ticker'],validate='one_to_one');err=float(np.max(abs(z.p-z[fam+'_REG'])))
   assert err==0,(market,fam,err);out.append(dict(market=market,family=fam,rows=len(z),error=err));print('PARITY',market,fam,err,flush=True)
 atomic_json(ROOT/'results/ORIGINAL_PARITY.json',dict(checks=out,environment=ENV,models_refitted=4))

def batch(task):
 market,year,seed=task;t=time.time();p=P11/f'inputs/annual/{market}_{year}.joblib';yp=ROOT/f'inputs/{market}_{year}_HEADS.npz'
 known={(r['market'],r['year']):r for r in json.loads((ROOT/'results/INPUT_AUDIT.json').read_text())}
 assert sha256(p)==known[(market,year)]['source_sha256'] and sha256(yp)==known[(market,year)]['heads_sha256']
 meta=dict(market=market,year=year,seed=seed,input_sha256=sha256(p),target_sha256=sha256(yp),environment=ENV,protocol_commit=PROTOCOL,parameters={f:parameters(f,seed) for f in ['ET','XGB']},code_sha256={n:sha256(ROOT/'src'/n) for n in ['train_heads.py','ranking_core.py','common.py']})
 key=hashlib.sha256(json.dumps(meta,sort_keys=True).encode()).hexdigest();dest=ROOT/f'models/{market}/{year}/{seed}';dest.mkdir(parents=True,exist_ok=True)
 if valid_checkpoint(dest,key):return dict(market=market,year=year,seed=seed,models=10,resumed=True)
 d=joblib.load(p);ys=np.load(yp);imp=SimpleImputer(strategy='median',keep_empty_features=True)
 X=imp.fit_transform(d['X']);XP=imp.transform(d['XP']);joblib.dump(imp,dest/'IMPUTER.joblib',compress=3)
 out=d['predict_keys'].copy();names=['IMPUTER.joblib']
 for h in HEADS:
  for fam in ['ET','XGB']:
   mod=model(fam,X,ys[h],seed);col=f'{h}_{fam}';out[col]=mod.predict(XP)
   assert np.isfinite(out[col]).all();name=col+('.joblib' if fam=='ET' else '.ubj')
   if fam=='ET':joblib.dump(mod,dest/name,compress=3)
   else:mod.save_model(dest/name)
   names.append(name)
 out=canonical_forecasts(out);out.to_csv(dest/'predictions.csv.gz',index=False,compression='gzip');meta['seconds']=round(time.time()-t,3)
 atomic_json(dest/'audit.json',meta);names+=['predictions.csv.gz','audit.json'];complete_checkpoint(dest,key,names,{'new_models':10})
 assert valid_checkpoint(dest,key)
 return dict(market=market,year=year,seed=seed,models=10,seconds=meta['seconds'])

def assemble():
 rows=[]
 for m in MARKETS:
  for s in SEEDS:
   frames=[]
   for y in range(2019,2027):
    dest=ROOT/f'models/{m}/{y}/{s}';c=json.loads((dest/'COMPLETE.json').read_text());assert valid_checkpoint(dest,c['key']);frames.append(readcsv(dest/'predictions.csv.gz'))
   p=pd.concat(frames,ignore_index=True).sort_values(['signal_date','ticker']).reset_index(drop=True)
   assert not p.duplicated(['signal_date','ticker']).any();p.to_csv(ROOT/f'results/{m}_S{s}_HEAD_FORECASTS.csv.gz',index=False,compression='gzip');rows.append(dict(market=m,seed=s,rows=len(p)))
 atomic_json(ROOT/'results/TRAINING_COMPLETE.json',dict(new_models=480,parity_fits=4,forecasts=rows,heads=HEADS))

if __name__=='__main__':
 ap=argparse.ArgumentParser();ap.add_argument('--prepare-parity',action='store_true');ap.add_argument('--workers',type=int,default=4);a=ap.parse_args()
 if a.prepare_parity:prepare();parity()
 else:
  assert (ROOT/'results/ORIGINAL_PARITY.json').is_file();done=[];t=time.time()
  with concurrent.futures.ProcessPoolExecutor(max_workers=a.workers) as pool:
   fs=[pool.submit(batch,(m,y,s)) for s in SEEDS for y in range(2019,2027) for m in MARKETS]
   for f in concurrent.futures.as_completed(fs):
    z=f.result();done.append(z);atomic_json(ROOT/'results/TRAIN_PROGRESS.json',dict(done=len(done),total=48,rows=done));print('BATCH',len(done),json.dumps(z),'elapsed',round(time.time()-t,1),flush=True)
  assemble();print('TRAINING_COMPLETE',480,flush=True)
