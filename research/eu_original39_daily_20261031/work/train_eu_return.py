"""Original economic NDCG first-stage, EU165. Native Hybrid stays frozen."""
import os
for key in ['OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS']:os.environ[key]='1'
from research_common import B,SRC,training_mask,digest
import numpy as np,pandas as pd,inspect,json,time,concurrent.futures
from etf_trader.source_only import kernel as k
from compact21_return_v1.core import recipe,prepare_targets,native_x,sha_array
import xgboost as xgb
P=B/'inputs/eu/source_v4/input/EU165_SPECIALISTS_20261029'
OUT=B/'results';CP=OUT/'checkpoints';CP.mkdir(exist_ok=True)
def fit_seed(seed,year,xtr,xt,labels,groups,params,rounds):
 d=xgb.QuantileDMatrix(xtr,label=labels,nthread=1);d.set_group(groups)
 t=xgb.QuantileDMatrix(xt,ref=d,nthread=1)
 p=dict(params,nthread=1,seed=seed)
 model=xgb.train(p,d,num_boost_round=rounds,verbose_eval=False)
 model.save_model(CP/f'EU_RETURN_{year}_{seed}.ubj')
 return model.predict(t)
def main():
 t0=time.time();T=pd.read_csv(P/'input/universe.csv').ticker.tolist()
 frames={t:pd.read_csv(P/'prices'/f'{t}.csv',index_col=0,parse_dates=True,float_precision='round_trip').loc[:'2026-07-01'] for t in T}
 mats={fld:pd.DataFrame({t:f[fld] for t,f in frames.items()}) for fld in ['Open','High','Low','Close','Volume']}
 for fld,f in mats.items():f.to_pickle(B/'inputs'/f'EU_{fld}.pkl')
 if (CP/'EU_ORIGINAL_COMPACT.pkl').exists():panel=pd.read_pickle(CP/'EU_ORIGINAL_COMPACT.pkl')
 else:
  src=inspect.getsource(k.build_features).split('\n    D={}')[0]+'\n    return dates,compact_long\n'
  ns=dict(k.__dict__);exec(compile(src,'<unmodified-original-compact125-prefix>','exec'),ns)
  dates,compact=ns['build_features'](mats)
  panel=k.add_labels(compact,mats['Open'],dates)
  panel.to_pickle(CP/'EU_ORIGINAL_COMPACT.pkl')
 print('PREPARED',len(panel),'feature_rows',round(time.time()-t0,2),flush=True)
 params,rounds,seeds=recipe('RETURN_RANK_NDCG');audit=[];parts=[]
 for year in range(2019,2027):
  pth=CP/f'EU_RETURN_{year}.csv.gz'
  valid=panel[k.F2D_FEATURES].notna().sum(axis=1)>=30
  tr=panel[training_mask(panel,year)&valid].sort_values(['signal_date','ticker']).reset_index(drop=True)
  te=panel[(panel.signal_date.dt.year==year)&valid&(panel.signal_date<='2026-06-30')].sort_values(['signal_date','ticker']).reset_index(drop=True)
  singletons=tr.groupby('signal_date').ticker.transform('size')<2
  tr=tr.loc[~singletons].reset_index(drop=True)
  labels,groups,meta=prepare_targets(tr,'RETURN_RANK_NDCG')
  if pth.exists():pred=pd.read_csv(pth,parse_dates=['signal_date']);scores=pred.raw_score.to_numpy()
  else:
   xtr=native_x(tr);xt=native_x(te)
   with concurrent.futures.ThreadPoolExecutor(max_workers=3) as pool:
    scores=np.mean(list(pool.map(lambda seed:fit_seed(seed,year,xtr,xt,labels,groups,params,rounds),seeds)),axis=0)
   pred=te[['signal_date','ticker']].copy();pred['raw_score']=scores
   pred['RETURN_PCT']=pred.groupby('signal_date').raw_score.rank(pct=True,method='average')
   pred.to_csv(pth,index=False,compression='gzip')
  parts.append(pred)
  row=dict(year=year,n_train=len(tr),n_predict=len(te),last_exit=str(tr.exit_date_21.max()),train_keys_sha256=hashlib_keys(tr),model_params=params,rounds=rounds,seeds=seeds,**meta)
  audit.append(row);(OUT/'EU_FIT_AUDIT.json').write_text(json.dumps(audit,indent=2))
  pd.concat(parts).to_csv(OUT/'EU_RETURN_PREDICTIONS.csv.gz',index=False,compression='gzip')
  print('FINISHED',year,len(tr),len(te),'seconds',round(time.time()-t0,2),flush=True)
 (OUT/'EU_FEATURE_CONTRACT.json').write_text(json.dumps({'kernel_sha256':digest(k.__file__),'source_commit':'13443836649d0f107d2063eb7acc1039135d6e9b','feature_names':k.F2D_FEATURES,'feature_fill':'none; original raw source semantics','market_reference':'original source median fallback because SPY not present','mature_labels_only':True,'Hybrid':'native frozen EU annual ET/XGB, not retrained here'},indent=2))
def hashlib_keys(f):
 import hashlib
 return hashlib.sha256(f[['signal_date','ticker']].to_csv(index=False).encode()).hexdigest()
if __name__=='__main__':main()
