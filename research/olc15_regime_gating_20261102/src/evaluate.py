"""Common endpoints for the ACTUAL mixed selections, not averaged NAVs."""
from io_utils import ROOT,MARKETS,VARIANTS,readcsv,dump
from prepare import utility
from layer_metrics import opportunity_metrics,ranking_metrics,topk_weights
import numpy as np,pandas as pd

def periods_for(date,available):
 if pd.isna(available) or available>pd.Timestamp('2026-07-01'):return []
 out=[]
 if pd.Timestamp('2023-01-01')<=date<pd.Timestamp('2025-01-01'):
  out.append('ADAPTIVE2023_2024_ALL_SIGNALS')
  if available<pd.Timestamp('2025-01-01'):out.append('ADAPTIVE2023_2024')
 if date>=pd.Timestamp('2023-01-01'):out.append('ADAPTIVE_FULL')
 if pd.Timestamp('2021-01-01')<=date<pd.Timestamp('2025-01-01') and available<pd.Timestamp('2025-01-01'):out.append('PRE2025')
 if date.year==2025 and available<pd.Timestamp('2026-01-01'):out.append('Y2025')
 if date.year==2026:out.append('Y2026_PARTIAL')
 return out

def main():
 rows=[];target=[];choices=[];excluded=[]
 for m in MARKETS:
  sc=readcsv(ROOT/f'results/{m}_SCORES.csv.gz');f=readcsv(ROOT/f'inputs/{m}_FITTING_FRAME.csv.gz');cols=[c for c in f if c.startswith(('fwd_ret_','exit_date_'))]+['TARGET','signal_date','ticker']
  all_=sc.merge(f[cols],on=['signal_date','ticker'],how='left',validate='one_to_one')
  for d,g in all_.groupby('signal_date'):
   g=g[np.isfinite(g.ORIGINAL_CURRENT)];rr=g[['fwd_ret_21','fwd_ret_42','fwd_ret_63']].to_numpy(float)
   if not(len(g)>=20 and np.isfinite(rr).all() and (rr>-1).all() and g.exit_date_63.notna().all()):excluded.append(dict(market=m,date=d,reason='incomplete future group; no live candidate dropped'));continue
   av=g.exit_date_63.max();periods=periods_for(d,av)
   if not periods:continue
   endpoints={'U42':utility(rr),'0_21':rr[:,0],'0_42':rr[:,1],'0_63':rr[:,2],'21_42':(1+rr[:,1])/(1+rr[:,0])-1,'42_63':(1+rr[:,2])/(1+rr[:,1])-1}
   for v in VARIANTS:
    for stage in ['CURRENT','SMOOTH','FUSION']:
     pred=g[v+'_'+stage].to_numpy();assert np.isfinite(pred).all()
     info=dict(market=m,date=d,available=av,variant=v,stage=stage,n=len(g))
     for h,u in endpoints.items():
      stats=opportunity_metrics(u,pred)
      for per in periods:rows.append(dict(**info,period=per,horizon=h,**stats))
     tt=ranking_metrics(g.TARGET.to_numpy(),pred)
     for per in periods:target.append(dict(**info,period=per,**tt))
     if stage in ['CURRENT','FUSION']:
      w=topk_weights(pred)
      for k in np.flatnonzero(w):choices.append(dict(**info,ticker=g.iloc[k].ticker,weight=w[k],utility=endpoints['U42'][k],return21=rr[k,0],score=pred[k]))
 o=pd.DataFrame(rows);t=pd.DataFrame(target);ks=['market','variant','stage','period']
 o.to_csv(ROOT/'results/OPPORTUNITY_MONTHS.csv.gz',index=False,compression='gzip');t.to_csv(ROOT/'results/TARGET_MONTHS.csv.gz',index=False,compression='gzip')
 om=['top2_return','top2_excess','top2_regret','selected_negative_return','bottom_quintile_fraction','top5_capture']
 tm=['ndcg2','ndcg5','ic','selected_target','target_regret','target_top_quintile_precision','target_bottom_quintile_fraction']
 o.groupby(ks+['horizon']).agg(months=('date','nunique'),**{k:(k,'mean') for k in om}).reset_index().to_csv(ROOT/'results/OPPORTUNITY_SUMMARY.csv',index=False)
 t.groupby(ks).agg(months=('date','nunique'),**{k:(k,'mean') for k in tm}).reset_index().to_csv(ROOT/'results/TARGET_SUMMARY.csv',index=False)
 pd.DataFrame(choices).to_csv(ROOT/'results/TOP2_DECISIONS.csv.gz',index=False,compression='gzip');pd.DataFrame(excluded).to_csv(ROOT/'results/EVALUATION_EXCLUSIONS.csv',index=False)
 dump(ROOT/'results/NATIVE_COMPLETE.json',dict(opportunity_rows=len(o),target_rows=len(t),no_self_target_change=True))
 z=o[(o.period=='ADAPTIVE2023_2024')&(o.horizon=='U42')&(o.stage=='CURRENT')]
 print('ADAPTIVE U:',z.groupby(['variant','market']).top2_excess.mean().unstack().mul(100).to_string())
if __name__=='__main__':main()
