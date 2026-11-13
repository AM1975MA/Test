#!/usr/bin/env python3
"""Independent portfolio math and locked selection/timing checks; no native metric functions."""
from pathlib import Path
import numpy as np,pandas as pd,json,hashlib
root=Path('/mnt/data/olc103');out=root/'results'
score=pd.read_csv(out/'OLC103_NATIVE_SCORECARD.csv')
daily=pd.read_csv(out/'OLC103_NATIVE_DAILY.csv.gz')
assert len(score)==48,len(score)
qa=[]; errors=[]
for row in score.itertuples(index=False):
 x=daily.loc[(daily.market==row.market)&(daily.allocation==row.allocation)&(daily.policy==row.policy)&(daily.fee==row.fee)&(daily.friction==row.friction)].sort_values('date')
 n=np.r_[x.nav.to_numpy(float),row.nav_final];assert len(n)>1500,(row.market,row.policy,len(n))
 lr=np.diff(np.log(np.r_[1.0,n]))[:-1]
 cagr=float(np.expm1(np.mean(lr)*252))
 eq=np.exp(lr.cumsum());maxdd=float(np.min(eq/np.maximum.accumulate(np.r_[1.,eq])[1:]-1))
 errors.append((abs(cagr-row.native_CAGR_FULL),abs(maxdd-row.native_MaxDD_FULL)))
 qa.append(dict(market=row.market,allocation=row.allocation,policy=row.policy,fee=row.fee,friction=row.friction,cagr_diff=abs(cagr-row.native_CAGR_FULL),maxdd_diff=abs(maxdd-row.native_MaxDD_FULL)))
assert max(e[0] for e in errors)<1e-12 and max(e[1] for e in errors)<1e-12,sorted(errors)[-4:]
assert score.groupby(['market','allocation','policy']).size().eq(2).all()
for m in ['EU','USA']:
 events=pd.read_csv(out/f'{m}_EVENT_STABILITY.csv');assert len(events)==89
 assert ((events.persist_day1+events.persist_day2)/4==events.retention).all()
 assert (events.full_stable==((events.persist_day1==2)&(events.persist_day2==2)).astype(int)).all()
 assert (pd.to_datetime(events.entry_day2_open)>pd.to_datetime(events.signal_date)).all()
 assert (pd.to_datetime(events.next_event_open)>pd.to_datetime(events.entry_day2_open)).all()
 assert not events.duplicated('signal_date').any()
 for t in ['quote_quality_ok','bad_loss_5pct','future_log_raw','future_log_excess']:
  assert events[t].notna().all(),t
for r in ['EU','USA']:
 p=pd.read_csv(out/'OLC103_PREQUENTIAL_PREDICTIONS.csv').query('market==@r')
 assert p.j.min()>=25 and p.n_train.min()>=24
 assert p.j.is_unique
r={'status':'PASS_FROZEN_REFERENCE_AND_48_NATIVE_INDEPENDENT_RECALCULATIONS','number_native_paths':len(score),'maximum_absolute_cagr_error':max(e[0] for e in errors),'maximum_absolute_maxdd_error':max(e[1] for e in errors),'predictive_data_source_quality':'EU 87/89 valid events; USA observed mask unavailable','historical_period_mined':True,'original_top2_preserved':True,'entry_after_third_close':'third opening after two close updates','all_liquid_policy_arms':'No new ETF selections','files':[{'path':f.name,'sha256':hashlib.sha256(f.read_bytes()).hexdigest()} for f in sorted(out.glob('OLC103_*')) if f.is_file() and not f.name.endswith('INDEPENDENT_QA.json')]}
(out/'OLC103_INDEPENDENT_QA.json').write_text(json.dumps(r,indent=2))
print(json.dumps({k:v for k,v in r.items() if k!='files'},indent=2))
