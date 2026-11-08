#!/usr/bin/env python3
"""Independent OLC72 matched-family output checks and paired monthly bootstrap."""
from pathlib import Path
import pandas as pd,numpy as np,json
R=Path(__file__).parent;O=R/'results'
p=pd.read_csv(O/'OLC72_CONDITIONAL_FAMILY_MONTHLY.csv')
assert len(p)==1440 and not p.duplicated(['market','month','family','rep_seed']).any()
assert p[['native21','native42']].notna().all().all()
assert (p.changed==p.native_top2.ne(p.conditional_top2).astype(int)).all()
for (market,month),d in p.groupby(['market','month']):
    assert len(d)==12 and d.native21.nunique()==d.native42.nunique()==d.native_top2.nunique()==1,(market,month)
    assert np.allclose(100*(d.native21-d.matched21),d.original_minus_matched21_pp,rtol=0,atol=1e-11)
rows=[];rng=np.random.default_rng(72001)
for (market,family),d in p[p.year.between(2021,2024)].groupby(['market','family']):
    z=d.groupby('month',sort=True).original_minus_matched21_pp.mean().to_numpy();assert len(z)==48
    bs=np.empty(4000)
    for j in range(len(bs)):
        ix=((rng.integers(0,48,8)[:,None]+np.arange(6))%48).ravel()
        bs[j]=z[ix].mean()
    rows.append({'market':market,'family':family,'main_months':48,'two_seeds_per_month':True,'mean_delta_original_minus_matched21_pp':z.mean(),
        'ci95_low':np.quantile(bs,.025),'ci95_high':np.quantile(bs,.975)})
pd.DataFrame(rows).to_csv(O/'OLC72_CONDITIONAL_PAIRED_CI.csv',index=False)
qa={'n_month_family_replicates':len(p),'n_market_months':p.groupby(['market','month']).ngroups,
    'all_replicas_consistent_native_top2':True,'all_change_flags_verified':True,
    'matched_family_input_signatures':'six preregistered families, 2 seeds, 5 matched donors from other 45 raw rank distances',
    'bootstrap_resamples':4000,'bootstrap_month_level_not_individual_etf_or_seed':'correct','status':'PASS_RESEARCH_ONLY'}
(O/'OLC72_CONDITIONAL_INDEPENDENT_QA.json').write_text(json.dumps(qa,indent=2))
print(pd.DataFrame(rows).to_string(index=False,float_format=lambda x:f'{x:.3f}'));print('QA',qa)