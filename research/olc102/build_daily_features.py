#!/usr/bin/env python3
"""OLC102: three AS-OF feature snapshots per frozen OLC19 monthly signal.
Uses original (OLC07 P0) compact and hybrid source code, original raw OHLCV,
and monthly cluster membership held fixed for the following two closes.
Never uses price/volume later than each as-of close in feature calculations.
"""
from __future__ import annotations
import os
for n in ['OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS','NUMEXPR_NUM_THREADS']: os.environ[n]='1'
import io,zipfile,json,sys,time,hashlib,warnings
from pathlib import Path
import numpy as np,pandas as pd
ROOT=Path('/mnt/data/olc102'); OUT=ROOT/'results';OUT.mkdir(parents=True,exist_ok=True)
SRC=ROOT/'source_src'; sys.path.insert(0,str(SRC));
from etf_trader.source_only import kernel as k
from etf_trader.ma3.producer import FEATURES_42
ZIP=zipfile.ZipFile('/mnt/data/olc101/original_models/EU_Original39_RH50_Checkpoint_20261031.zip')
CAL=zipfile.ZipFile('/mnt/data/olc101/original_models/OLC08_01_Pannelli_Verificati_20261101.zip')
CK=zipfile.ZipFile('/mnt/data/frozen_sources/OLC19_Rischio_Rientro_Checkpoint_20261102.zip')
SRC_PREF='eu_original_retest_20261031/'
CAL_PREF='parents/olc07_calendar_20261101/phases/P0/results/calendar/'
CK_PREF='olc19_combined_risk_20261102/restore/olc18_execution_20261102/'

# Source text is frozen, stored unchanged and checksummed with the test.
COMPACT_SRC=CAL.read(CAL_PREF+'COMPACT_SOURCE.py').decode();HYBRID_SRC=CAL.read(CAL_PREF+'HYBRID_RAW_SOURCE.py').decode()

def load_q(m):
 with np.load(io.BytesIO(CK.read(CK_PREF+f'inputs/{m}_TOP2_CONTEXT_REVALUE.npz')),allow_pickle=False) as a:q={f:a[f].copy() for f in a.files}
 dec=pd.read_csv(io.BytesIO(CK.read(CK_PREF+f'inputs/{m}_TOP2_CONTEXT_REVALUE_DECISIONS.csv')),parse_dates=['signal_date','entry_date'])
 score=pd.read_csv(io.BytesIO(CK.read(CK_PREF+f'parent_archive/parent/olc16_contextual_rank_20261102/results/{m}_SCORES.csv.gz')),compression='gzip',parse_dates=['signal_date'])
 return q,dec,score

def load_raw(m):
 if m=='EU':
  pref=SRC_PREF+'inputs/eu/source_v4/input/EU165_SPECIALISTS_20261029/'
  u=pd.read_csv(io.BytesIO(ZIP.read(pref+'input/universe.csv'))); prices=pref+'prices/'
 else:
  pref=SRC_PREF+'raw/_repeat1/'
  u=pd.read_csv(io.BytesIO(ZIP.read(pref+'universe.csv')));prices=pref
 frames={}
 for t in u.ticker.astype(str):
  f=pd.read_csv(io.BytesIO(ZIP.read(prices+t+'.csv')),index_col=0,parse_dates=True,float_precision='round_trip').sort_index().loc[:'2026-07-01']
  good=np.isfinite(f[['Open','High','Low','Close']]).all(axis=1)&(f[['Open','High','Low','Close']]>0).all(axis=1)
  frames[t]=f.loc[good,['Open','High','Low','Close','Volume']]
 return frames,u

def rebuild(m):
 ts=time.time();q,dec,score=load_q(m);frames,u=load_raw(m)
 names=list(frames);C=pd.DataFrame({t:f.Close for t,f in frames.items()}).sort_index();master=C.index
 if m=='USA':benchmark=C['SPY'].dropna()
 else:benchmark=(1+C.ffill(limit=3).pct_change(fill_method=None).median(axis=1).fillna(0)).cumprod()
 # Dates must be observed by the market; first new decision is entry open k+1, then k+2.
 ev=np.flatnonzero(q['events']); assert len(dec)==len(ev)==90
 selected=[]
 for j,evt_k in enumerate(ev):
  d0=pd.Timestamp(dec.loc[j,'signal_date']);t0=pd.Timestamp(q['dates'][evt_k]);
  assert d0<t0, ('invalid t0 cutoff',m,j,d0,t0)
  for step,dt in [(0,d0),(1,pd.Timestamp(q['dates'][evt_k])),(2,pd.Timestamp(q['dates'][evt_k+1]) if evt_k+1<len(q['dates']) else pd.NaT)]:
   if pd.notna(dt):selected.append({'event_j':j,'asof_step':step,'asof_date':dt,'signal_date':d0,'entry_date':t0})
 eventmap=pd.DataFrame(selected)
 # Only features whose date is in OLC19 (no end-of-last-file edge).
 query_dates=pd.DatetimeIndex(sorted(set(eventmap.asof_date)))
 ns=dict(k.__dict__,BENCHMARK=benchmark)
 ns['month_end_dates']=lambda idx: query_dates.intersection(idx)
 exec(compile(COMPACT_SRC,'<frozen-compact>','exec'),ns)
 compact_func=ns['build_features']
 hns={'pd':pd,'np':np};exec(compile(HYBRID_SRC,'<frozen-hybrid>','exec'),hns);hybrid_func=hns['hybrid_raw']
 comparts=[];hyparts=[]
 with warnings.catch_warnings():
  warnings.simplefilter('ignore')
  for i,(t,f) in enumerate(frames.items()):
   mats={fld:f[[fld]].rename(columns={fld:t}) for fld in ['Open','High','Low','Close','Volume']}
   # Full native observed dates are needed for as-of the next 1/2 market closes.
   localpos=f.index.searchsorted(query_dates,side='right')-1
   valid=localpos>=0;safe=np.maximum(localpos,0);srcdates=pd.DatetimeIndex(f.index[safe]);fresh=valid&((query_dates-srcdates).days<=5)
   ns['month_end_dates']=lambda idx: srcdates.unique().intersection(idx)
   comp=compact_func(mats)
   cf=pd.DataFrame({'asof_date':query_dates,'ticker':t,'source_date':np.where(fresh,srcdates,np.datetime64('NaT'))})
   for key,v in comp.items():
    cf[key]=v[t].reindex(srcdates).to_numpy()
   cf.loc[~fresh,list(comp)]=np.nan
   comparts.append(cf)
   raw=hybrid_func(mats)
   hf=cf[['asof_date','ticker','source_date']].copy()
   for key,v in raw.items():hf[key]=v[t].reindex(srcdates).to_numpy()
   log=np.log(f.Close).to_numpy();lret=np.diff(log,prepend=np.nan)
   for w in [21,63]:
    slopes=np.full(len(query_dates),np.nan);autoc=np.full(len(query_dates),np.nan)
    xc=np.arange(w)-(w-1)/2;den=np.sum(xc**2)
    for j,p in enumerate(localpos):
     if not fresh[j] or p-w+1<0:continue
     v=log[p-w+1:p+1];slopes[j]=np.sum((v-v.mean())*xc)/den
     lr=lret[p-w+1:p+1]
     if np.isfinite(lr).all() and np.std(lr[1:])>0 and np.std(lr[:-1])>0:autoc[j]=np.corrcoef(lr[1:],lr[:-1])[0,1]
    hf[f'slope_{w}']=slopes;hf[f'autocorr1_{w}']=autoc
   dom=np.full(len(query_dates),np.nan)
   for j,p in enumerate(localpos):
    if not fresh[j] or p<64:continue
    a=lret[p-63:p+1];a=a-np.nanmean(a);powr=abs(np.fft.rfft(np.nan_to_num(a)))[1:]**2
    if powr.sum()>0:dom[j]=powr.max()/powr.sum()
   hf['dominant_energy64']=dom
   numeric=[n for n in hf if n not in ['asof_date','ticker','source_date']];hf.loc[~fresh,numeric]=np.nan
   hyparts.append(hf)
   if (i+1)%40==0:print('PROGRESS',m,i+1,len(frames),round(time.time()-ts,1),flush=True)
 comp=pd.concat(comparts,ignore_index=True).replace([np.inf,-np.inf],np.nan)
 bases=[n for n in k.F2D_FEATURES if not n.endswith('_pct') and not n.endswith('_dev')]
 for name in bases:
  if name+'_pct' in k.F2D_FEATURES:comp[name+'_pct']=comp.groupby('asof_date')[name].rank(pct=True)
  if name+'_dev' in k.F2D_FEATURES:
   wide=comp.pivot(index='asof_date',columns='ticker',values=name)
   dev=k.cs_robust_dev(wide).stack(dropna=False).rename(name+'_dev').reset_index().rename(columns={'level_0':'asof_date'})
   comp=comp.merge(dev,on=['asof_date','ticker'],validate='one_to_one')
 comp['eligible']=comp[k.F2D_FEATURES].notna().sum(axis=1)>=30
 # monthly exact-membership (no daily re-cluster allowed): as-of step 1 and 2 use step-0 clusters.
 clusters=pd.read_csv(io.BytesIO(CAL.read(CAL_PREF+m+'_CLUSTERS.csv')),parse_dates=['signal_date'])
 clusters=clusters[['signal_date','ticker','cluster_id']]
 cl=eventmap[['event_j','signal_date','asof_date','asof_step']].merge(clusters,on='signal_date',how='inner',validate='many_to_many')
 # MONTHLY/source feature group; only original eligible cluster members for all three snapshots
 hy=pd.concat(hyparts,ignore_index=True).replace([np.inf,-np.inf],np.nan)
 hy=hy.merge(cl[['asof_date','ticker','event_j','asof_step','signal_date','cluster_id']],on=['asof_date','ticker'],how='inner',validate='one_to_one')
 # Original ranks in source were within the *eligible cluster population*, not whole raw universe.
 numeric=[c for c in hy if c not in ['asof_date','ticker','source_date','event_j','asof_step','signal_date','cluster_id']]
 for c in numeric:hy[c+'_rank']=hy.groupby('asof_date')[c].rank(pct=True,method='average')
 for c in ['ret_21','ret_63','ret_126','vol_63','acc_5_21','eff_63','signed_volume21']:
  hy[f'cluster_{c}_mean']=hy.groupby(['asof_date','cluster_id'])[c].transform('mean');hy[f'{c}_vs_cluster']=hy[c]-hy[f'cluster_{c}_mean']
  hy[f'{c}_cluster_rank']=hy.groupby(['asof_date','cluster_id'])[c].rank(pct=True);hy[f'cluster_{c}_univ_rank']=hy.groupby('asof_date')[f'cluster_{c}_mean'].rank(pct=True)
 for w in [21,63]:hy[f'cluster_breadth{w}']=hy.groupby(['asof_date','cluster_id'])[f'ret_{w}'].transform(lambda x:(x>0).mean())
 context=[c for c in hy if (c.startswith('cluster_') or c.endswith('_vs_cluster') or c.endswith('_cluster_rank')) and pd.api.types.is_numeric_dtype(hy[c])]
 for c in context:
  if c+'_rank' not in hy:hy[c+'_rank']=hy.groupby('asof_date')[c].rank(pct=True)
 assert not set(FEATURES_42)-set(hy)
 comp=comp.merge(eventmap[['event_j','asof_step','asof_date','signal_date','entry_date']],on='asof_date',validate='many_to_one')
 # strict correctness gates against frozen OLC08 for all 90 dates, not only 2026
 orig_comp=pd.read_pickle(io.BytesIO(CAL.read(CAL_PREF+m+'_COMPACT.pkl')))
 orig_hyb=pd.read_pickle(io.BytesIO(CAL.read(CAL_PREF+m+'_HYBRID.pkl')))
 cmp=comp[comp.asof_step.eq(0)].merge(orig_comp,on=['ticker','signal_date'],suffixes=('','_REF'),validate='one_to_one')
 check=[]
 for col in k.F2D_FEATURES:
  x=cmp[col].to_numpy(float);y=cmp[col+'_REF'].to_numpy(float);valid=np.isfinite(x)&np.isfinite(y);mask=np.array_equal(np.isfinite(x),np.isfinite(y));maxerr=float(np.max(np.abs(x[valid]-y[valid]))) if valid.any() else 0
  check.append({'feature':col,'finite_mask_equal':bool(mask),'max_abs_error':maxerr,'pass':bool(mask and maxerr<=1e-8)})
 hc=hy[hy.asof_step.eq(0)].merge(orig_hyb,on=['ticker','signal_date'],suffixes=('','_REF'),validate='one_to_one')
 hcheck=[]
 for col in FEATURES_42:
  x=hc[col].to_numpy(float);y=hc[col+'_REF'].to_numpy(float);valid=np.isfinite(x)&np.isfinite(y);mask=np.array_equal(np.isfinite(x),np.isfinite(y));maxerr=float(np.max(np.abs(x[valid]-y[valid]))) if valid.any() else 0
  hcheck.append({'feature':col,'finite_mask_equal':bool(mask),'max_abs_error':maxerr,'pass':bool(mask and maxerr<=1e-8)})
 qa={'market':m,'source':'OLC07 native source formulas + frozen calendar and clusters','rows_compact':int(len(comp)),'rows_hybrid':int(len(hy)),'features_return_pass':sum(a['pass'] for a in check),'features_return_total':125,'features_hybrid_pass':sum(a['pass'] for a in hcheck),'features_hybrid_total':42,'feature_return_failed':[a for a in check if not a['pass']][:10],'feature_hybrid_failed':[a for a in hcheck if not a['pass']][:15],'comparison_rows_compact':len(cmp),'comparison_rows_hybrid':len(hc),'elapsed_s':round(time.time()-ts,2)}
 (OUT/f'{m}_DAILY_FEATURE_QA.json').write_text(json.dumps(qa,indent=2))
 comp.to_pickle(OUT/f'{m}_DAILY_COMPACT.pkl');hy[['event_j','signal_date','asof_step','asof_date','ticker','cluster_id',*FEATURES_42]].to_pickle(OUT/f'{m}_DAILY_HYBRID.pkl')
 eventmap.to_csv(OUT/f'{m}_EVENT_MAP.csv',index=False)
 print('FINISH',json.dumps(qa),flush=True)
 return qa

if __name__=='__main__':
 import argparse
 a=argparse.ArgumentParser();a.add_argument('market',choices=['EU','USA']);v=a.parse_args();rebuild(v.market)
