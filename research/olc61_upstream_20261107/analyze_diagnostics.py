#!/usr/bin/env python3
"""OLC61 post-result diagnostics (NOT candidate generation or parameter search).
Emphasizes top-tail economics vs generic cross-sectional discrimination.
"""
from __future__ import annotations
import argparse,json
from pathlib import Path
import numpy as np
import pandas as pd
from scipy.stats import spearmanr
from sklearn.metrics import ndcg_score

METHODS={'B0_NATIVE':'ORIGINAL_CURRENT','B0_FUSION_CONTEXT':'ORIGINAL_FUSION',
        'ECON21':'pred_ECON21','STAY2':'pred_STAY2','ECO_STAY':'pred_ECO_STAY'}

def run(root):
 root=Path(root)
 panel=pd.read_csv(root/'OLC61_PREDICTIONS.csv.gz')
 sel=pd.read_csv(root/'OLC61_TOP2_SELECTIONS.csv')
 mm=pd.read_csv(root/'OLC61_MONTHLY_METRICS.csv')
 checks=[];ranks=[];events=[]
 for (m,date),g in panel.groupby(['market','signal_date'],sort=True):
  assert len(g)>=50 and not g.ticker.duplicated().any()
  assert g[list(METHODS.values())].notna().all().all()
  year=int(date[:4])
  if g.g1_bp.notna().all() and g.g2_bp.notna().all():
   # Compute gains with fixed boundaries identically to preregistered target.
   label=np.digitize(g.g1_bp.to_numpy(float),[-300,-100,0,100,300],right=True)
   for method,col in METHODS.items():
    p=g[col].to_numpy(dtype=float)
    s=spearmanr(p,g.g1_bp.to_numpy(dtype=float)).statistic
    n=ndcg_score(label.reshape(1,-1),p.reshape(1,-1),k=2)
    ranks.append(dict(market=m,date=date,year=year,method=method,ndcg2_g1=float(n),ic_g1=float(s)))
  # Mean fraction of its Top2 present in baseline FUSION Top10 (descriptive, no future)
  order=g.nlargest(10,'ORIGINAL_FUSION').ticker.to_list()
  for method in METHODS:
   z=sel[(sel.market==m)&(sel.signal_date==date)&(sel.method==method)]
   assert abs(z.weight.sum()-1)<1e-12
   weight_in_fusion_top10=z[z.ticker.isin(order)].weight.sum()
   events.append(dict(market=m,date=date,year=year,method=method,fusion10_overlap=float(weight_in_fusion_top10)))
 rank=pd.DataFrame(ranks);over=pd.DataFrame(events)
 rank.to_csv(root/'OLC61_RANK_QUALITY.csv',index=False)
 over.to_csv(root/'OLC61_OVERLAP_FUSION_TOP10.csv',index=False)
 summary=rank[rank.year.between(2021,2024)].groupby(['market','method'])[['ndcg2_g1','ic_g1']].mean().reset_index()
 ov=over[over.year.between(2021,2024)].groupby(['market','method'])['fusion10_overlap'].mean().reset_index()
 summary=summary.merge(ov,on=['market','method'])
 summary.to_csv(root/'OLC61_SELECTION_DIAGNOSTICS_SUMMARY.csv',index=False)
 for m in ['EU','USA']:
  allm=mm[(mm.market==m)&mm.year.between(2021,2024)]
  wide=allm.pivot(index='signal_date',columns='method',values='fwd_ret_21')
  assert len(wide)==48
  for challenger in ['ECON21','STAY2','ECO_STAY']:
   x=(wide[challenger]-wide['B0_FUSION_CONTEXT'])*100
   checks.append(dict(market=m,method=challenger,win_months=int((x>0).sum()),loss_months=int((x<0).sum()),tie_months=int((x==0).sum()),mean_pp=float(x.mean()),median_pp=float(x.median()),
    total_diff_pp=float(x.sum()),top_three_positive_months_pct_of_positive_sum=float(x[x>0].nlargest(3).sum()/x[x>0].sum()) if (x>0).any() else float('nan')))
  for k in ['B0_NATIVE','B0_FUSION_CONTEXT','ECON21','STAY2','ECO_STAY']:
   row=summary[(summary.market==m)&(summary.method==k)].iloc[0]
   print(m,k,'ndcg2_g1',round(row.ndcg2_g1,4),'ic_g1',round(row.ic_g1,4),'overlap fusionTop10',round(row.fusion10_overlap,4))
 res=pd.DataFrame(checks);res.to_csv(root/'OLC61_PAIRED_MONTHLY_DIAGNOSTICS.csv',index=False)
 print(res.to_string(index=False,float_format=lambda x:f'{x:.4f}'))
 print('saved. no new candidate fit, no strategy backtest')

if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--results',required=True);a=p.parse_args();run(a.results)