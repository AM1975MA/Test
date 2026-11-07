#!/usr/bin/env python3
"""OLC63 exploratory post-result component interaction and concentration diagnostics.

Entirely descriptive. Inputs: fixed monthly scores for all 16 coalitions from OLC63;
no additional price inputs, fitting, model selection, or policy replay.
"""
from pathlib import Path
from itertools import combinations
from math import factorial
import numpy as np
import pandas as pd

ROOT=Path(__file__).resolve().parent
D=ROOT/'results'
F=pd.read_csv(D/'OLC63_MONTHLY_FACTORIAL.csv')
S=pd.read_csv(D/'OLC63_MONTHLY_SHAPLEY.csv')
L=pd.read_csv(D/'OLC63_LEAVE_ONE_OUT.csv')
ALL=[('R',1),('E',2),('X',4),('M',8)]

assert set(F['mask'].dropna().astype(int).unique())==set(range(16))
assert len(F[F['method']=='SUBSET'])+len(F[F['method']!='SUBSET'])==len(F)

out=[]
for (market,date),g in F.loc[F.method=='SUBSET'].groupby(['market','date'],sort=True):
    if len(g)!=16: raise RuntimeError(f'Incomplete {market} {date}: {len(g)}')
    vals={int(m):row for m,row in zip(g['mask'],g.to_dict('records'))}
    year=pd.Timestamp(date).year
    for h in ('mean21','mean42'):
        v={m:float(row[h]) for m,row in vals.items()}
        for a,b in combinations(ALL,2):
            ((na,ba),(nb,bb))=(a,b)
            others=[bit for _,bit in ALL if bit not in [ba,bb]]
            interaction=0
            for s in range(4):
                m=sum(others[k] for k in range(2) if s & (1<<k))
                d=v[m|ba|bb]-v[m|ba]-v[m|bb]+v[m]
                k=s.bit_count()
                interaction+=factorial(k)*factorial(2-k)/factorial(3)*d
            out.append(dict(market=market,date=date,year=year,horizon=h,pair=na+'×'+nb,shapley_interaction=interaction))

I=pd.DataFrame(out)
assert len(I)==len(F[(F.method=='SUBSET')&(F['mask']==15)])*2*6
I.to_csv(D/'OLC63_PAIRWISE_INTERACTIONS.csv',index=False)

rows=[]
for (market,horizon,pair),g in I.groupby(['market','horizon','pair']):
    for period,years in [('MAIN',range(2021,2025)),('LATE',[2025])]:
        s=g[g.year.isin(years)]
        if not len(s): continue
        a=s.shapley_interaction.to_numpy()
        rows.append(dict(market=market,period=period,horizon=horizon,pair=pair,months=len(s),mean_pp=100*a.mean(),positive_months=int((a>0).sum()),negative_months=int((a<0).sum()),median_pp=100*np.median(a),sum_pp=100*a.sum()))
pd.DataFrame(rows).sort_values(['period','horizon','market','mean_pp'],ascending=[True,True,True,False]).to_csv(D/'OLC63_INTERACTION_SUMMARY.csv',index=False)

# Annual variation in already frozen exact Shapley contribution (not policy outcomes).
annual=(S.assign(shapley_pp=S.shapley_return*100).groupby(['market','year','horizon','component'],as_index=False)
       .agg(nmonths=('date','nunique'),avg_pp=('shapley_pp','mean'),median_pp=('shapley_pp','median'),pos_months=('shapley_pp',lambda x:int((x>0).sum()))))
annual.to_csv(D/'OLC63_COMPONENT_ANNUAL.csv',index=False)

# Paired monthly ablation impact conditional on all other components active
main=L[L.period=='MAIN'].copy()
main['mean21_inclusion_pp']=100*main.mean21_inclusion
main['mean42_inclusion_pp']=100*main.mean42_inclusion
main['changed_share']=main.changed_months/main.nmonths
main[['market','component','nmonths','changed_months','changed_share','mean21_inclusion_pp','mean42_inclusion_pp','favor_inclusion_months','harm_inclusion_months','bootstrap_mean21_low','bootstrap_mean21_high']].to_csv(D/'OLC63_ABLATION_DECISION_TABLE.csv',index=False)

# component Shapley contributions: top 3 largest plus negative countereffect, in all fixed 48 MAIN months
con=[]
for (market,horizon,c),g in S[(S.year>=2021)&(S.year<=2024)].groupby(['market','horizon','component']):
    x=g.sort_values('shapley_return',ascending=False)
    total=x.shapley_return.sum()
    top3=x.head(3).shapley_return.sum()
    exclude_one=(total-x.shapley_return.iloc[0])/(len(x)-1)
    sum_positive=x.loc[x.shapley_return>0,'shapley_return'].sum()
    sum_negative=x.loc[x.shapley_return<0,'shapley_return'].sum()
    # top-3 / net can exceed 100%, so don't interpret as a share of total positive
    con.append(dict(market=market,horizon=horizon,component=c,months=len(x),total_pp=100*total,top3_sum_pp=100*top3,positive_contributions_sum_pp=100*sum_positive,negative_contributions_sum_pp=100*sum_negative,leave_largest_month_out_avg_pp=100*exclude_one,largest_month=x.date.iloc[0]))
pd.DataFrame(con).to_csv(D/'OLC63_COMPONENT_CONCENTRATION.csv',index=False)

# No-training/no-looking-ahead sanity check for appendonly diagnostic, subset arrays unchanged
import json, hashlib
manifest={
    'source':'OLC63_MONTHLY_FACTORIAL.csv and OLC63_MONTHLY_SHAPLEY.csv fixed original outputs',
    'purpose':'post-result exploratory interaction and contribution stability, not a new strategy',
    'no_new_learner':True,
    'no_new_market_prices':True,
    'no_optimized_weight_or_threshold':True,
    'number_monthly_coalitions':len(F[F.method=='SUBSET']),
    'number_interaction_rows':len(I),
    'nmarkets':len(F.market.unique()),
    'source_hashes':{p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in (D/'OLC63_MONTHLY_FACTORIAL.csv',D/'OLC63_MONTHLY_SHAPLEY.csv',D/'OLC63_LEAVE_ONE_OUT.csv')},
}
(D/'OLC63_DIAGNOSTIC_QA.json').write_text(json.dumps(manifest,indent=2)+'\n')
print(json.dumps(manifest,indent=2))