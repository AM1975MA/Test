#!/usr/bin/env python3
"""Cross-check OLC64 by an independent per-row join and pandas rank correlation."""
from pathlib import Path
import numpy as np, pandas as pd, hashlib, json
R=Path(__file__).resolve().parent
P=R.parent/'OLC63_Fusion_Attribution_20261107'/'results'
T=pd.read_csv(R/'results/OLC64_MONTHLY_DIAGNOSTIC.csv')
Q=pd.read_csv(R/'results/OLC64_ASSOCIATIONS.csv')
F=pd.read_csv(P/'OLC63_MONTHLY_FACTORIAL.csv');C=pd.read_csv(P/'OLC63_MONTHLY_CORRELATIONS.csv')
assert F.duplicated(['market','date','mask']).sum()==0
F=F[F.method=='SUBSET'];C=C.set_index(['market','date','pair'])
max_e=0.;n=0
for row in T.itertuples(index=False):
    vals=F[(F.market==row.market)&(F.date==row.date)].set_index('mask')
    assert len(vals)==16
    pcol='RETURN__ORIGINAL_CURRENT' if row.hypothesis=='H1_RETURN_VS_ET' else 'ER__XR'
    d=1-float(C.loc[(row.market,row.date,pcol),'spearman'])
    y=(vals.loc[13.,row.horizon]-vals.loc[14.,row.horizon]) if row.hypothesis=='H1_RETURN_VS_ET' else (vals.loc[15.,row.horizon]-vals.loc[11.,row.horizon])
    max_e=max(max_e,abs(row.disagreement-d),abs(row.future_marginal_utility_pp-100*y));n+=1
assert n==472 and max_e<1e-11
maxrho=0.
for group,sub in T.groupby(['market','period','hypothesis','horizon']):
    a=sub.disagreement.rank().to_numpy()
    b=sub.future_marginal_utility_pp.rank().to_numpy()
    rho=np.corrcoef(a,b)[0,1]
    q=Q[(Q.market==group[0])&(Q.period==group[1])&(Q.hypothesis==group[2])&(Q.horizon==group[3])]
    assert len(q)==1
    maxrho=max(maxrho,abs(rho-q.spearman.iloc[0]))
assert maxrho<1e-13
qa={'status':'PASS','rows':n,'max_row_error':max_e,'max_spearman_abs_error':maxrho,
    'method':'per-row mask/market/date join and independent Pearson-on-ranks Spearman computation',
    'no_model_fit':True,'production_unchanged':True}
(R/'results/OLC64_INDEPENDENT_QA.json').write_text(json.dumps(qa,indent=2)+'\n');print(json.dumps(qa,indent=2))