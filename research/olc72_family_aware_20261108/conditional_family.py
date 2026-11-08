#!/usr/bin/env python3
"""OLC72 matching-based approximate conditional native-family perturbation (both markets)."""
import os
for k in ('OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS'):os.environ[k]='1'
import io,hashlib,json,time,warnings
import numpy as np,pandas as pd,xgboost as xgb
from pathlib import Path
import run_olc72 as core
ROOT=Path(__file__).resolve().parent;OUT=ROOT/'results'
FAMILIES=('mom5','acc_mom_5_21','acc_mom_21_63','vol21','vol63','beta_mkt126')
SEEDS=(72001,72002)

def rank_group(v,dates):
 return pd.DataFrame({'d':dates,'v':v}).groupby('d').v.rank(pct=True).to_numpy()

def top2(a,tickers,ret21,ret42,month_ix):
 result={}
 for month,indices in month_ix.items():
  ix=np.asarray(indices,dtype=int); ix=ix[np.isfinite(a[ix])]
  ix=ix[np.lexsort((tickers[ix],-a[ix]))[:2]]
  result[month]={'top2':';'.join(tickers[ix]),
     'p21':float(np.mean(ret21[ix])) if np.isfinite(ret21[ix]).all() else np.nan,
     'p42':float(np.mean(ret42[ix])) if np.isfinite(ret42[ix]).all() else np.nan}
 return result

def donor_indices(raw,mask,seed,m,yr,family,date):
 # Same-date 45-dimensional raw-feature similarity, independent of future labels.
 a=np.asarray(raw[:,mask],dtype=float);n=len(a)
 if n<7: raise AssertionError(('few candidates',m,yr,date))
 # Missing rank is neutral FOR DONOR MATCHING ONLY, never modifies model inputs.
 ranks=pd.DataFrame(a).rank(pct=True,na_option='keep').fillna(.5).to_numpy()
 # Max matrix ~165x165x45, manageable.
 ss=np.sum(ranks*ranks,axis=1)
 D=np.maximum(ss[:,None]+ss[None,:]-2*ranks@ranks.T,0)
 np.fill_diagonal(D,np.inf)
 near=np.argpartition(D,kth=4,axis=1)[:,:5]
 # sort candidates to avoid argpartition order non-determinism
 near=np.take_along_axis(near,np.argsort(np.take_along_axis(D,near,axis=1),axis=1,kind='mergesort'),axis=1)
 msg=f'{m}|{yr}|{family}|{date}|{seed}'.encode();rng=np.random.default_rng(int(hashlib.sha256(msg).hexdigest()[:16],16))
 select=near[np.arange(n),rng.integers(0,5,size=n)]
 assert (select!=np.arange(n)).all()
 return select

def main():
 tic=time.time();z=core.init();rows=[];parity=[]
 for m in ['EU','USA']:
  cp=pd.read_pickle(io.BytesIO(z['OLC08F_01_FeaturePack_20261101.zip'].read(f'inputs/{m}_RSI_COMPACT.pkl')))
  orig=pd.read_csv(io.BytesIO(z['OLC19_Rischio_Rientro_Checkpoint_20261102.zip'].read(core.PRE+f'{m}_MEAN3_SCORES.csv.gz')),compression='gzip',parse_dates=['signal_date'],float_precision='round_trip')
  for year in range(2021,2026):
   start=time.time();tr,te,y,groups=core.train_test(cp,year)
   col=core.audit(z,m,year)['return_features'];assert len(col)==125
   families={}
   for i,k in enumerate(col):families.setdefault(k.removesuffix('_pct').removesuffix('_dev'),[]).append(i)
   assert len(families)==46
   X=te[col].to_numpy(float);X[~np.isfinite(X)]=np.nan;dates=te.signal_date.dt.strftime('%Y-%m-%d').to_numpy(str)
   datesgrp={d:np.flatnonzero(dates==d) for d in np.unique(dates)};names=te.ticker.astype(str).to_numpy()
   original_models=[core.orig_model(z,m,year,s) for s in core.SEEDS]
   rp=np.mean([b.predict(xgb.DMatrix(X,nthread=1)) for b in original_models],axis=0)
   rank=rank_group(rp,dates)
   q=te[['signal_date','ticker']].merge(orig[['signal_date','ticker','RETURN','ORIGINAL_SMOOTH','ORIGINAL_FUSION']],on=['signal_date','ticker'],validate='one_to_one',sort=False)
   assert np.max(abs(q.RETURN.to_numpy()-rank))<1e-13
   sm=q.ORIGINAL_SMOOTH.to_numpy(float);original_fusion=.475*rank+.525*sm
   assert np.nanmax(abs(original_fusion-q.ORIGINAL_FUSION.to_numpy(float)))<1e-12
   ret21=te.fwd_ret_21.to_numpy(float);ret42=te.fwd_ret_42.to_numpy(float)
   baseline=top2(original_fusion,names,ret21,ret42,datesgrp)
   raw_ind={k:col.index(k) for k in families}
   for fam in FAMILIES:
    cols=np.array(families[fam],dtype=int)
    remain=[raw_ind[k] for k in families if k!=fam]
    base_raw=X[:,remain]
    for rep in SEEDS:
     modified=X.copy()
     for date,ix in datesgrp.items():
      donor=donor_indices(base_raw[ix],list(range(len(remain))),rep,m,year,fam,date)
      modified[np.ix_(ix,cols)]=X[np.ix_(ix[donor],cols)]
     curr=np.mean([b.predict(xgb.DMatrix(modified,nthread=1)) for b in original_models],axis=0)
     fused=.475*rank_group(curr,dates)+.525*sm
     selected=top2(fused,names,ret21,ret42,datesgrp)
     for date in datesgrp:
      b=baseline[date];c=selected[date]
      rows.append({'market':m,'year':year,'month':date[:7],'family':fam,'rep_seed':rep,
                   'native_top2':b['top2'],'conditional_top2':c['top2'],'changed':int(b['top2']!=c['top2']),
                   'native21':b['p21'],'matched21':c['p21'],'native42':b['p42'],'matched42':c['p42'],
                   'original_minus_matched21_pp':100*(b['p21']-c['p21']) if np.isfinite(b['p21']+c['p21']) else np.nan,
                   'original_minus_matched42_pp':100*(b['p42']-c['p42']) if np.isfinite(b['p42']+c['p42']) else np.nan})
   parity.append({'market':m,'year':year,'n_months':len(datesgrp),'n_tickers':len(te),'max_parity_error':np.max(abs(q.RETURN.to_numpy()-rank))})
   print('CONDITIONAL',m,year,'months',len(datesgrp),'seconds',round(time.time()-start,1),flush=True)
 d=pd.DataFrame(rows);d.to_csv(OUT/'OLC72_CONDITIONAL_FAMILY_MONTHLY.csv',index=False)
 summary=[]
 for (m,period,fam),grp in d.assign(period=np.where(d.year<=2024,'MAIN_2021_2024','LATE_2025')).groupby(['market','period','family']):
  summary.append({'market':m,'period':period,'family':fam,'n_perturbations':len(grp),
    'changed_rate':grp.changed.mean(),'original_minus_matched21_pp':grp.original_minus_matched21_pp.mean(),
    'original_minus_matched42_pp':grp.original_minus_matched42_pp.mean(),
    'metric':'approx_conditional_k5_raw_peer_match_two_seeds'})
 pd.DataFrame(summary).to_csv(OUT/'OLC72_CONDITIONAL_FAMILY_SUMMARY.csv',index=False)
 (OUT/'OLC72_CONDITIONAL_QA.json').write_text(json.dumps({'original_native_EU_USA_parity':True,'matched_family_block':True,
  'families':list(FAMILIES),'seeds':list(SEEDS),'months':sum(a['n_months'] for a in parity),'rows':len(d),
  'method':'donor from 5 closest same-date peers on other 45 raw family ranks, no future label in matching',
  'warning':'Approximate conditional perturbation, not causal importance; donor swaps still may be off-manifold; families exploratory based on prior OLC71 EU.',
  'parity':parity,'elapsed_seconds':time.time()-tic},indent=2))
 print('CONDITIONAL_DONE',len(d),flush=True)
if __name__=='__main__':
 with warnings.catch_warnings():warnings.simplefilter('ignore',RuntimeWarning);main()