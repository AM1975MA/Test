#!/usr/bin/env python3
"""Independently reconstruct OLC71D monthly payoff and summary from OLC71 original OOF."""
from pathlib import Path
import json
import numpy as np,pandas as pd
R=Path(__file__).resolve().parent/'results'
d=pd.read_csv(R/'OLC71D_NATIVE_FAMILY_MONTHLY.csv')
s=pd.read_csv(R/'OLC71D_NATIVE_FAMILY_SUMMARY.csv')
a=pd.read_csv(R/'OLC71_OOF_PREDICTIONS.csv.gz',parse_dates=['signal_date'])
a=a[a.market=='EU'].copy();a['month']=a.signal_date.dt.strftime('%Y-%m')
orig={};lookup={}
for month,g in a.groupby('month'):
 g=g[g.fwd_ret_21.notna() & g.fwd_ret_42.notna()].sort_values(['ORIG_FUSION','ticker'],ascending=[False,True])
 orig[month]=g.ticker.head(2).tolist()
 lookup[month]=dict(zip(g.ticker,zip(g.fwd_ret_21,g.fwd_ret_42)))
assert len(d)==5520 and d.family.nunique()==46 and set(d.rep_seed)=={71101,71102}
assert len(d[d.year.between(2021,2024)])==48*46*2
assert len(d[d.year.eq(2025)])==12*46*2
assert len(s)==46*2*2
assert d.valid_outcomes.all()
errs=[];rows=0
for rec in d.itertuples(index=False):
 month=rec.month
 assert rec.original_top2.split(';')==orig[month],(month,rec.original_top2,orig[month])
 for tickers,target21,target42 in [(rec.original_top2.split(';'),rec.original_payoff21,rec.original_payoff42),
                                    (rec.permuted_top2.split(';'),rec.perturbed_payoff21,rec.perturbed_payoff42)]:
  v=np.array([lookup[month][t] for t in tickers],float)
  errs.extend([abs(np.mean(v[:,0])-target21),abs(np.mean(v[:,1])-target42)])
 rows+=1
assert max(errs)<1e-12,max(errs)
for rec in s.itertuples(index=False):
 x=d[(d.family==rec.family)&(d.rep_seed==rec.rep_seed)&
     (d.year.between(2021,2024) if rec.period=='MAIN_2021_2024' else d.year.eq(2025))]
 assert len(x)==rec.n_months
 assert abs(x.top2_changed.mean()-rec.top2_change_rate)<1e-12
 assert abs(x.mean_abs_return_rank_move.mean()-rec.mean_abs_return_rank_move)<1e-12
 assert abs(x.payoff21_loss_if_scrambled_pp.mean()-rec.delta_original_minus_scramble_payoff21_pp)<1e-12
res={'passed':True,'rows':rows,'n_families':46,'n_seeds':2,'n_years':5,'n_months':60,
    'max_return_recompute_abs':max(errs),'monthly_summary_tieout':True,
    'original_fusion_top2_parity':True,
    'limitations':'EU-only, off-manifold permutation of cross-section, no native context/V6/stop, historical 2021-25 already mined'}
(R/'OLC71D_NATIVE_FAMILY_INDEPENDENT_QA.json').write_text(json.dumps(res,indent=2,ensure_ascii=False)+'\n')
print(json.dumps(res,indent=2,ensure_ascii=False))