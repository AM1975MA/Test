"""Common economic endpoints for all ranking formulas; no self-target victory."""
from __future__ import annotations
import numpy as np,pandas as pd,json
from common import ROOT,P11,MARKETS,SEEDS,VARIANTS,readcsv
from ranking_core import utility
from layer_metrics import ranking_metrics,opportunity_metrics,topk_weights
from recovery_core import atomic_json
PERIODS=('PRE2025','Y2025','Y2026_PARTIAL','ALL_ACTIVE')
STAGES=('CURRENT','MAPPED','SMOOTH','FUSION')

def period_ok(date,exitdate,period):
 if pd.isna(exitdate):return False
 if period=='PRE2025':return pd.Timestamp('2021-01-01')<=date<pd.Timestamp('2025-01-01') and exitdate<pd.Timestamp('2025-01-01')
 if period=='Y2025':return date.year==2025 and exitdate<pd.Timestamp('2026-01-01')
 if period=='Y2026_PARTIAL':return date.year==2026 and exitdate<=pd.Timestamp('2026-07-01')
 if period=='ALL_ACTIVE':return date>=pd.Timestamp('2021-01-01') and exitdate<=pd.Timestamp('2026-07-01')
 raise ValueError('Unknown period')

def main():
 rows=[];ty=[];decisions=[];excluded=[];mapchecks=[]
 for market in MARKETS:
  labels=readcsv(P11/f'inputs/{market}_LAYER_LABELS.csv.gz').drop(columns=['source_date'])
  for seed in ('MEAN3',*SEEDS):
   f=readcsv(ROOT/f'results/{market}_{seed}_SCORES.csv.gz').merge(labels,on=['signal_date','ticker'],how='left',validate='one_to_one')
   for date,g0 in f.groupby('signal_date'):
    valid=np.isfinite(g0.ORIGINAL_CURRENT)
    for v in VARIANTS:assert np.array_equal(valid,np.isfinite(g0[v+'_CURRENT'])),(market,seed,v,date)
    g=g0[valid];rr=g[['fwd_ret_21','fwd_ret_42','fwd_ret_63']].to_numpy(float)
    full=len(g)>=20 and np.isfinite(rr).all() and g.exit_date_63.notna().all() and np.isfinite(g.TARGET).all()
    if not full:
     if seed=='MEAN3':excluded.append(dict(market=market,date=date,rows=len(g),reason='incomplete_future_group_not_removed_from_predictions'))
     continue
    ex=g.exit_date_63.max();periods=[p for p in PERIODS if period_ok(date,ex,p)]
    if not periods:continue
    endpoints={'U42':utility(rr),'0_21':rr[:,0],'0_42':rr[:,1],'0_63':rr[:,2],
     '21_42':(1+rr[:,1])/(1+rr[:,0])-1,'42_63':(1+rr[:,2])/(1+rr[:,1])-1}
    for v in VARIANTS:
     np.testing.assert_array_equal(topk_weights(g[v+'_CURRENT']),topk_weights(g[v+'_MAPPED']))
     for stage in STAGES:
      pred=g[v+'_'+stage].to_numpy();info=dict(market=market,seed=str(seed),variant=v,stage=stage,date=date,last_exit=ex,n=len(g))
      target_metrics=ranking_metrics(g.TARGET.to_numpy(),pred)
      for p in periods:ty.append(dict(**info,period=p,**target_metrics))
      for horizon,r in endpoints.items():
       stats=opportunity_metrics(r,pred)
       for p in periods:rows.append(dict(**info,period=p,horizon=horizon,**stats))
      if seed=='MEAN3' and stage in ('CURRENT','FUSION'):
       ww=topk_weights(pred)
       for k in np.flatnonzero(ww):
        a=g.iloc[k];decisions.append(dict(market=market,variant=v,stage=stage,date=date,ticker=a.ticker,weight=ww[k],score=pred[k],utility=endpoints['U42'][k],fwd21=rr[k,0],fwd42=rr[k,1],fwd63=rr[k,2]))
   mapchecks.append(dict(market=market,seed=str(seed),rank_preserved=True));print('EVALUATED',market,seed,flush=True)
 o=pd.DataFrame(rows);t=pd.DataFrame(ty);ks=['market','seed','variant','stage','period']
 o.to_csv(ROOT/'results/OPPORTUNITY_MONTHS.csv.gz',index=False,compression='gzip');t.to_csv(ROOT/'results/TARGET_MONTHS.csv.gz',index=False,compression='gzip')
 om=['top2_return','top2_excess','top2_regret','selected_negative_return','bottom_quintile_fraction','top5_capture']
 tm=['ndcg2','ndcg5','ic','selected_target','target_regret','target_top_quintile_precision','target_bottom_quintile_fraction']
 o.groupby(ks+['horizon']).agg(months=('date','nunique'),**{k:(k,'mean') for k in om}).reset_index().to_csv(ROOT/'results/OPPORTUNITY_SUMMARY.csv',index=False)
 t.groupby(ks).agg(months=('date','nunique'),**{k:(k,'mean') for k in tm}).reset_index().to_csv(ROOT/'results/TARGET_SUMMARY.csv',index=False)
 pd.DataFrame(decisions).to_csv(ROOT/'results/TOP2_DECISIONS.csv.gz',index=False,compression='gzip')
 pd.DataFrame(excluded).to_csv(ROOT/'results/EXCLUSIONS.csv',index=False)
 atomic_json(ROOT/'results/EVALUATION_COMPLETE.json',dict(opportunity_rows=len(o),target_rows=len(t),mapping_rank_checks=mapchecks,utility_is_not_portfolio_return=True))
 print('EVALUATION_COMPLETE',len(o),len(t),flush=True)
if __name__=='__main__':main()
