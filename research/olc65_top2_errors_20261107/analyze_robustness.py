#!/usr/bin/env python3
"""Post-result robustness check, not a search for trading rules.
Block bootstrap on share of the retrospective opportunity gap due to ordering.
"""
from pathlib import Path
import pandas as pd, numpy as np
p=Path(__file__).resolve().parent/'results'
m=pd.read_csv(p/'OLC65_MONTHLY_GAPS.csv')
rows=[]
for market in ('EU','USA'):
 for period in ('MAIN','LATE'):
  s=m[(m.market==market)&(m.period==period)&(m.status=='VALID')].sort_values('date').reset_index(drop=True)
  n=len(s);rng=np.random.default_rng(65002);res=[]
  B=5000 if period=='MAIN' else 0
  for _ in range(B):
   idx=[]
   while len(idx)<n:
    st=int(rng.integers(n));idx.extend((st+k)%n for k in range(6))
   z=s.iloc[idx[:n]];res.append(z.ordering_gap21.sum()/z.total_gap21.sum())
  rows.append(dict(market=market,period=period,nmonths=n,
      ordering_share=float(s.ordering_gap21.sum()/s.total_gap21.sum()),
      bootstrap_ci_low=float(np.quantile(res,.025)) if res else float('nan'),
      bootstrap_ci_high=float(np.quantile(res,.975)) if res else float('nan'),
      months_ordering_gap_gt_discovery=int((s.ordering_gap21>s.discovery_gap21).sum()),
      years_ordering_gap_gt_discovery=int(sum((g.ordering_gap21.mean()>g.discovery_gap21.mean()) for _,g in s.groupby('year')))))
r=pd.DataFrame(rows);r.to_csv(p/'OLC65_ORDERING_SHARE_BLOCK_BOOTSTRAP.csv',index=False)
print(r.to_string(index=False))