#!/usr/bin/env python3
"""OLC102 independent monthly paired analysis; no parameter selection."""
import os
for k in ['OPENBLAS_NUM_THREADS','MKL_NUM_THREADS','OMP_NUM_THREADS']:os.environ[k]='1'
from pathlib import Path
import numpy as np,pandas as pd,json
ROOT=Path('/mnt/data/olc102/results');ROOT.mkdir(exist_ok=True)
S=pd.read_csv(ROOT/'OLC102_SCORECARD.csv');d=pd.read_csv(ROOT/'OLC102_DAILY.csv.gz',parse_dates=['date']);sel=pd.read_csv(ROOT/'OLC102_SELECTION_CHANGES.csv');d['month']=d.date.dt.to_period('M').astype(str)
PAIRINGS=[('ML_DAY1_HALF','FIXED_DAY1_HALF'),('ML_DAY2_HALF','FIXED_DAY2_HALF'),('ML_AVG_50_30_20_HALF','FIXED_DAY2_HALF'),('ML_AVG_80_15_05_HALF','FIXED_DAY2_HALF'),('ML_AVG_20_30_50_HALF','FIXED_DAY2_HALF'),('ML_SCORE_AVG_50_30_20_HALF','FIXED_DAY2_HALF'),('ML_AVG_50_30_20_MINVAR63','FIXED_DAY2_MINVAR63'),('ML_AVG_80_15_05_MINVAR63','FIXED_DAY2_MINVAR63'),('ML_AVG_20_30_50_MINVAR63','FIXED_DAY2_MINVAR63'),('OLC67_MINVAR63_DELAY3','OLC19_IMMEDIATE')]
paired=[];annual=[]
for m in ['EU','USA']:
 month=d[(d.market==m)&d.fee.eq(.001)].groupby(['arm','month']).agg(mlr=('lr','sum'),ndays=('lr','size')).reset_index()
 for a,b in PAIRINGS:
  left=month[month.arm==a].set_index('month');right=month[month.arm==b].set_index('month');months=sorted(set(left.index)&set(right.index))
  assert len(months)>=80
  dl=(left.loc[months,'mlr']-right.loc[months,'mlr']).to_numpy(float);N=left.loc[months,'ndays'].to_numpy(int)
  assert np.array_equal(N,right.loc[months,'ndays'].to_numpy(int))
  rng=np.random.default_rng(102113)
  n=len(months);L=6;boot=np.empty(5000,float)
  for k in range(len(boot)):
   idcs=[]
   while len(idcs)<n:
    start=int(rng.integers(0,n));idcs.extend(((start+np.arange(L))%n).tolist())
   ix=np.array(idcs[:n]);boot[k]=252*dl[ix].sum()/N[ix].sum()
  point=252*dl.sum()/N.sum();ci=np.quantile(boot,[.025,.975])
  paired.append(dict(market=m,arm=a,control=b,months=n,delta_log_annual=point,ci95_low=ci[0],ci95_high=ci[1],months_outperform=int(np.sum(dl>0)),months_underperform=int(np.sum(dl<0)),tail_worst_month=months[int(np.argmin(dl))],tail_worst_month_log_difference=float(np.min(dl))))
 for arm,g in d[(d.market==m)&d.fee.eq(.001)].groupby('arm'):
  for y,grp in g.groupby(g.date.dt.year):
   annual.append(dict(market=m,arm=arm,year=int(y),n=int(len(grp)),return_cumulative=float(np.expm1(grp.lr.sum()))))
pd.DataFrame(paired).to_csv(ROOT/'OLC102_PAIRED_BLOCK6.csv',index=False)
pd.DataFrame(annual).to_csv(ROOT/'OLC102_ANNUAL_RETURNS.csv',index=False)
sel.groupby(['market','policy'],as_index=False).agg(months=('event_j','size'),changed_pairs=('changed_identity','sum'),changed_order=('changed_order','sum')).to_csv(ROOT/'OLC102_SELECTION_SUMMARY.csv',index=False)
qa=json.loads((ROOT/'OLC102_NATIVE_QA.json').read_text())
qa.update({'n_paired_comparisons':len(paired),'paired_bootstrap_repetitions':5000,'block_months':6,'boot_seed':102113,'not_multiplicity_adjusted':True,'not_new_holdout':True,'same_execution_time_controls':True})
(ROOT/'OLC102_NATIVE_QA.json').write_text(json.dumps(qa,indent=2)+'\n')
print(pd.DataFrame(paired).round(4).to_string(index=False));print('SUMMARY',pd.DataFrame(paired).shape,flush=True)
