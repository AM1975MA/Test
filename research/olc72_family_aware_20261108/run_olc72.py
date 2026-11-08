#!/usr/bin/env python3
"""OLC72: causal native Return125 XGB with equal 46-family column-sampling mass."""
import os
for k in ('OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS'):os.environ[k]='1'
from pathlib import Path
from zipfile import ZipFile
import io,json,hashlib,time,warnings
import pandas as pd,numpy as np,xgboost as xgb

ROOT=Path(__file__).parent; OUT=ROOT/'results';OUT.mkdir(exist_ok=True);SRC=Path('/mnt/data/etf_source')
SOURCES={'OLC08F_01_FeaturePack_20261101.zip':'420faa56547721fd58db9f75ceef1370483047073d91c1b675587bd2d2e9db6c',
'OLC08_03_RSI_Confronto_Verificato_20261101.zip':'0dbcb8ee93cd0acaefd7505a202fbf30c9fda8df1804d90a0dd1578abd704f4b',
'OLC08F_Checkpoint_Completo_Volume1_20261101.zip':'e2a188488251a1db2c5d6db8c7188f95ca4ec6a9a5487aec45cb183017ac0aaf',
'OLC08F_Checkpoint_Completo_Volume2_20261101.zip':'7afbd101606330179fcc558ffd645c9744ac17451f3c0b631319267d8c193efa',
'OLC19_Rischio_Rientro_Checkpoint_20261102.zip':'3b5799dae060c104408f581c70280cef8ce4d84c3978434d4e6ba81108f16540'}
PARAMS=dict(objective='rank:ndcg',ndcg_exp_gain=False,lambdarank_pair_method='topk',lambdarank_num_pair_per_sample=5,eval_metric='ndcg@5',max_depth=4,learning_rate=.035,subsample=.85,colsample_bytree=.8,min_child_weight=8,reg_lambda=8,reg_alpha=.1,tree_method='hist',nthread=1)
PRE='olc19_combined_risk_20261102/restore/olc18_execution_20261102/parent_archive/parent/olc16_contextual_rank_20261102/inputs/'
SEEDS=(101,202,303)
def get(zs,key):
 for z in zs:
  try:return z.read(key)
  except KeyError:pass
 raise KeyError(key)
def sha(a):
 a=np.ascontiguousarray(a);return hashlib.sha256(str(a.dtype).encode()+str(a.shape).encode()+a.tobytes()).hexdigest()
def init():
 for n,h in SOURCES.items():
  digest=hashlib.file_digest(open(SRC/n,'rb'),'sha256').hexdigest(); assert digest==h,(n,digest)
 return {n:ZipFile(SRC/n) for n in SOURCES}
def orig_model(z,market,year,seed):
 if market=='EU': b=z['OLC08_03_RSI_Confronto_Verificato_20261101.zip'].read(f'fits/EU/R_RSI_DOMAIN/{year}/RETURN_{seed}.ubj')
 else:b=get((z['OLC08F_Checkpoint_Completo_Volume1_20261101.zip'],z['OLC08F_Checkpoint_Completo_Volume2_20261101.zip']),f'parents/fits/USA/BASE/{year}/RETURN_{seed}.ubj')
 return xgb.Booster(model_file=bytearray(b))
def audit(z,m,y):
 if m=='EU':return json.loads(z['OLC08_03_RSI_Confronto_Verificato_20261101.zip'].read(f'fits/EU/R_RSI_DOMAIN/{y}/audit.json'))
 return json.loads(get((z['OLC08F_Checkpoint_Completo_Volume1_20261101.zip'],z['OLC08F_Checkpoint_Completo_Volume2_20261101.zip']),f'parents/fits/USA/BASE/{y}/audit.json'))
def train_test(cp,year):
 cutoff=pd.Timestamp(year,1,1);end=pd.Timestamp(year+1,1,1)
 tr=cp.loc[cp.signal_date.lt(cutoff)&cp.exit_date_21.lt(cutoff)&cp.fwd_ret_21.notna()&cp.eligible].sort_values(['signal_date','ticker'])
 tr=tr.loc[tr.groupby('signal_date').ticker.transform('size').ge(2)].copy()
 te=cp.loc[cp.signal_date.ge(cutoff)&cp.signal_date.lt(end)&cp.eligible].sort_values(['signal_date','ticker']).copy()
 g=tr.groupby('signal_date').fwd_ret_21
 med=g.transform('median');spread=np.maximum(g.transform(lambda x:x.quantile(.9))-g.transform(lambda x:x.quantile(.1)),1e-6)
 label=np.rint(7.5+7.5*np.clip((tr.fwd_ret_21-med)/spread,-1,1)).to_numpy(np.int32)
 groups=tr.groupby('signal_date',sort=False).size().to_numpy()
 assert tr.exit_date_21.max()<cutoff and tr.source_date.le(tr.signal_date).all() and te.source_date.le(te.signal_date).all()
 return tr,te,label,groups

def evaluate(df,market):
 result=[]
 for dt,sub in df.groupby('signal_date',sort=True):
  for method in ['ORIGINAL_FUSION','FAMILY_FUSION']:
   ch=sub.sort_values([method,'ticker'],ascending=[False,True],kind='mergesort').head(2)
   p21,p42=ch.fwd_ret_21.mean(),ch.fwd_ret_42.mean()
   cut21=sub.fwd_ret_21.quantile(.8);cut42=sub.fwd_ret_42.quantile(.8)
   result.append({'market':market,'month':dt.strftime('%Y-%m'),'year':dt.year,'method':method,'top2':';'.join(ch.ticker.astype(str)),
    'p21':p21,'p42':p42,'persistent':float(((ch.fwd_ret_21>=cut21)&(ch.fwd_ret_42>=cut42)).mean()),
    'top20_21':float((ch.fwd_ret_21>=cut21).mean()),'negative21':float((ch.fwd_ret_21<0).mean())})
 return result

def main():
 start=time.time();z=init();aud=[];predictions=[];months=[]
 for m in ['EU','USA']:
  cp=pd.read_pickle(io.BytesIO(z['OLC08F_01_FeaturePack_20261101.zip'].read(f'inputs/{m}_RSI_COMPACT.pkl')))
  orig=pd.read_csv(io.BytesIO(z['OLC19_Rischio_Rientro_Checkpoint_20261102.zip'].read(PRE+f'{m}_MEAN3_SCORES.csv.gz')),compression='gzip',parse_dates=['signal_date'],float_precision='round_trip')
  for year in range(2021,2026):
   t0=time.time();tr,te,label,groups=train_test(cp,year);a=audit(z,m,year);feat=a['return_features'];assert len(feat)==125
   X=tr[feat].to_numpy(float);XP=te[feat].to_numpy(float);X[~np.isfinite(X)]=np.nan;XP[~np.isfinite(XP)]=np.nan
   if m=='EU':
    for val in (X,XP,label,groups): assert sha(val) in a['return_matrices'],(m,year,'input hash')
   # B0: reuse original, not a new fit. Validate every date of both original market ensembles.
   originalraw=np.mean([orig_model(z,m,year,s).predict(xgb.DMatrix(XP,nthread=1)) for s in SEEDS],axis=0)
   q=te[['signal_date','ticker','fwd_ret_21','fwd_ret_42']].copy().reset_index(drop=True)
   q['RETURN_REBUILT']=pd.DataFrame({'d':q.signal_date,'raw':originalraw}).groupby('d').raw.rank(pct=True).to_numpy()
   q=q.merge(orig[['signal_date','ticker','RETURN','ORIGINAL_SMOOTH','ORIGINAL_FUSION']],on=['signal_date','ticker'],validate='one_to_one',sort=False)
   assert q.RETURN.notna().all() and q.ORIGINAL_FUSION.notna().sum()>100
   assert q.ORIGINAL_FUSION.isna().equals(q.ORIGINAL_SMOOTH.isna())
   err=float(np.max(abs(q.RETURN_REBUILT-q.RETURN)));ferr=float(np.nanmax(abs(.475*q.RETURN_REBUILT+.525*q.ORIGINAL_SMOOTH-q.ORIGINAL_FUSION)))
   assert err<1e-13 and ferr<1e-12,(m,year,err,ferr)
   families={}
   for ix,name in enumerate(feat):families.setdefault(name.removesuffix('_pct').removesuffix('_dev'),[]).append(ix)
   assert len(families)==46
   fw=np.zeros(125,dtype=np.float64)
   for indices in families.values():fw[indices]=1.0/len(indices)
   assert np.allclose([fw[ix].sum() for ix in families.values()],1)
   dt=xgb.QuantileDMatrix(X,label=label,feature_weights=fw,nthread=1);dt.set_group(groups)
   dp=xgb.QuantileDMatrix(XP,ref=dt,nthread=1)
   raw=[];fit_times=[]
   for seed in SEEDS:
    ts=time.time();bs=xgb.train({**PARAMS,'seed':seed},dt,num_boost_round=360,verbose_eval=False)
    d=ROOT/'models'/m/str(year);d.mkdir(parents=True,exist_ok=True);bs.save_model(d/f'FAMILY_{seed}.ubj')
    raw.append(bs.predict(dp));fit_times.append(round(time.time()-ts,1))
   q['FAMILY_RAW']=np.mean(raw,axis=0)
   q['FAMILY_RETURN']=q.groupby('signal_date').FAMILY_RAW.rank(pct=True)
   q['FAMILY_FUSION']=.475*q.FAMILY_RETURN+.525*q.ORIGINAL_SMOOTH
   q.insert(0,'market',m);predictions.append(q)
   months+=evaluate(q,m)
   aud.append({'market':m,'year':year,'n_train':len(tr),'n_predict':len(te),'n_families':len(families),'rank_parity_max_abs':err,
    'fusion_parity_max_abs':ferr,'max_train_exit':str(tr.exit_date_21.max().date()),'fit_times':fit_times,'elapsed':round(time.time()-t0,1)})
   (OUT/'OLC72_AUDIT.json').write_text(json.dumps(aud,indent=2))
   print('FITTED',m,year,'ntrain',len(tr),'npred',len(te),'baseline_parity',err,'seconds',round(time.time()-t0,1),flush=True)
  print('MARKET_COMPLETE',m,flush=True)
 p=pd.concat(predictions,ignore_index=True);p.to_csv(OUT/'OLC72_PREDICTIONS.csv.gz',compression='gzip',index=False)
 mo=pd.DataFrame(months);mo.to_csv(OUT/'OLC72_MONTHLY.csv',index=False)
 out=[]
 for (m,period,method),d in mo.assign(period=np.where(mo.year<=2024,'MAIN_2021_2024','LATE_2025')).groupby(['market','period','method']):
  out.append({'market':m,'period':period,'method':method,'months':len(d),'p21_pct':d.p21.mean()*100,'p42_pct':d.p42.mean()*100,
   'persistent_rate':d.persistent.mean(),'top20_21':d.top20_21.mean(),'negative21':d.negative21.mean()})
 pd.DataFrame(out).to_csv(OUT/'OLC72_SUMMARY.csv',index=False)
 paired=[];rng=np.random.default_rng(72001)
 for m in ['EU','USA']:
  d=mo[(mo.market==m)&mo.year.between(2021,2024)];piv=d.pivot(index='month',columns='method',values=['p21','p42','persistent'])
  assert len(piv)==48
  for col in ['p21','p42','persistent']:
   arr=(piv[(col,'FAMILY_FUSION')]-piv[(col,'ORIGINAL_FUSION')]).to_numpy();assert np.isfinite(arr).all()
   boot=[]
   for _ in range(4000):
    ix=((rng.integers(0,48,8)[:,None]+np.arange(6))%48).ravel()
    boot.append(arr[ix].mean())
   k=100 if col in ('p21','p42') else 1
   paired.append({'market':m,'metric':col,'delta':float(np.mean(arr)*k),'lower':float(np.quantile(boot,.025)*k),'upper':float(np.quantile(boot,.975)*k),'units':'pp' if k==100 else 'fraction'})
 pd.DataFrame(paired).to_csv(OUT/'OLC72_BOOTSTRAP.csv',index=False)
 qa={'n_predictions':len(p),'n_market_months':len(mo)//2,'n_new_boosters':len(aud)*3,'original_rank_parity_EU_USA':True,
 'n_families':46,'original_125_features_unchanged':True,'main_2021_2024':True,'source_hashes':SOURCES,'param_recipe':PARAMS,
 'elapsed_seconds':time.time()-start,'research_only':True}
 (OUT/'OLC72_QA.json').write_text(json.dumps(qa,indent=2));print('DONE',json.dumps(qa),flush=True)
if __name__=='__main__':
 with warnings.catch_warnings():warnings.simplefilter('ignore',RuntimeWarning);main()