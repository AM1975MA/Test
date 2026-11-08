#!/usr/bin/env python3
"""OLC73 independent tabulations and block-paired descriptive uncertainty; no optimization."""
from pathlib import Path
import pandas as pd
import numpy as np
import json,hashlib
BASE=Path(__file__).resolve().parent
OUT=BASE/'results'
sc=pd.read_csv(OUT/'OLC73_SCORECARD.csv')
an=pd.read_csv(OUT/'OLC73_ANNUAL.csv')
dy=pd.read_csv(OUT/'OLC73_DAILY_LOGRET.csv.gz',parse_dates=['date'])
orig=['HALF','MINVAR63_CAP25']
policies=['HALF','TOP1_65','TOP1_75','TOP2_65','TOP2_75','INVOL63_CAP25','MOM63_LEADER65','MINVAR63_CAP25']
assert len(dy.key.unique())==64
# Build monthly paired 6 month circular bootstrap on consistent sessions per-market.
monthly=(dy.assign(month=dy.date.dt.to_period('M').astype(str))
          .groupby(['market','timing','fee','policy','month'],as_index=False)
          .agg(log_return=('logr','sum'),n=('logr','size')))
monthly.to_csv(OUT/'OLC73_MONTHLY_LOGRET.csv',index=False)
rec=[];B=4000;rng=np.random.default_rng(73008)
for market in ['EU','USA']:
 for timing in ['IMMEDIATE','DELAY3']:
  for fee in [.001,.003]:
   part=monthly[(monthly.market==market)&(monthly.timing==timing)&(monthly.fee==fee)]
   ctrl=part[part.policy=='HALF'].set_index('month').sort_index()
   for pol in policies[1:]:
    comp=part[part.policy==pol].set_index('month').sort_index()
    assert np.array_equal(ctrl.index,comp.index)
    assert np.array_equal(ctrl.n,comp.n)
    for period,selector in [('MAIN2021_2024', (ctrl.index>='2021-01')&(ctrl.index<='2025-01')),
                            ('FULL',np.ones(len(ctrl),bool)),
                            ('LATE2024_2026',(ctrl.index>='2024-01'))]:
     d=(comp.log_return.to_numpy()-ctrl.log_return.to_numpy())[selector]
     n=ctrl.n.to_numpy()[selector]
     k=len(d)
     bootstrap=np.empty(B)
     for z in range(B):
      blocks=rng.integers(0,k,size=int(np.ceil(k/6)))
      idx=(blocks[:,None]+np.arange(6)[None,:])%k
      choose=idx.ravel()[:k]
      bootstrap[z]=252*d[choose].sum()/n[choose].sum()
     lb,ub=np.percentile(bootstrap,[2.5,97.5]);point=252*d.sum()/n.sum()
     rec.append(dict(market=market,timing=timing,fee=fee,policy=pol,period=period,
             diff_annual_log=point,ci_low=lb,ci_high=ub,months=k,positive_month_fraction=float(np.mean(d>0)),
             net_log_total=float(d.sum()),largest3_positive=float(np.sort(d)[-3:].sum()),largest3_negative=float(np.sort(d)[:3].sum())))
res=pd.DataFrame(rec);res.to_csv(OUT/'OLC73_PAIRED_BLOCK6.csv',index=False)
# Fixed gate against baseline of SAME TIMING, fee .001.
gate=[]
for timing in ['IMMEDIATE','DELAY3']:
 for policy in policies:
  allpass=True;fields={}
  for market in ['EU','USA']:
   a=sc[(sc.market==market)&(sc.timing==timing)&(sc.fee==.001)&(sc.policy=='HALF')].set_index('period')
   b=sc[(sc.market==market)&(sc.timing==timing)&(sc.fee==.001)&(sc.policy==policy)].set_index('period')
   main_d=b.loc['ACTIVE2021_2024','cagr']-a.loc['ACTIVE2021_2024','cagr']
   full_d=b.loc['FULL','cagr']-a.loc['FULL','cagr']
   dd_diff=b.loc['FULL','maxdd']-a.loc['FULL','maxdd']
   fields.update({f'{market}_main_delta':main_d,f'{market}_full_delta':full_d,f'{market}_dd_delta':dd_diff})
   if main_d<-1e-10 or full_d<1e-10 or dd_diff<-.03:allpass=False
  gate.append({'timing':timing,'policy':policy,'gate_pass_vs_same_timing_HALF':(None if policy=='HALF' else allpass),**fields})
pd.DataFrame(gate).to_csv(OUT/'OLC73_GATE.csv',index=False)
# Independent day-return reconstruction from daily table, not from engine states.
checks=[]
for x in sc.itertuples():
 s=dy[dy.key==x.key]
 sub=s[(s.date>=pd.Timestamp(x.first_valuation))&(s.date<=pd.Timestamp(x.last_valuation))]
 vals=sub.logr.to_numpy()
 assert len(vals)==x.n
 e=np.exp(np.cumsum(vals))
 c=np.expm1(vals.sum()/len(vals)*252)
 d=np.min(e/np.maximum.accumulate(np.r_[1.,e])[1:]-1)
 assert abs(c-x.cagr)<1e-11 and abs(d-x.maxdd)<1e-11
 checks.append([x.key,x.period,len(vals),abs(c-x.cagr),abs(d-x.maxdd)])
qa=json.loads((OUT/'OLC73_QA.json').read_text());qa['verified_scorecard_period_rows']=len(checks)
qa['verified_max_abs_cagr_diff']=float(np.max(np.asarray(checks)[:,3].astype(float)))
qa['verified_max_abs_dd_diff']=float(np.max(np.asarray(checks)[:,4].astype(float)))
qa['bootstrap_seed']=73008;qa['bootstrap_resamples']=B
qa['unverified_USA_observation_flags']='USA original q lacks observed; used finite valid Close fallback exactly as OLC56 prior code; not verified true market-observation mask'
qa['new_policy_promoted']=False
(OUT/'OLC73_INDEPENDENT_QA.json').write_text(json.dumps(qa,indent=2,ensure_ascii=False))
# 2024-2026 rank flip diagnostic with clear causal caveats.
piv=an[(an.fee==.001)&(an.year.isin([2024,2025,2026]))].pivot_table(index=['market','timing','year'],columns='policy',values='return').reset_index()
piv['top1_75_minus_top2_75_pp']=(piv.TOP1_75-piv.TOP2_75)*100
piv['mom63_minus_half_pp']=(piv.MOM63_LEADER65-piv.HALF)*100
piv.to_csv(OUT/'OLC73_RANK_FLIPS_2024_2026.csv',index=False)
print('independent verification:',qa['verified_scorecard_period_rows'],'periods, max_cagr_diff',qa['verified_max_abs_cagr_diff'])
print('eligibility gate:');print(pd.DataFrame(gate)[['timing','policy','gate_pass_vs_same_timing_HALF']].to_string(index=False))
print('rank flips:');print(piv[['market','timing','year','top1_75_minus_top2_75_pp','mom63_minus_half_pp']].round(2).to_string(index=False))
print('bootstrap main vs HALF:');print(res[(res.fee==.001)&(res.period=='MAIN2021_2024')&res.policy.isin(['TOP1_75','TOP2_75','MOM63_LEADER65','MINVAR63_CAP25'])][['market','timing','policy','diff_annual_log','ci_low','ci_high']].round(4).to_string(index=False))