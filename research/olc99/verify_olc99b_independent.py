#!/usr/bin/env python3
"""Independent account-metric, source-selection and warm-up checks for OLC99B."""
from pathlib import Path
import numpy as np,pandas as pd,json
ROOT=Path(__file__).resolve().parent;P=ROOT/'results'
sc=pd.read_csv(P/'OLC99B_NATIVE_SCORECARD.csv')
daily=pd.read_csv(P/'OLC99B_NATIVE_DAILY_LOGRET.csv.gz',parse_dates=['date'])
sel=pd.read_csv(P/'OLC99B_SELECTIONS.csv')
assert len(sc)==2*2*2*13 and len(sel)==180
qa=json.loads((P/'OLC99B_QA.json').read_text())
mx=[0.,0.];n=0
for rec in sc.itertuples(index=False):
 x=daily[(daily.market==rec.market)&(daily.arm==rec.arm)&(daily.timing==rec.timing)&(daily.fee==rec.fee)]
 x=x[(x.date>=pd.Timestamp(rec.first_valuation))&(x.date<=pd.Timestamp(rec.last_valuation))]
 assert len(x)==rec.n
 l=x.logr.to_numpy();cg=np.expm1(l.mean()*252)
 nav=np.exp(np.cumsum(l));dd=np.min(nav/np.maximum.accumulate(np.r_[1.,nav])[1:]-1)
 mx[0]=max(mx[0],abs(cg-rec.cagr));mx[1]=max(mx[1],abs(dd-rec.maxdd));n+=1
 assert abs(cg-rec.cagr)<1e-10 and abs(dd-rec.maxdd)<1e-10
reference=str(ROOT/'source/OLC98_Model_Review_20261112/native/olc19_combined_risk_20261102/restore/olc18_execution_20261102')
if not Path(reference).exists():reference='/mnt/data/olc99_refs/OLC98_Model_Review_20261112/native/olc19_combined_risk_20261102/restore/olc18_execution_20261102'
for m in ('EU','USA'):
 old=pd.read_csv(reference+f'/inputs/{m}_TOP2_CONTEXT_REVALUE_DECISIONS.csv')
 score=pd.read_csv(reference+f'/parent_archive/parent/olc16_contextual_rank_20261102/results/{m}_SCORES.csv.gz')
 rows=sel[sel.market==m].sort_values('event_j').reset_index(drop=True)
 for j,row in rows.iterrows():
  g=score[score.signal_date==row.signal_date].dropna(subset=['ORIGINAL_SMOOTH','ORIGINAL_FUSION','TOP2_CONTEXT_REVALUE_FUSION'])
  top=set(g.sort_values(['ORIGINAL_FUSION','ticker'],ascending=[False,True],kind='mergesort').head(10).ticker)
  assert row.ticker1 in top and row.ticker2 in top and row.ticker1!=row.ticker2
  if j<24:assert [row.ticker1,row.ticker2]==old.loc[j,['ticker1','ticker2']].tolist()
 assert qa['markets'][m]['candidate_rows']==900
res={'status':'PASS','independent_account_metric_rows':n,'max_cagr_error':mx[0],
 'max_drawdown_error':mx[1],'pair_in_frozen_top10':180,'first_24_events_baseline_parity':True,
 'limitations':['Historical replay only','No PIT certification for full ETF universe','Fitted model reviewed for chronology but not independently refit']}
(P/'OLC99B_INDEPENDENT_QA.json').write_text(json.dumps(res,indent=2));print(json.dumps(res,indent=2))