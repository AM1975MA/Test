#!/usr/bin/env python3
"""Original versus family-balanced XGB family gain concentration, descriptive only."""
from pathlib import Path
import pandas as pd,numpy as np,json,xgboost as xgb
import run_olc72 as c
R=Path(__file__).parent;O=R/'results'
def main():
 z=c.init();rows=[]
 for market in ('EU','USA'):
  for year in range(2021,2026):
   f=c.audit(z,market,year)['return_features'];fam=[v.removesuffix('_pct').removesuffix('_dev') for v in f]
   assert len(set(fam))==46
   for variant in ('ORIGINAL','FAMILY_BALANCED'):
    scores={k:0.0 for k in set(fam)}
    for seed in c.SEEDS:
     b=c.orig_model(z,market,year,seed) if variant=='ORIGINAL' else xgb.Booster(model_file=str(R/'models'/market/str(year)/f'FAMILY_{seed}.ubj'))
     imp=b.get_score(importance_type='total_gain')
     for key,v in imp.items():
      j=int(key[1:]) if key.startswith('f') else f.index(key)
      scores[fam[j]]+=float(v)
    tot=sum(scores.values()); assert tot>0
    p=np.array(list(scores.values()))/tot
    rows.append({'market':market,'year':year,'variant':variant,'n_families_used':int((p>0).sum()),
                 'effective_families_HHI':float(1/np.sum(p*p)),'entropy_family_count':float(np.exp(-np.sum(p[p>0]*np.log(p[p>0])))),
                 'top5_family_gain_share':float(np.sort(p)[-5:].sum())})
 d=pd.DataFrame(rows);d.to_csv(O/'OLC72_MODEL_USAGE.csv',index=False)
 mo=pd.read_csv(O/'OLC72_MONTHLY.csv')
 annual=mo.groupby(['market','year','method']).agg(months=('month','count'),ret21=('p21','mean'),ret42=('p42','mean'),persistent=('persistent','mean')).reset_index()
 annual[['ret21','ret42']]*=100
 annual.to_csv(O/'OLC72_ANNUAL.csv',index=False)
 both=mo.pivot(index=['market','month','year'],columns='method',values='top2').reset_index()
 both['different']=both.FAMILY_FUSION.ne(both.ORIGINAL_FUSION)
 changes=both.groupby(['market','year']).different.agg(['mean','sum','count']).reset_index()
 changes.to_csv(O/'OLC72_DECISION_CHANGES.csv',index=False)
 print(d.groupby(['market','variant'])[['effective_families_HHI','top5_family_gain_share']].mean().to_string())
 print('\nAnnual return performance:');print(annual.to_string(index=False,float_format=lambda x:f'{x:.3f}'))
 print('\nDecision change rate:');print(changes.to_string(index=False))
if __name__=='__main__':main()