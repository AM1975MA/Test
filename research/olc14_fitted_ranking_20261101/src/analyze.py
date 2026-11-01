"""Paired block uncertainty and fitting-vs-fixed attribution."""
from __future__ import annotations
import json
import numpy as np,pandas as pd
from common import ROOT,MARKETS,readcsv
from build_scores import load_frame,make_groups
from chrono_fit import inner_folds,balanced_value
from ranking_core import score,PRIOR
from recovery_core import atomic_json
CONTRASTS=[('TARGET_SELECT','ORIGINAL'),('CUM_FIXED','ORIGINAL'),('CUM_FIT','CUM_FIXED'),('INC_FIXED','ORIGINAL'),('INC_FIT','INC_FIXED')]

def main():
 o=readcsv(ROOT/'results/OPPORTUNITY_MONTHS.csv.gz');s=readcsv(ROOT/'results/SCORECARD.csv')
 main=o[(o.seed=='MEAN3')&(o.period=='PRE2025')]
 rng=np.random.default_rng(20261101);grid=pd.period_range('2021-01','2024-12',freq='M');n=len(grid)
 starts=rng.integers(0,n,size=(4000,8));indices=((starts[:,:,None]+np.arange(6))%n).reshape(4000,n)
 rows=[]
 for cand,base in CONTRASTS:
  for stage in ['CURRENT','FUSION']:
   for horizon in ['U42','0_21','0_63','21_42','42_63']:
    for market in MARKETS:
     f=main[(main.stage==stage)&(main.horizon==horizon)&(main.market==market)&main.variant.isin([cand,base])]
     p=f.pivot(index='date',columns='variant',values='top2_excess');p.index=p.index.to_period('M');p=p.reindex(grid)
     delta=(p[cand]-p[base]).to_numpy();boot=np.nanmean(delta[indices],axis=1);lo,hi=np.quantile(boot,[.025,.975])
     rows.append(dict(candidate=cand,baseline=base,stage=stage,horizon=horizon,market=market,n=int(np.isfinite(delta).sum()),difference=float(np.nanmean(delta)),lower=float(lo),upper=float(hi),block_months=6,draws=4000))
 pd.DataFrame(rows).to_csv(ROOT/'results/PAIRED_UNCERTAINTY.csv',index=False)
 params=json.loads((ROOT/'results/FITTED_PARAMETERS.json').read_text());groups=make_groups({m:load_frame(m) for m in MARKETS});val=[]
 for year,p in params.items():
  outer=pd.Timestamp(int(year),1,1);folds=inner_folds(groups,outer);valid=[g for f in folds for g in f['valid']]
  for rep in ['CUM','INC']:
   cfg=p[rep];chosen=next(v for v in cfg['cv'] if v['alpha']==cfg['alpha'] and v['lambda']==cfg['lambda'])
   anchor=balanced_value(valid,[score(g[rep],PRIOR) for g in valid])
   for m in MARKETS:
    a=o[(o.market==m)&(o.seed=='MEAN3')&(o.period=='ALL_ACTIVE')&(o.stage=='CURRENT')&(o.horizon=='U42')&(o.date.dt.year==int(year))]
    means=a.groupby('variant').top2_excess.mean();count=a[a.variant==rep+'_FIT'].date.nunique()
    val.append(dict(year=int(year),representation=rep,market=m,inner_selected=chosen[m],inner_fixed=anchor[m],inner_delta=chosen[m]-anchor[m],outer_delta=float(means.get(rep+'_FIT',np.nan)-means.get(rep+'_FIXED',np.nan)),outer_months=count))
 pd.DataFrame(val).to_csv(ROOT/'results/INNER_VS_OUTER.csv',index=False)
 native=pd.read_csv(ROOT/'results/OPPORTUNITY_SUMMARY.csv');sel=native[(native.seed=='MEAN3')&(native.period=='PRE2025')&(native.stage=='CURRENT')]
 sel.to_csv(ROOT/'results/MAIN_NATIVE.csv',index=False)
 port=s[(s.period=='ACTIVE2021_2024')&(s.policy=='IMMEDIATE')&(s['mode']=='FULL')&(s.fee==.001)]
 port.to_csv(ROOT/'results/MAIN_PORTFOLIO.csv',index=False)
 # Seed sensitivity uses the already fixed MEAN3-fitted coefficients, not retuning.
 seedrows=[]
 for rep in ['CUM','INC']:
  for m in MARKETS:
   for seed in ['101','211','307','MEAN3']:
    a=native[(native.market==m)&(native.seed.astype(str)==seed)&(native.period=='PRE2025')&(native.stage=='CURRENT')&(native.horizon=='U42')].set_index('variant')
    seedrows.append(dict(market=m,representation=rep,seed=seed,delta_U=float(a.loc[rep+'_FIT','top2_excess']-a.loc[rep+'_FIXED','top2_excess'])))
 pd.DataFrame(seedrows).to_csv(ROOT/'results/SEED_SENSITIVITY.csv',index=False)
 follow=o[(o.seed.astype(str)=='MEAN3')&(o.period=='ALL_ACTIVE')&(o.date>=pd.Timestamp('2021-01-01'))&(o.date<pd.Timestamp('2025-01-01'))]
 follow.groupby(['market','variant','stage','horizon']).agg(months=('date','nunique'),top2_excess=('top2_excess','mean'),top2_regret=('top2_regret','mean')).reset_index().to_csv(ROOT/'results/ALL_2021_2024_SIGNALS_FOLLOWUP.csv',index=False)
 atomic_json(ROOT/'results/ANALYSIS_COMPLETE.json',dict(paired_contrasts=len(rows),nested_fit_diagnostics=len(val),seed_sensitivity_rows=len(seedrows),inference='Descriptive paired circular block6 bootstrap; no posterior or full history selection correction'))
 print('ANALYSIS_COMPLETE',len(rows),flush=True)
if __name__=='__main__':main()
