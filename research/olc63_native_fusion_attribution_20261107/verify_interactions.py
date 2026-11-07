#!/usr/bin/env python3
"""Independent Harsanyi-dividend check for OLC63 pairwise Shapley interaction.
Works on already frozen monthly 16-coalition table. No market data or model fits.
"""
from pathlib import Path
from itertools import combinations
import numpy as np
import pandas as pd
import json
root=Path(__file__).resolve().parent/'results'
f=pd.read_csv(root/'OLC63_MONTHLY_FACTORIAL.csv')
i=pd.read_csv(root/'OLC63_PAIRWISE_INTERACTIONS.csv')
s=pd.read_csv(root/'OLC63_MONTHLY_SHAPLEY.csv')
maxpair=maxshap=0.; n=0
labs=['R','E','X','M']; bits=[1,2,4,8]
for (market,date),g in f[f.method=='SUBSET'].groupby(['market','date']):
  assert len(g)==16
  for h in ['mean21','mean42']:
    v={int(r['mask']):r[h] for _,r in g.iterrows()}
    # independent inclusion-exclusion dividend algebra
    dividends={}
    for mask in range(16):
      x=0.
      for sub in range(16):
        if sub&mask==sub:
          x+=(-1)**((mask^sub).bit_count())*v[sub]
      dividends[mask]=x
    for a,b in combinations(range(4),2):
      target=i[(i.market==market)&(i.date==date)&(i.horizon==h)&(i.pair==labs[a]+'×'+labs[b])]
      assert len(target)==1
      mask=bits[a]|bits[b]
      x=sum(dividends[t]/(t.bit_count()-1) for t in range(16) if t&mask==mask)
      maxpair=max(maxpair,abs(x-target.shapley_interaction.iloc[0]));n+=1
    for a in range(4):
      target=s[(s.market==market)&(s.date==date)&(s.horizon==h)&(s.component==labs[a])]
      assert len(target)==1
      x=sum(dividends[t]/t.bit_count() for t in range(1,16) if t&bits[a])
      maxshap=max(maxshap,abs(x-target.shapley_return.iloc[0]))
    assert abs(v[15]-v[0]-sum(dividends[t] for t in range(1,16)))<1e-12
assert n==1416
assert maxpair<1e-12 and maxshap<1e-12
q={'source':'OLC63 frozen 16-coalition output','num_interactions_checked':n,'max_pair_abs_error':maxpair,'max_shapley_abs_error':maxshap,'method':'independent Harsanyi inclusion-exclusion decomposition','status':'PASS'}
(root/'OLC63_INTERACTIONS_INDEPENDENT_QA.json').write_text(json.dumps(q,indent=2)+'\n')
print(json.dumps(q,indent=2))