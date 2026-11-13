#!/usr/bin/env python3
"""OLC102: original OLC19 contextual score updated with actual frozen ML predictions.
Exact baseline R0; daily scores change only by the frozen-model prediction deltas
from R0 to each +1/+2 observed close, with frozen monthly clusters/eligibility.
"""
from __future__ import annotations
import os
for n in ['OPENBLAS_NUM_THREADS','OMP_NUM_THREADS','MKL_NUM_THREADS']:os.environ[n]='1'
import sys,json,io,zipfile,time
from pathlib import Path
import numpy as np,pandas as pd
ROOT=Path('/mnt/data/olc102');OUT=ROOT/'results';sys.path.insert(0,str(ROOT/'srcfreeze'))
from core import benchmark_context,leadership
from context_model import predict_weights
from revalue_memory import revalue
CK=zipfile.ZipFile('/mnt/data/frozen_sources/OLC19_Rischio_Rientro_Checkpoint_20261102.zip');B='olc19_combined_risk_20261102/restore/olc18_execution_20261102/parent_archive/parent/olc16_contextual_rank_20261102/'
CAL=zipfile.ZipFile('/mnt/data/olc101/original_models/OLC08_01_Pannelli_Verificati_20261101.zip');CALROOT='parents/olc07_calendar_20261101/phases/P0/results/calendar/'
ANNUAL={int(k):v for k,v in json.loads(CK.read(B+'results/ANNUAL_MODELS.json')).items()}

def retable(path,date='signal_date'):
 return pd.read_csv(io.BytesIO(CK.read(B+path)),compression='gzip' if path.endswith('.gz') else 'infer',parse_dates=[date],float_precision='round_trip')

def generate(m):
 ts=time.time(); ml=pd.read_pickle(OUT/f'{m}_DAILY_ML_SCORES.pkl')
 eventmap=pd.read_csv(OUT/f'{m}_EVENT_MAP.csv',parse_dates=['signal_date','entry_date','asof_date'])
 ref=retable(f'results/{m}_SCORES.csv.gz');fit=retable(f'inputs/{m}_FITTING_FRAME.csv.gz');cum=retable(f'inputs/{m}_MEAN3_SCORES.csv.gz');gate=retable('inputs/GATE_PANEL.csv','date');gate=gate[gate.market.eq(m)].set_index('date')
 assert len(ref.signal_date.unique())==90
 # Build baseline original group sequence as originally used by OLC16.
 hist=fit[['signal_date','ticker','C21','C42','C63']].merge(cum[['signal_date','ticker','CUM_FIXED_MAPPED']],on=['signal_date','ticker'],validate='one_to_one')
 groups=[];betas=[]
 for d,g in hist.groupby('signal_date',sort=True):
  g=g.dropna(subset=['C21','C42','C63','CUM_FIXED_MAPPED']).sort_values('ticker')
  if g.empty:raise ValueError('No native OLC19 group')
  context=gate.loc[d][['trend126','vol_ratio','leadership']].to_numpy(float)
  model=ANNUAL.get(d.year,{}).get('TOP2_CONTEXT')
  beta=predict_weights(model,context) if model else np.array([.45,.35,.20])
  groups.append(dict(date=d,tickers=g.ticker.to_numpy(str),z=g[['C21','C42','C63']].to_numpy(float),anchor=g.CUM_FIXED_MAPPED.to_numpy(float),x=context))
  betas.append(beta)
 ref_map={str(d.date()):g.set_index('ticker') for d,g in ref.groupby('signal_date')}
 smooth=revalue(groups,betas);compares=[]
 for g,s in zip(groups,smooth):
  r=ref_map[str(g['date'].date())].reindex(g['tickers'])
  if len(r)!=len(g['tickers']) or r.TOP2_CONTEXT_REVALUE_SMOOTH.isna().any():raise ValueError('missing ref')
  err=float(np.max(abs(s-r.TOP2_CONTEXT_REVALUE_SMOOTH.to_numpy(float))))
  if err>2e-10:raise ValueError((m,g['date'],'baseline OLC16 revalue mismatch',err))
  compares.append(err)
 print('ORIGINAL_REVALUE_PARITY',m,len(compares),max(compares),flush=True)
 # Rebuild benchmark as of day after original monthly signal, no future prices used.
 C=pd.read_pickle(io.BytesIO(CAL.read(CALROOT+f'{m}_CLOSE.pkl')))
 ticker='EXSA.DE' if m=='EU' else 'SPY'
 ctx=benchmark_context(C[ticker].dropna())
 drows=[];qa_r0=[];p_ranks=[]
 for j,(g,beta0) in enumerate(zip(groups,betas)):
  date=g['date'];sm=smooth[j];r=ref_map[str(date.date())].reindex(g['tickers'])
  original_s=r.TOP2_CONTEXT_REVALUE_FUSION.to_numpy(float)
  if not np.isfinite(original_s).all():raise ValueError((m,j,'nonfinite baseline'))
  for step in [0,1,2]:
   view=ml[(ml.event_j.eq(j))&(ml.asof_step.eq(step))].set_index('ticker').reindex(g['tickers'])
   if step==2 and len(view)==len(g['tickers']) and view.asof_date.isna().all():continue
   if view.empty or view['asof_date'].isna().any():
    assert j==89 and step==2;continue
   origin=ml[(ml.event_j.eq(j))&(ml.asof_step.eq(0))].set_index('ticker').reindex(g['tickers'])
   # Original native predictor output at asof s0 is the exact canonical score.
   # Frozen annual models produce *increments* only. This anchors finite-rank
   # precision/support differences without changing legacy monthly decisions.
   tr=r['RETURN'].to_numpy(float)+(view.RETURN.to_numpy(float)-origin.RETURN.to_numpy(float))
   new_z=np.column_stack([g['z'][:,ind]+(view[h].to_numpy(float)-origin[h].to_numpy(float)) for ind,h in enumerate(['C21','C42','C63'])])
   anc=g['anchor']+(view.CUM_FIXED_MAPPED.to_numpy(float)-origin.CUM_FIXED_MAPPED.to_numpy(float))
   assert np.isfinite(tr).all() and np.isfinite(new_z).all() and np.isfinite(anc).all(),(m,j,step,'nonfinite model scores')
   asof_date=pd.Timestamp(view.asof_date.iloc[0]);
   if step==0:
    beta=beta0
   else:
    observed=ctx.index.searchsorted(asof_date,side='right')-1
    assert observed>=0
    feat=ctx.iloc[observed]
    if j>0:
     previous=cum[cum.signal_date.eq(groups[j-1]['date'])].set_index('ticker')['CUM_FIXED_MAPPED']
     L=leadership(pd.Series(anc,index=g['tickers']),previous)
    else:L=np.nan
    contextual=np.array([feat.trend126,feat.vol_ratio,L])
    model=ANNUAL.get(date.year,{}).get('TOP2_CONTEXT')
    beta=predict_weights(model,contextual) if model else np.array([.45,.35,.20])
   gnew=dict(g,z=new_z,anchor=anc)
   other=groups[:j]+[gnew]; bb=betas[:j]+[beta];new_sm=revalue(other,bb)[-1]
   score=np.clip(r.TOP2_CONTEXT_REVALUE_FUSION.to_numpy(float)+(.475*(tr-r.RETURN.to_numpy(float))+.525*(new_sm-sm)),0,1)
   if step==0:
    err=float(np.max(abs(score-original_s)))
    assert err<1e-11,(m,j,err)
    # Verify original Top2 order, not just cross-sectional norm
    original=ref_map[str(date.date())].sort_values(['TOP2_CONTEXT_REVALUE_FUSION','ticker'],ascending=[False,True]).head(2).index.to_list()
    predicted=list(np.asarray(g['tickers'])[np.lexsort((g['tickers'],-score))[:2]])
    assert original==predicted,(m,j,'Top2 mismatch',original,predicted)
    qa_r0.append(err)
   rank=pd.Series(score,index=g['tickers']).rank(pct=True,method='average').to_numpy(float)
   for i,t in enumerate(g['tickers']):
    drows.append({'market':m,'event_j':j,'signal_date':str(date.date()),'asof_step':step,'asof_date':str(asof_date.date()),'ticker':t,'original_score':float(original_s[i]),'updated_score':float(score[i]),'updated_percentile':float(rank[i]),'native_return':float(r.RETURN.iloc[i]),'updated_return':float(tr[i]),'beta21':float(beta[0]),'beta42':float(beta[1]),'beta63':float(beta[2])})
 print('SCORE_ROWS',m,len(drows),'elapsed',round(time.time()-ts,2),flush=True)
 df=pd.DataFrame(drows);df.to_pickle(OUT/f'{m}_DAILY_CONTEXTUAL_RANK.pkl');df.to_csv(OUT/f'{m}_DAILY_CONTEXTUAL_RANK.csv.gz',index=False,compression='gzip')
 qa={'market':m,'n_events':len(groups),'baseline_revalue_max_error':max(compares),'baseline_score_max_error':max(qa_r0),'candidate_rows':len(df),'s0_monthly_top2_exact':len(qa_r0),'status':'PASS_ORIGINAL_MONTHLY_SCORE_PARITY__DAILY_UPDATED_FROZEN_ML_RESEARCH','daily_cluster_state':'MONTHLY_CLUSTER_FROZEN','daily_frozen_model_scores_anchored_to_native_monthly':True,'sample_in':str(eventmap.signal_date.min().date()),'sample_through':str(eventmap.signal_date.max().date()),'elapsed_s':time.time()-ts}
 (OUT/f'{m}_DAILY_CONTEXT_QA.json').write_text(json.dumps(qa,indent=2))
 print('FINAL',json.dumps(qa),flush=True)

if __name__=='__main__':
 import argparse;ap=argparse.ArgumentParser();ap.add_argument('market',choices=['EU','USA']);generate(ap.parse_args().market)
