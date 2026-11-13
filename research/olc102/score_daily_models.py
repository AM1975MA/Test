#!/usr/bin/env python3
"""Frozen OLC08 Return + OLC11 hybrid reg + OLC14 five heads; re-predict 3 as-of dates.
Models are trained annually in original research, do not fit anything here.
Only outputs are model predictions at as-of close with frozen month eligibility/cluster.
"""
from __future__ import annotations
import os
for n in ['OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS','NUMEXPR_NUM_THREADS']:os.environ[n]='1'
import io,zipfile,time,sys,joblib,json,warnings
from pathlib import Path
import numpy as np,pandas as pd,xgboost as xgb
ROOT=Path('/mnt/data/olc102'); OUT=ROOT/'results';sys.path.insert(0,str(ROOT/'source_src'))
from etf_trader.source_only.kernel import F2D_FEATURES
from etf_trader.ma3.producer import FEATURES_42
BASE=zipfile.ZipFile('/mnt/data/olc101/original_models/OLC08_02_Riferimenti_Riprodotti_20261101.zip');
EU_RETURN=zipfile.ZipFile('/mnt/data/olc102/OLC08_03_RSI_Confronto_Verificato_20261101.zip');
HREG=zipfile.ZipFile('/mnt/data/olc101/original_models/OLC11_02_Modelli_Verificati_20261101.zip')
HEAD=zipfile.ZipFile('/mnt/data/olc101/original_models/OLC14_Heads_Checkpoint_20261101.zip')
OLC19=zipfile.ZipFile('/mnt/data/frozen_sources/OLC19_Rischio_Rientro_Checkpoint_20261102.zip');CKP='olc19_combined_risk_20261102/restore/olc18_execution_20261102/parent_archive/parent/olc16_contextual_rank_20261102/'
SEEDS=(101,211,307);HORIZONS=('C21','C42','C63');FULL_H=('C21','C42','C63','I42','I63')

def load_xgb(z,fn,tmpname):
 tmp=ROOT/f'_{tmpname}.ubj';tmp.write_bytes(z.read(fn));b=xgb.Booster();b.load_model(str(tmp));tmp.unlink();return b

def predict(m):
 st=time.time()
 comp=pd.read_pickle(OUT/f'{m}_DAILY_COMPACT.pkl');hy=pd.read_pickle(OUT/f'{m}_DAILY_HYBRID.pkl')
 assert set(comp.asof_step.unique())=={0,1,2},(m,comp.asof_step.value_counts())
 comp=comp[comp.eligible].sort_values(['event_j','asof_step','ticker']).reset_index(drop=True)
 hy=hy.sort_values(['event_j','asof_step','ticker']).reset_index(drop=True)
 # SAME original eligible support: only tickers in frozen original monthly score support at event j, shared across all steps
 ref=pd.read_csv(io.BytesIO(OLC19.read(CKP+f'results/{m}_SCORES.csv.gz')),compression='gzip',parse_dates=['signal_date'])
 mon=ref.dropna(subset=['RETURN','ORIGINAL_FUSION','TOP2_CONTEXT_REVALUE_FUSION'])[['signal_date','ticker']].drop_duplicates()
 comp=comp.merge(mon,on=['signal_date','ticker'],how='inner',validate='many_to_one')
 hy=hy.merge(mon,on=['signal_date','ticker'],how='inner',validate='many_to_one')
 kcols=['event_j','asof_step','signal_date','ticker']; comp_set=set(zip(*[comp[c].to_numpy() for c in kcols]));hy_set=set(zip(*[hy[c].to_numpy() for c in kcols]));print('SUPPORT',m,len(comp),len(hy),'intersection',len(comp_set&hy_set),'difference',len(comp_set^hy_set),flush=True)
 # Need original month same support for every step; failure indicates market quote data new, refuse rather than silently change.
 if comp_set!=hy_set:raise ValueError('Return/Hybrid support differs for daily model rows')
 for j,g in comp.groupby('event_j'):
  groups=g.groupby('asof_step');sz=groups.size()
  if len(sz)!=3:
   assert j==89 and len(sz)==2, (m,j,'missing ticker step data',sz)
   continue
  if sz.nunique()!=1: raise ValueError((m,j,'step support mismatch',sz))
 out=comp[kcols+['asof_date']].copy()
 out['year']=out.signal_date.dt.year
 for field in ('RETURN_RAW','RETURN'):
  out[field]=np.nan
 for name in ['ET_REG_RAW','XGB_REG_RAW']+ [h+'_'+fam for h in HORIZONS for fam in ['ET','XGB']]:out[name]=np.nan
 for year,g in comp.groupby(comp.signal_date.dt.year):
  mask=comp.signal_date.dt.year.eq(year).to_numpy();index=np.flatnonzero(mask)
  xp=np.asarray(comp.loc[mask,list(F2D_FEATURES)].to_numpy(float),dtype=float);xp[~np.isfinite(xp)]=np.nan
  # per month-step cross sectional percentile on the same frozen eligible candidates
  return_preds=[]
  for seed in [101,202,303]:
   modelzip=(EU_RETURN if m=='EU' else BASE)
   modelpath=(f'fits/EU/R_RSI_DOMAIN/{year}/RETURN_{seed}.ubj' if m=='EU' else f'fits/{m}/BASE/{year}/RETURN_{seed}.ubj')
   booster=load_xgb(modelzip,modelpath,f'{m}_{year}_return_{seed}')
   return_preds.append(booster.predict(xgb.DMatrix(xp)))
  out.loc[index,'RETURN_RAW']=np.mean(return_preds,axis=0)
  hbase=hy.loc[hy.signal_date.dt.year.eq(year)].copy(); assert hbase[kcols].equals(g[kcols]),(m,year,'order')
  raw=hbase[list(FEATURES_42)].to_numpy(float)
  hreg_preds={fam:[] for fam in ['ET','XGB']};head_preds={h+'_'+fam:[] for h in HORIZONS for fam in ['ET','XGB']}
  for seed in SEEDS:
   pre=f'models/{m}/{year}/{seed}/';himp=joblib.load(io.BytesIO(HREG.read(pre+'IMPUTER.joblib')));hx=himp.transform(raw)
   et=joblib.load(io.BytesIO(HREG.read(pre+'ET_REG.joblib')));hreg_preds['ET'].append(et.predict(hx))
   xb=load_xgb(HREG,pre+'XGB_REG.ubj',f'{m}_{year}_{seed}_xgreg')
   hreg_preds['XGB'].append(xb.predict(xgb.DMatrix(hx)))
   pre2=f'olc14_fitted_ranking_20261101/models/{m}/{year}/{seed}/';imp=joblib.load(io.BytesIO(HEAD.read(pre2+'IMPUTER.joblib')));hxp=imp.transform(raw)
   for h in HORIZONS:
    et=joblib.load(io.BytesIO(HEAD.read(pre2+h+'_ET.joblib')))
    head_preds[h+'_ET'].append(et.predict(hxp))
    xb=load_xgb(HEAD,pre2+h+'_XGB.ubj',f'{m}_{year}_{seed}_{h}_xgb')
    head_preds[h+'_XGB'].append(xb.predict(xgb.DMatrix(hxp)))
  for fam in ('ET','XGB'):out.loc[index,fam+'_REG_RAW']=np.mean(hreg_preds[fam],axis=0)
  for n,v in head_preds.items():out.loc[index,n]=np.mean(v,axis=0)
  print('YEAR',m,year,'rows',len(index),'sec',round(time.time()-st,2),flush=True)
 # ranking is within each event *and* step, never across separate decision dates
 fields=['RETURN_RAW','ET_REG_RAW','XGB_REG_RAW']+[h+'_'+fam for h in HORIZONS for fam in ['ET','XGB']]
 for n in fields:out[n.replace('_RAW','')+'_RANK']=out.groupby(['event_j','asof_step'])[n].rank(pct=True,method='average')
 # NOTE : RETURN score is pct on same eligible support; original prior scores within month may have other support.
 out['RETURN']=out.RETURN_RANK
 out['ORIGINAL_P15']=.60*out.ET_REG_RANK+.40*out.XGB_REG_RANK
 for h in HORIZONS:out[h]=.60*out[h+'_ET_RANK']+.40*out[h+'_XGB_RANK']
 out['CUM_FIXED_MAPPED']=.45*out.C21+.35*out.C42+.20*out.C63
 # Compare original historical monthly reference on R0 only, all 90 months.
 ref0=out[out.asof_step.eq(0)].merge(ref,on=['signal_date','ticker'],suffixes=('','_REF'),validate='one_to_one')
 cmp=[]
 for name in ['RETURN','ORIGINAL_P15','C21','C42','C63']:
  tgt=name+'_REF';
  if tgt not in ref0.columns:continue
  val=ref0[name].to_numpy(float);o=ref0[tgt].to_numpy(float)
  good=np.isfinite(val)&np.isfinite(o);mx=float(np.max(abs(val[good]-o[good]))) if good.any() else None
  month_agree=sum(g.sort_values([name,'ticker'],ascending=[False,True]).ticker.tolist()==g.sort_values([tgt,'ticker'],ascending=[False,True]).ticker.tolist() for _,g in ref0.groupby('signal_date'))
  cmp.append(dict(field=name,matched=int(good.sum()),max_abs_error=mx,months_whole_rank_equal=int(month_agree)))
 qa={'market':m,'rows':len(out),'n_events':90,'compare':cmp,'computed_from_frozen_models':True,'no_fit':True,'at_event_asof_closes':3,'elapsed_s':time.time()-st}
 (OUT/f'{m}_DAILY_SCORE_QA.json').write_text(json.dumps(qa,indent=2))
 out.to_pickle(OUT/f'{m}_DAILY_ML_SCORES.pkl')
 print('FINISHED',json.dumps(qa),flush=True)
 return qa

if __name__=='__main__':
 import argparse;a=argparse.ArgumentParser();a.add_argument('market',choices=['EU','USA']);p=a.parse_args();predict(p.market)
