"""Reload every saved estimator and independently reproduce its persisted forecast."""
import os
for k in ('OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS'):os.environ[k]='1'
import json
import numpy as np,joblib,xgboost as xgb
from common import ROOT,P11,SEEDS,MARKETS,HEADS,readcsv
from recovery_core import canonical_forecasts,valid_checkpoint,atomic_json

def main():
 checks=[]
 for m in MARKETS:
  for y in range(2019,2027):
   d=joblib.load(P11/f'inputs/annual/{m}_{y}.joblib')
   for s in SEEDS:
    dest=ROOT/f'models/{m}/{y}/{s}';meta=json.loads((dest/'COMPLETE.json').read_text());assert valid_checkpoint(dest,meta['key'])
    imp=joblib.load(dest/'IMPUTER.joblib');xp=imp.transform(d['XP']);ref=readcsv(dest/'predictions.csv.gz')
    for h in HEADS:
     for fam in ('ET','XGB'):
      col=f'{h}_{fam}'
      if fam=='ET':mod=joblib.load(dest/(col+'.joblib'))
      else:mod=xgb.XGBRegressor(n_jobs=1);mod.load_model(dest/(col+'.ubj'))
      p=d['predict_keys'].copy();p['p']=mod.predict(xp);p=canonical_forecasts(p)
      z=ref.merge(p,on=['signal_date','ticker'],validate='one_to_one');error=float(np.max(abs(z[col]-z.p)));assert error==0,(m,y,s,col,error)
      checks.append(dict(market=m,year=y,seed=s,head=h,family=fam,rows=len(z),error=error))
   print('VERIFIED',m,y,flush=True)
 import pandas as pd
 pd.DataFrame(checks).to_csv(ROOT/'results/MODEL_RELOAD_VERIFICATION.csv',index=False)
 atomic_json(ROOT/'results/MODEL_RELOAD_COMPLETE.json',dict(models=len(checks),max_error=max(x['error'] for x in checks),all_hashes_valid=True))
 print('ALL_MODELS_VERIFIED',len(checks),flush=True)
if __name__=='__main__':main()
