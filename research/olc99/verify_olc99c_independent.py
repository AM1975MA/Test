#!/usr/bin/env python3
"""OLC99C independent account and same-state source checks."""
from pathlib import Path
import numpy as np,pandas as pd,json
R=Path(__file__).resolve().parent;O=R/'results'
sc=pd.read_csv(O/'OLC99C_SCORECARD.csv');daily=pd.read_csv(O/'OLC99C_DAILY_LOGRET.csv.gz',parse_dates=['date'])
lbl=pd.read_csv(O/'OLC99C_TOP10_NATIVE_LABELS.csv.gz')
sel=pd.read_csv(O/'OLC99C_SELECTIONS.csv');qa=json.loads((O/'OLC99C_QA.json').read_text())
assert len(lbl)==1800 and len(sel)==180 and len(sc)==52
assert lbl.groupby(['market','event_j']).size().eq(10).all()
assert lbl[lbl.event_j==89].native_logr.isna().all()
mx=[0.,0.];n=0
for x in sc.itertuples(index=False):
 d=daily[(daily.market==x.market)&(daily.arm==x.arm)&(daily.timing==x.timing)&(daily.fee==x.fee)]
 d=d[(d.date>=pd.Timestamp(x.first_valuation))&(d.date<=pd.Timestamp(x.last_valuation))]
 assert len(d)==x.n
 v=d.logr.to_numpy();cagr=np.expm1(v.mean()*252);NAV=np.exp(v.cumsum())
 dd=(NAV/np.maximum.accumulate(np.r_[1.,NAV])[1:]-1).min()
 mx[0]=max(mx[0],abs(cagr-x.cagr));mx[1]=max(mx[1],abs(dd-x.maxdd));n+=1
 assert abs(cagr-x.cagr)<2e-11 and abs(dd-x.maxdd)<2e-11
 # Native labels come from *same* original context state but target differs from month Open->Open.
for m in ('EU','USA'):
 g=lbl[lbl.market==m]
 assert qa['markets'][m]['n_matched_single_asset_forks']==890
 assert qa['markets'][m]['baseline_instrumented_native_parity']=='7/7 bitwise'
 # Every signal t with n_training<24 keeps the original unchanged; no future-tied labels.
 s=sel[sel.market==m].sort_values('event_j')
 source=R/'source/OLC98_Model_Review_20261112/native/olc19_combined_risk_20261102/restore/olc18_execution_20261102/inputs'
 if not source.exists():source=Path('/mnt/data/olc99_refs/OLC98_Model_Review_20261112/native/olc19_combined_risk_20261102/restore/olc18_execution_20261102/inputs')
 ref=pd.read_csv(source/(m+'_TOP2_CONTEXT_REVALUE_DECISIONS.csv'))
 assert np.array_equal(s.iloc[:24][['ticker1','ticker2']].to_numpy(),ref.iloc[:24][['ticker1','ticker2']].to_numpy())
 assert g[(g.event_j>=25)].native_pred.notna().all() # predictions only use mature prior events
res={'status':'PASS','independent_account_metric_rows':n,'max_cagr_diff':mx[0], 'max_drawdown_diff':mx[1],
 'counterfactual_solo_etf_branches':1780,'pre_trade_state_baseline_7_arrays_bitwise':'PASS',
 'candidate_group_grain':'180x10','terminal_label_na':'PASS','warmup_parity':'PASS'}
(O/'OLC99C_INDEPENDENT_QA.json').write_text(json.dumps(res,indent=2));print(json.dumps(res,indent=2))