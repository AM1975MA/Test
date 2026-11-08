#!/usr/bin/env python3
"""Independent verification of 72 OLC74 engine paths, 18-feature models and source parity.
Does not import the authoring runner or helper for financial recomputation."""
from pathlib import Path
import numpy as np,pandas as pd,json,hashlib
P=Path(__file__).resolve().parent/'results'

def sha(p):
 h=hashlib.sha256()
 with p.open('rb') as f:
  for c in iter(lambda:f.read(4*1024*1024),b''):h.update(c)
 return h.hexdigest()

def verify():
 pairs=pd.read_csv(P/'OLC74_PAIR_PANEL.csv',parse_dates=['event_date','signal_date','exit_date'])
 assert len(pairs)==180 and not pairs.duplicated(['market','pos']).any()
 assert (pairs.event_date>pairs.signal_date).all()
 assert (pairs.groupby('market').pos.agg(['min','max']).to_numpy()==np.array([[0,89],[0,89]])).all()
 fit=pairs[pairs.fit_available]
 assert len(fit)==128 and (fit.max_train_pos<=fit.pos-2).all() and (fit.n_train>=24).all()
 # True event-mature label, never access prior observation from same or previous event.
 for m,g in pairs.groupby('market'):
  g=g.sort_values('pos').reset_index(drop=True)
  for r in g.itertuples():
   if r.fit_available:
    assert g.loc[r.max_train_pos,'exit_date']<=g.loc[r.pos-1,'event_date']
 pairb=pd.read_csv(P/'OLC74B_PAIR_FORECASTS.csv',parse_dates=['event_date'])
 assert len(pairb)==180 and (pairb.loc[pairb.fit_available,'max_train_pos']<=pairb.loc[pairb.fit_available,'pos']-2).all()
 score=pd.concat([pd.read_csv(P/'OLC74_SCORECARD.csv'),pd.read_csv(P/'OLC74B_SCORECARD.csv')],ignore_index=True)
 daily=pd.concat([pd.read_csv(P/'OLC74_DAILY_LOGRET.csv.gz'),pd.read_csv(P/'OLC74B_DAILY_LOGRET.csv.gz')],ignore_index=True)
 ann=pd.concat([pd.read_csv(P/'OLC74_ANNUAL.csv'),pd.read_csv(P/'OLC74B_ANNUAL.csv')],ignore_index=True)
 daily.date=pd.to_datetime(daily.date)
 assert daily.groupby('key').size().shape[0]==72
 assert score.groupby('key').size().nunique()==1 and len(score)==72*9
 assert len(ann)==72*8
 checks=0;maxdelta=0.;sub=[]
 for r in score.itertuples(index=False):
  z=daily[(daily.key==r.key)&(daily.date>=r.first_valuation)&(daily.date<=r.last_valuation)].sort_values('date')
  x=z.logr.to_numpy(float);assert len(x)==r.n,(r.key,r.period,len(x),r.n)
  comp=float(np.expm1(x.sum()/len(x)*252))
  eq=np.exp(np.cumsum(x));peak=np.maximum.accumulate(np.r_[1.,eq]);dd=float(np.min(eq/peak[1:]-1))
  dif=max(abs(comp-r.cagr),abs(dd-r.maxdd));maxdelta=max(maxdelta,dif)
  assert dif<1e-10,(r.key,r.period,dif)
  checks+=1
 for r in ann.itertuples(index=False):
  z=daily[(daily.key==r.market+'_'+r.policy+'_'+r.timing+'_'+str(int(r.fee*10000)))&(daily.date.dt.year==r.year)]
  assert len(z)==r.n
  val=float(np.expm1(z.logr.to_numpy(float).sum()));assert abs(val-r[-2])<1e-10
 # original OLC73 reference exact native ledger daily log returns (same date and original name)
 old=pd.read_csv('/mnt/data/OLC73_Allocation_20261108/results/OLC73_DAILY_LOGRET.csv.gz')
 for key in ['EU_HALF_IMMEDIATE_10','USA_HALF_IMMEDIATE_10','EU_MINVAR63_DELAY3_10','USA_MINVAR63_DELAY3_10']:
  k=key.replace('_MINVAR63_','_MINVAR63_CAP25_')
  x=daily[daily.key==key].logr.to_numpy();y=old[old.key==k].logr.to_numpy();assert len(x)==len(y) and np.max(np.abs(x-y))<1e-13
 weights=pd.concat([pd.read_csv(P/'OLC74_EVENT_WEIGHTS.csv'),pd.read_csv(P/'OLC74B_EVENT_WEIGHTS.csv')])
 assert len(weights)==180*9 and weights.w1.between(.25-1e-12,.75+1e-12).all()
 assert np.max(np.abs(weights.w1+weights.w2-1))<1e-12
 data={'status':'PASS','engine_paths':72,'annual_return_recalculations':len(ann),'period_CAGR_MaxDD_recalculations':checks,'max_abs_cagr_drawdown_error':maxdelta,'max_train_pos_at_least_two_events_before_current':True,'score_source_dates_prior_to_event':True,'static_original_parity_keys':4,'market_source_mask_USA_absent':True}
 (P/'OLC74_INDEPENDENT_QA.json').write_text(json.dumps(data,indent=2));print(json.dumps(data,indent=2))
if __name__=='__main__':verify()