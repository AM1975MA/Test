#!/usr/bin/env python3
"""Independent table/accounting QA; does not import run_olc75 or native accounting code."""
from pathlib import Path
import json, numpy as np,pandas as pd,zipfile,io
ROOT=Path(__file__).resolve().parent;R=ROOT/'results'
panel=pd.read_csv(R/'OLC75_EVENT_FORECASTS.csv',parse_dates=['event_date','signal_date','exit_date'])
consensus=pd.read_csv(R/'OLC75_CONSENSUS_DIAGNOSTIC.csv')
skill=pd.read_csv(R/'OLC75_FORECAST_SKILL.csv')
card=pd.read_csv(R/'OLC75_SCORECARD.csv')
daily=pd.read_csv(R/'OLC75_DAILY_LOGRET.csv.gz',parse_dates=['date'])
annual=pd.read_csv(R/'OLC75_ANNUAL.csv')
w=pd.read_csv(R/'OLC75_EVENT_WEIGHTS.csv',parse_dates=['event_date'])
assert len(panel)==180 and panel.groupby('market').size().to_dict()=={'EU':90,'USA':90}
assert panel.groupby('market').diff_month_log.count().to_dict()=={'EU':87,'USA':89}
assert not panel.duplicated(['market','pos']).any()
assert (panel.signal_date<panel.event_date).all()
assert (panel.train_max_pos.eq(-1)|panel.train_max_pos.le(panel.pos-2)).all()
assert panel[panel.trainable].n_train_y.ge(24).all()
assert panel[~panel.trainable].n_train_y.lt(24).all()
assert np.allclose(panel.d_fusion, .475*panel.d_return+.525*panel.d_hybrid_smooth,atol=1e-11,rtol=0)
assert len(w)==180*5 and w.w1.between(.25,.75).all() and np.allclose(w.w1+w.w2,1)
refkey=['market','pos','event_date','ticker1','ticker2']
with zipfile.ZipFile('/mnt/data/OLC74_Causal_Allocazione_Top2_20261108_VERIFICATO.zip') as z:
 original=pd.read_csv(z.open('OLC74/results/OLC74_PAIR_PANEL.csv'),parse_dates=['event_date','signal_date'])
ref=panel.merge(original[refkey+['diff_month_log']],on=refkey,validate='one_to_one',suffixes=('','_ref'))
assert len(ref)==180
m=ref.diff_month_log.notna()&ref.diff_month_log_ref.notna()
assert np.max(np.abs(ref.loc[m,'diff_month_log']-ref.loc[m,'diff_month_log_ref']))<1e-14
keycounts=daily.groupby('key').size()
assert len(keycounts)==40 and all(keycounts>1500)
counts=card.groupby(['market','policy','timing','fee']).size()
assert len(counts)==40 and counts.nunique()==1
# Independent daily valuation arithmetic: grouped by native key; same aligned first/last dates as metrics.
checks=[]
for s in card.itertuples(index=False):
 vals=daily[(daily.key==s.key)&daily.date.between(pd.Timestamp(s.first_valuation),pd.Timestamp(s.last_valuation))].logr.to_numpy(float)
 assert len(vals)==s.n
 nv=np.exp(np.cumsum(vals));maxv=np.maximum.accumulate(np.r_[1.,nv])[1:]
 c=np.expm1(vals.mean()*252.);dd=np.min(nv/maxv-1)
 assert abs(c-s.cagr)<1e-10,(s.key,s.period,'CAGR',c,s.cagr)
 assert abs(dd-s.maxdd)<1e-10,(s.key,s.period,'DD',dd,s.maxdd)
 checks.append((s.key,s.period))
for _,s in annual.iterrows():
 ss=daily[(daily.market==s.market)&(daily.policy==s.policy)&(daily.timing==s.timing)&(daily.fee==s.fee)&(daily.date.dt.year==s.year)]
 assert len(ss)==s.n
 assert abs(np.expm1(ss.logr.sum())-s['return'])<1e-10
for s in skill.itertuples(index=False):
 filt=panel[(panel.market==s.market)&panel.trainable&panel.label_win.notna()]
 if s.period=='MAIN':filt=filt[filt.event_date.dt.year.between(2021,2024)]
 elif s.period=='2026_PART':filt=filt[filt.event_date.dt.year==2026]
 elif s.period!='FULL':filt=filt[filt.event_date.dt.year==int(s.period)]
 assert len(filt)==s.n
 probs=filt[s.model].to_numpy(float);y=filt.label_win.to_numpy(float)
 b=np.mean((probs-y)**2)
 assert abs(b-s.brier)<1e-11
# Classifier confidence intervals: H1 majority/unanimity counts derive from pre-labelled frame only.
for row in consensus.itertuples(index=False):
 if row.period!='MAIN':continue
 g=panel[(panel.market==row.market)&panel.event_date.dt.year.between(2021,2024)&panel.label_win.notna()]
 if row.group=='unanimous':g=g[g.unanimity==1]
 elif row.group=='split_votes':g=g[g.unanimity==0]
 else:continue
 assert len(g)==row.n
 assert abs(g.label_win.mean()-row.first_win_rate)<1e-12
qa={'verified':True,'n_event_rows':int(len(panel)),'event_labels_by_market':{k:int(v) for k,v in panel.groupby('market').diff_month_log.count().to_dict().items()},'n_policy_paths':int(len(keycounts)),'n_scorecard_periods':len(checks),'n_annual_verified':len(annual),'n_skill_verified':len(skill),'native_reference_parity':'verified separately in OLC75_QA', 'prequential_label_maturity':'PASS','pair_source_parity':'PASS','numerical_accounting':'PASS','asof_dates':'PASS','untouched_aug_oct_2026':'NOT_AVAILABLE'}
(R/'OLC75_INDEPENDENT_QA.json').write_text(json.dumps(qa,indent=2))
print(json.dumps(qa,indent=2))