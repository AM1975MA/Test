#!/usr/bin/env python3
"""OLC102 original OLC19/OLC67 complete-accounting experiment.
Four genuine frozen-ML daily rank variations, equal-timing controls, two weights,
EU/USA, exact native risk engine, costs and explicit no-LIVE gating.
Historic period mined; cannot claim alpha or prospective performance.
"""
from __future__ import annotations
import os
for v in ('OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS'):os.environ[v]='1'
import sys,time,io,json,hashlib,zipfile
from pathlib import Path
import numpy as np,pandas as pd
ROOT=Path('/mnt/data/olc102');OUT=ROOT/'results';OUT.mkdir(exist_ok=True)
sys.path.insert(0,str(ROOT))
import sim_backend as b

# Interpret rank percentages as ordinal information; no ticker leakage from outcomes.
POLICIES={
 'FIXED_DAY1': ('FIXED',1),
 'ML_DAY1':('DAY1',1),
 'FIXED_DAY2':('FIXED',2),
 'ML_DAY2':('DAY2',2),
 'ML_AVG_50_30_20':('AVG',2),
 'ML_AVG_80_15_05':('CONSERVATIVE',2),
 'ML_AVG_20_30_50':('RECENT',2),
 'ML_SCORE_AVG_50_30_20':('SCORE_AVG',2),
}

def load_pairs(m,dec):
 data=pd.read_pickle(OUT/f'{m}_DAILY_CONTEXTUAL_RANK.pkl')
 pairs={name:[] for name in POLICIES}
 changes=[]
 for j in range(len(dec)):
  native=(str(dec.ticker1.iloc[j]),str(dec.ticker2.iloc[j]))
  rows=data[data.event_j.eq(j)];gs={s:g.set_index('ticker') for s,g in rows.groupby('asof_step')}
  def best(data):
   r=data.sort_values(['score','ticker'],ascending=[False,True],kind='mergesort').head(2).ticker.tolist()
   return (str(r[0]),str(r[1]))
  if 0 not in gs:raise ValueError(('missing original asof',m,j))
  original=set(gs[0].index)
  assert len(original)>=10 and all(set(g.index)==original for g in gs.values())
  p0=gs[0].updated_percentile.rename('p0')
  if 1 in gs:p1=gs[1].updated_percentile.rename('p1')
  else:p1=p0.rename('p1')
  if 2 in gs:p2=gs[2].updated_percentile.rename('p2')
  else:p2=p0.rename('p2')
  s0=gs[0].updated_score.rename('s0');s1=gs.get(1,gs[0]).updated_score.rename('s1');s2=gs.get(2,gs[0]).updated_score.rename('s2')
  x=pd.concat([p0,p1,p2,s0,s1,s2],axis=1).reset_index(names='ticker')
  candidate={
   'FIXED':native,
   'DAY1':best(x.assign(score=x.p1)),
   'DAY2':best(x.assign(score=x.p2)),
   'AVG':best(x.assign(score=.5*x.p0+.3*x.p1+.2*x.p2)),
   'CONSERVATIVE':best(x.assign(score=.8*x.p0+.15*x.p1+.05*x.p2)),
   'RECENT':best(x.assign(score=.2*x.p0+.3*x.p1+.5*x.p2)),
   'SCORE_AVG':best(x.assign(score=.5*x.s0+.3*x.s1+.2*x.s2)),
  }
  if j==len(dec)-1: # no +2 completed close for the last monthly event
   candidate={n:native for n in candidate}
  for name,(style,lag) in POLICIES.items():
   pair=candidate[style];pairs[name].append(pair)
   changes.append({'market':m,'event_j':j,'signal_date':str(pd.Timestamp(dec.signal_date.iloc[j]).date()),'policy':name,
                   'original1':native[0],'original2':native[1],'chosen1':pair[0],'chosen2':pair[1],
                   'changed_identity':int(set(pair)!=set(native)),'changed_order':int(pair!=native),'same_time_control':'FIXED_DAY1' if lag==1 else 'FIXED_DAY2','min_rank_gap':float(x.p0.nlargest(2).iloc[0]-x.p0.nlargest(2).iloc[1])})
 return pairs,pd.DataFrame(changes)

def independent_metrics(nav,dates,start=None,end=None):
 # Independent calculation uses *exact OLC19 accounting convention*: last NAV is an evaluation date,
 # not an observed next-session outcome. Initial boundary is synthetic NAV 1.
 x=np.asarray(nav,float);dt=pd.DatetimeIndex(dates);actual=dt[1:];r=np.diff(np.log(np.r_[1.,x]))[:-1]
 mask=np.ones(len(actual),bool)
 if start:mask&=actual>=pd.Timestamp(start)
 if end:mask&=actual<=pd.Timestamp(end)
 v=r[mask];eq=np.exp(np.cumsum(v));dd=eq/np.maximum.accumulate(np.r_[1.,eq])[1:]-1
 return dict(CAGR=float(np.expm1(np.mean(v)*252)),MaxDD=float(np.min(dd)),n=len(v))

def run():
 t=time.time();data={m:b.source(m) for m in ['EU','USA']};qu=data['USA'][0]
 scorecards=[];daily=[];decisions=[];audit=[]
 arm_configs={'OLC19_IMMEDIATE':('NATIVE',0,'HALF','IMMEDIATE'),
              'OLC67_MINVAR63_DELAY3':('NATIVE',0,'MINVAR63','DELAY'),
              'OLC19_NATIVE_DELAY3':('NATIVE',0,'HALF','DELAY')}
 for name,(style,lag) in POLICIES.items():
  for allocation in ['HALF','MINVAR63']:
   arm_configs[f'{name}_{allocation}']=(name,lag,allocation,'IMMEDIATE')
 for m,(q,dec,scores) in data.items():
  events=np.flatnonzero(q['events']);original=[(str(x.ticker1),str(x.ticker2)) for x in dec.itertuples()]
  source=b.simulate(q,.001,.001)
  for key in b.F:
   assert np.array_equal(source[key],b.orig_ref(m)[key]),(m,key,'original native 7-array parity FAIL')
  assert np.array_equal(b.v6_alt(m,q,qu),q['alt']),('native V6 parities not met',m)
  arms,changes=load_pairs(m,dec);decisions.append(changes)
  m_audit={'market':m,'events':len(events),'baseline_arrays_bitwise':len(b.F),'original_V6_alt_bitwise':True,'all_initial_selections_exact':True}
  for arm,(key,lag,alloc,timing) in arm_configs.items():
   if arm=='OLC19_IMMEDIATE':z=q
   elif key=='NATIVE':
    z,_=b.staged(q,events,original,'fixed',0,alloc)
    z['alt'][:]=b.v6_alt(m,z,qu)
   else:
    z,used=b.staged(q,events,arms[key],key,lag,alloc)
    z['alt'][:]=b.v6_alt(m,z,qu)
   for fee,friction in [(0.001,0.001),(0.003,0.005)]:
    r=b.simulate(z,fee,friction,timing)
    mat={x['period']:x for x in b.metrics(q,r)};full={'CAGR':mat['FULL']['cagr'],'MaxDD':mat['FULL']['maxdd'],'n_days':mat['FULL']['n']};main={'CAGR':mat['ACTIVE2021_2024']['cagr'],'MaxDD':mat['ACTIVE2021_2024']['maxdd']}
    independent=independent_metrics(r['nav'],q['dates'])
    if abs(full['CAGR']-independent['CAGR'])>1e-12 or abs(full['MaxDD']-independent['MaxDD'])>1e-12:raise AssertionError((m,arm,'independent nav math'))
    p=dict(market=m,arm=arm,fee=fee,friction=friction,CAGR_FULL=full['CAGR'],MaxDD_FULL=full['MaxDD'],CAGR_MAIN=main['CAGR'],MaxDD_MAIN=main['MaxDD'],NAV_END=float(r['nav'][-1]),Stops=int(np.sum(r['ledger'][:,8])),n_days=full['n_days'],turnover_total=float(np.sum(r['ledger'][:,4])))
    scorecards.append(p)
    nav=r['nav'];lr=np.r_[np.diff(np.log(np.r_[1.,nav]))[:-1],np.nan]
    daily.extend({'market':m,'arm':arm,'fee':fee,'friction':friction,'date':str(pd.Timestamp(d).date()),'nav':float(v),'lr':float(x)} for d,v,x in zip(q['dates'][1:],nav[:-1],lr[:-1]))
   if arm in ['OLC19_IMMEDIATE','OLC67_MINVAR63_DELAY3','FIXED_DAY2_HALF','ML_AVG_50_30_20_HALF','ML_AVG_80_15_05_HALF','ML_AVG_50_30_20_MINVAR63']:
    print('ARM',m,arm,'CAGR',round(100*scorecards[-2]['CAGR_FULL'],3),'DD',round(100*scorecards[-2]['MaxDD_FULL'],3),flush=True)
  audit.append(m_audit)
  print('MARKET_DONE',m,'sec',round(time.time()-t,2),flush=True)
 ds=pd.DataFrame(scorecards);dd=pd.DataFrame(daily);ch=pd.concat(decisions)
 ds.to_csv(OUT/'OLC102_SCORECARD.csv',index=False);dd.to_csv(OUT/'OLC102_DAILY.csv.gz',compression='gzip',index=False);ch.to_csv(OUT/'OLC102_SELECTION_CHANGES.csv',index=False)
 # check historical official OLC19 and OLC67 reference directly
 EXPECT={'EU':{'OLC19_IMMEDIATE':.1976,'OLC67_MINVAR63_DELAY3':.2261},'USA':{'OLC19_IMMEDIATE':.3948,'OLC67_MINVAR63_DELAY3':.4210}}
 for m,ar in EXPECT.items():
  for arm,v in ar.items():
   v2=ds[(ds.market.eq(m))&ds.arm.eq(arm)&ds.fee.eq(.001)].CAGR_FULL.iloc[0]
   assert abs(v2-v)<.00012,(m,arm,v2)
 qa={'status':'OLC102_FROZEN_DAILY_ML_NATIVE_REPLAY_PASS_RETROSPECTIVE_ONLY','native_baseline_audits':audit,'n_paths':len(ds),'n_decisions_tested':180,'eligible_retrospective_end':'2026-07-01','model_validation':'see separate feature and rank QA files','paired_policy_comparison_requires_matching_timing':True,'no_prospective_outcome':True,'not_broker_execution':True,'completion_seconds':time.time()-t}
 (OUT/'OLC102_NATIVE_QA.json').write_text(json.dumps(qa,indent=2))
 print('TOTAL',len(ds),'elapsed',round(time.time()-t,2),flush=True)

if __name__=='__main__':run()
