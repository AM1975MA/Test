"""Fresh annual original Return and Hybrid model families on CL01 source panels."""
import os
for key in ['OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS']:os.environ[key]='1'
from pathlib import Path
import sys,json,time,hashlib
import numpy as np,pandas as pd
ROOT=Path(__file__).resolve().parents[1];OLD=ROOT/'legacy';SRC=OLD/'source/research/tail-only-and-allocation-ablation-20261017'
sys.path[:0]=[str(SRC),str(SRC/'vendor/etf_trader_v2/src')]
from etf_trader.source_only import kernel as k
from etf_trader.ma3.hybrid_producer import ET_MODEL_KW,XGB_MODEL_KW,FEATURES_42,corrected_target
from compact21_return_v1.core import recipe,prepare_targets,native_x
from sklearn.ensemble import ExtraTreesRegressor
from sklearn.impute import SimpleImputer
import xgboost as xgb
OUT=ROOT/'results/calendar';(OUT/'models').mkdir(parents=True,exist_ok=True)
def digest_frame(f):return hashlib.sha256(f[['signal_date','ticker']].to_csv(index=False).encode()).hexdigest()
def fit(market):
 start=time.time();cp=pd.read_pickle(OUT/f'{market}_COMPACT.pkl');hp=pd.read_pickle(OUT/f'{market}_HYBRID.pkl');hp['TARGET']=corrected_target(hp)
 params,rounds,seeds=recipe('RETURN_RANK_NDCG');rows=[];audit=[]
 for year in range(2019,2027):
  cutoff=pd.Timestamp(year,1,1);end=pd.Timestamp(year+1,1,1)
  tr=cp[(cp.signal_date<cutoff)&(cp.exit_date_21<cutoff)&cp.fwd_ret_21.notna()&cp.eligible].sort_values(['signal_date','ticker'])
  tr=tr[tr.groupby('signal_date').ticker.transform('size')>=2].copy()
  pr=cp[(cp.signal_date>=cutoff)&(cp.signal_date<end)&cp.eligible].sort_values(['signal_date','ticker']).copy()
  labels,groups,meta=prepare_targets(tr,'RETURN_RANK_NDCG');X=native_x(tr);XP=native_x(pr)
  d=xgb.QuantileDMatrix(X,label=labels,nthread=1);d.set_group(groups);test=xgb.QuantileDMatrix(XP,ref=d,nthread=1);preds=[]
  for seed in seeds:
   model=xgb.train(dict(params,nthread=1,seed=seed),d,num_boost_round=rounds,verbose_eval=False)
   model.save_model(OUT/'models'/f'{market}_{year}_RETURN_{seed}.ubj');preds.append(model.predict(test))
  p=pr[['signal_date','ticker','source_date']].copy();p['RETURN_RAW']=np.mean(preds,axis=0);p['RETURN']=p.groupby('signal_date').RETURN_RAW.rank(pct=True)
  audit.append({'market':market,'year':year,'model':'RETURN','n_train':len(tr),'n_predict':len(pr),'max_signal':str(tr.signal_date.max().date()),'max_exit':str(tr.exit_date_21.max().date()),'cutoff':str(cutoff.date()),'training_keys_sha256':digest_frame(tr),'seeds':seeds,'rounds':rounds})
  ht=hp[(hp.signal_date<cutoff)&(hp.exit_date_63<cutoff)&hp.TARGET.notna()].sort_values(['signal_date','ticker'])
  pp=hp[(hp.signal_date>=cutoff)&(hp.signal_date<end)].sort_values(['signal_date','ticker']).copy()
  assert len(ht)>0 and ht.exit_date_63.max()<cutoff and tr.exit_date_21.max()<cutoff
  imp=SimpleImputer(strategy='median',keep_empty_features=True);HX=imp.fit_transform(ht[list(FEATURES_42)]);HXP=imp.transform(pp[list(FEATURES_42)])
  hy=ht.TARGET.to_numpy(float)
  et=ExtraTreesRegressor(n_jobs=1,**ET_MODEL_KW);et.fit(HX,hy)
  gb=xgb.XGBRegressor(n_jobs=1,**XGB_MODEL_KW);gb.fit(HX,hy)
  # Pickles are generated internally, versioned with hashes; never load unknown external pickles.
  import joblib
  joblib.dump({'imputer':imp,'model':et},OUT/'models'/f'{market}_{year}_ET.joblib',compress=3)
  joblib.dump(imp,OUT/'models'/f'{market}_{year}_IMPUTER.joblib',compress=3);gb.save_model(OUT/'models'/f'{market}_{year}_HYBRID_XGB.ubj')
  pp['ET_RAW']=et.predict(HXP);pp['XGB_RAW']=gb.predict(HXP)
  pp['ET']=pp.groupby('signal_date').ET_RAW.rank(pct=True);pp['XGB']=pp.groupby('signal_date').XGB_RAW.rank(pct=True)
  audit.append({'market':market,'year':year,'model':'HYBRID_ET_XGB','n_train':len(ht),'n_predict':len(pp),'max_signal':str(ht.signal_date.max().date()),'max_exit':str(ht.exit_date_63.max().date()),'cutoff':str(cutoff.date()),'training_keys_sha256':digest_frame(ht)})
  p=p.merge(pp[['signal_date','ticker','ET','XGB','ET_RAW','XGB_RAW']],on=['signal_date','ticker'],how='outer',validate='one_to_one');rows.append(p)
  pd.concat(rows).to_csv(OUT/f'{market}_FORECASTS.csv.gz',index=False,compression='gzip');(OUT/f'{market}_FIT_AUDIT.json').write_text(json.dumps(audit,indent=2))
  print('FIT_DONE',market,year,len(tr),len(ht),len(p),'elapsed',round(time.time()-start),flush=True)
 (OUT/f'{market}_FIT_COMPLETE.json').write_text(json.dumps({'market':market,'years':8,'return_models':24,'hybrid_ET_models':8,'hybrid_XGB_models':8,'elapsed':time.time()-start},indent=2));print('COMPLETE',market,flush=True)
if __name__=='__main__':fit(sys.argv[1])
