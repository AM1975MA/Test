#!/usr/bin/env python3
"""Diagnostic analysis using only already computed OLC99 A/B outputs."""
from pathlib import Path
import json
import numpy as np,pandas as pd
from scipy.stats import spearmanr
R=Path(__file__).resolve().parent;P=R/'results'
static=pd.read_csv(P/'OLC99_STATIC_TOP2_OUTCOMES.csv')
rank=pd.read_csv(P/'OLC99_TOP10_ECONOMIC_PANEL.csv.gz')
alloc=pd.read_csv(P/'OLC99_ALLOCATOR_WEIGHTS.csv')
cf=pd.read_csv(P/'OLC99_MATCHED_STATE_COUNTERFACTUALS.csv')
selb=pd.read_csv(P/'OLC99B_SELECTIONS.csv')
features=pd.read_csv(P/'OLC99B_TOP10_PREDICTIONS.csv')
ann=pd.read_csv(P/'OLC99_ANNUAL.csv');annb=pd.read_csv(P/'OLC99B_ANNUAL.csv')
staticp=static.pivot_table(index=['market','j','signal_date'],columns='arm',values='static_top2_logr',aggfunc='first').reset_index()
staticp['e1_minus_original_logpp']=100*(staticp['E1_ANCHORED_20']-staticp['E0_CONTEXT'])
staticp['e2_minus_original_logpp']=100*(staticp['E2_ANCHORED_35']-staticp['E0_CONTEXT'])
staticp['year']=staticp.signal_date.str[:4]
base=static[static.arm=='E0_CONTEXT'][['market','j','ticker1','ticker2']]
E1=static[static.arm=='E1_ANCHORED_20'][['market','j','ticker1','ticker2']]
changed=base.merge(E1,on=['market','j'],suffixes=('_base','_e1'))
changed['pair_changed']=(changed.ticker1_base!=changed.ticker1_e1)|(changed.ticker2_base!=changed.ticker2_e1)
staticp=staticp.merge(changed[['market','j','pair_changed','ticker1_base','ticker2_base','ticker1_e1','ticker2_e1']],on=['market','j'])
staticp.to_csv(P/'OLC99_FOR_FORENSIC_MONTHLY_SELECTION_DELTA.csv',index=False)
for_rows=[]
for market,g in staticp.groupby('market'):
 u=g[g.pair_changed & g.e1_minus_original_logpp.notna()]
 l=g[g.e1_minus_original_logpp.notna()]
 for_rows.append(dict(market=market,valid_months=len(l),changed_months=len(u),
  favorable_change_n=int((u.e1_minus_original_logpp>0).sum()),
  damaging_change_n=int((u.e1_minus_original_logpp<0).sum()),
  average_logpp_all=float(l.e1_minus_original_logpp.mean()),
  mean_logpp_changed=float(u.e1_minus_original_logpp.mean()) if len(u) else 0.,
  worst_three_logpp=float(u.nsmallest(3,'e1_minus_original_logpp').e1_minus_original_logpp.sum())))
 # Score ranking next leaders within Top10
 for label in ('E0_CONTEXT','E1_ANCHORED_20','E2_ANCHORED_35'):
  sel=static[(static.market==market)&(static.arm==label)]
  precision=[]
  for row in sel.itertuples(index=False):
   g=rank[(rank.market==market)&(rank.event_j==row.j)]
   if not g.future_logr.notna().all():continue
   rank_true=set(g.sort_values('future_logr',ascending=False).head(2).ticker)
   precision.append(int(row.ticker1 in rank_true)+int(row.ticker2 in rank_true))
  for_rows.append({'market':market,'arm':label,'precision_top2_within_top10':float(np.mean(precision))/2.,
    'n_events':len(precision),'avg_selected_true_leaders':float(np.mean(precision))})
 # Allocators forecasts native spread vs prior-only mean: labels matched own policy state.
 for policy in ('PRIOR','ML'):
  w=alloc[(alloc.market==market)&(alloc.policy==policy)]
  c=cf[(cf.market==market)&(cf.policy==policy)]
  j=w.merge(c,on=['market','policy','event_j','signal_date'],validate='one_to_one')
  z=j[j.n_mature>=24].copy()
  if len(z):
   sgn=(np.sign(z.pred_spread_logbp)==np.sign(z.spread_100_vs_0_logbp)).mean()
   mae=np.abs(z.pred_spread_logbp-z.spread_100_vs_0_logbp).mean()
   sp=spearmanr(z.pred_spread_logbp,z.spread_100_vs_0_logbp).statistic
  else:sgn=mae=sp=np.nan
  for_rows.append(dict(market=market,arm='ALLOC_'+policy,
    n_evaluated=len(z),sign_accuracy=float(sgn),MAE_logbp=float(mae),Spearman=float(sp)))
# Annual comparison of strategy variants
sel=ann[(ann.fee==.001)&(ann.timing=='DELAY3')&(ann.arm.isin(['E0_CONTEXT','E1_ANCHORED_20','E1_ALLOC_PRIOR','E1_ALLOC_ML']))]
bsel=annb[(annb.fee==.001)&(annb.timing=='DELAY3')].copy()
pd.concat([sel,bsel],ignore_index=True).to_csv(P/'OLC99_ANNUAL_COMPARISON.csv',index=False)
pd.DataFrame(for_rows).to_csv(P/'OLC99_FORENSIC_SUMMARY.csv',index=False)
print(pd.DataFrame(for_rows).to_string(index=False))
print('\nLargest E1 errors\n',staticp[staticp.pair_changed].sort_values('e1_minus_original_logpp').head(12).to_string(index=False))