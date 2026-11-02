"""Paired regime attribution, effective contrast counts, not CAGR selection."""
from io_utils import ROOT,MARKETS,readcsv,dump
import pandas as pd,numpy as np,json
from scipy.stats import spearmanr

COMPARISONS=[('CONTEXT_RECENT','CONSTANT'),('CONTEXT_RECENT','RECENT'),('CONTEXT_RECENT','CUM_FIT'),('F_CONTEXT_RECENT','F_CONSTANT'),('F_CONTEXT_RECENT','F_RECENT'),('F_CONTEXT_RECENT','CUM_FIT')]

def block_indices(n,draws=4000,block=6,seed=20261102):
 rng=np.random.default_rng(seed);s=rng.integers(0,n,size=(draws,int(np.ceil(n/block))))
 return ((s[:,:,None]+np.arange(block)[None,None,:])%n).reshape(draws,-1)[:,:n]

def main():
 o=readcsv(ROOT/'results/OPPORTUNITY_MONTHS.csv.gz');summ=readcsv(ROOT/'results/OPPORTUNITY_SUMMARY.csv');trace=readcsv(ROOT/'results/GATE_TRACE.csv')
 comparisons=[]
 for period,start,end in [('ADAPTIVE2023_2024','2023-01-31','2024-12-31'),('ADAPTIVE_FULL','2023-01-31','2026-06-30')]:
  grid=pd.period_range(start,end,freq='M');idx=block_indices(len(grid))
  for stage in ['CURRENT','FUSION']:
   for m in MARKETS:
    q=o[(o.period==period)&(o.stage==stage)&(o.market==m)&(o.horizon=='U42')]
    for a,b in COMPARISONS:
     qa=q[q.variant.eq(a)].set_index('date').top2_excess;qb=q[q.variant.eq(b)].set_index('date').top2_excess
     diff=qa-qb;diff.index=diff.index.to_period('M');z=diff.reindex(grid).to_numpy(float)
     boot=np.nanmean(z[idx],axis=1);lo,hi=np.nanquantile(boot,[.025,.975])
     comparisons.append(dict(period=period,stage=stage,market=m,candidate=a,baseline=b,n=int(np.isfinite(z).sum()),delta=float(np.nanmean(z)),lo=float(lo),hi=float(hi),identical_observed_payoffs=bool(np.nanmax(abs(z))==0)))
 pd.DataFrame(comparisons).to_csv(ROOT/'results/PAIRED_UNCERTAINTY.csv',index=False)
 rows=[];predrows=[];groupstats=[];corr=[]
 for m in MARKETS:
  s=readcsv(ROOT/f'results/{m}_SCORES.csv.gz')
  for d,g in s.groupby('signal_date'):
   if d.year<2023:continue
   for a,b in [('CUM_FIT','CUM_FIXED'),*COMPARISONS]:
    for stage in ['CURRENT','SMOOTH','FUSION']:
     top=lambda v:set(g.sort_values([v+'_'+stage,'ticker'],ascending=[False,True]).ticker.head(2))
     rows.append(dict(market=m,date=d,year=d.year,candidate=a,baseline=b,stage=stage,different=top(a)!=top(b)))
  f=readcsv(ROOT/f'inputs/{m}_FITTING_FRAME.csv.gz')
  for d,g in f.groupby('signal_date'):
   if d.year<2023:continue
   for a,b in [('C21','C42'),('C21','C63'),('C42','C63')]:
    corr.append(dict(market=m,date=d,pair=f'{a}_{b}',spearman=float(spearmanr(g[a],g[b],nan_policy='omit').statistic)))
 pd.DataFrame(rows).to_csv(ROOT/'results/CHOICE_CONTRASTS.csv',index=False)
 pd.DataFrame(rows).groupby(['candidate','baseline','stage','market']).different.agg(changes='sum',signals='size').reset_index().to_csv(ROOT/'results/CHOICE_CONTRAST_SUMMARY.csv',index=False)
 pd.DataFrame(corr).to_csv(ROOT/'results/HEAD_CORRELATIONS.csv',index=False)
 for target,path in [('CURRENT','GATE_PANEL.csv'),('FUSION','FUSION_GATE_PANEL.csv')]:
  p=readcsv(ROOT/'inputs'/path);p=p[(p.date>=pd.Timestamp('2021-01-01'))&(p.available<=pd.Timestamp('2026-07-01'))]
  p['trend_state']=np.where(p.trend126>=0,'up','down');p['volatility_state']=np.where(p.vol_ratio>=0,'rising','falling')
  for (m,t,v),g in p.groupby(['market','trend_state','volatility_state']):
   groupstats.append(dict(target=target,market=m,trend=t,volatility=v,months=len(g),nonzero_contrasts=int((abs(g.delta)>1e-14).sum()),mean_delta=g.delta.mean(),descriptive_only=True))
 for (m,v),g in trace[trace.adaptive & trace.available.notna() & (trace.available<=pd.Timestamp('2026-07-01'))].groupby(['market','variant']):
  e=g.predicted_delta-g.realized_delta
  predrows.append(dict(market=m,variant=v,months=len(g),mse=float(np.mean(e**2)),mae=float(np.mean(abs(e))),g_min=g.g.min(),g_mean=g.g.mean(),g_max=g.g.max(),nonzero_contrasts=int((abs(g.realized_delta)>1e-14).sum())))
 pd.DataFrame(groupstats).to_csv(ROOT/'results/REGIME_DIAGNOSTICS.csv',index=False);pd.DataFrame(predrows).to_csv(ROOT/'results/DELTA_PREDICTION_DIAGNOSTICS.csv',index=False)
 audit=pd.concat([pd.read_csv(ROOT/'results/GATE_FIT_AUDIT.csv'),pd.read_csv(ROOT/'results/FUSION_GATE_FIT_AUDIT.csv')]);audit.to_csv(ROOT/'results/ALL_GATE_FIT_AUDIT.csv',index=False)
 cols=[]
 for path in sorted((ROOT/'models').glob('*.json')):
  j=json.loads(path.read_text())
  if not j['active']:continue
  for name,beta in zip(j['model']['features'],j['model']['coef']):cols.append(dict(model=path.stem,year=j['year'],feature=name,normalized_coef=beta,penalty=j['model']['penalty']))
 pd.DataFrame(cols).to_csv(ROOT/'results/CONTEXT_COEFFICIENTS.csv',index=False)
 for m in MARKETS:
  trace[trace.market.eq(m)].pivot(index='date',columns='variant',values='g').to_csv(ROOT/f'results/{m}_GATE_WEIGHTS.csv')
 checks=[]
 for m in MARKETS:
  for a,b in [('CONTEXT_RECENT','CONSTANT'),('CONTEXT_RECENT','RECENT'),('F_CONTEXT_RECENT','F_CONSTANT'),('F_CONTEXT_RECENT','F_RECENT')]:
   for mode in ['FULL','LAG1']:
    for pol in ['IMMEDIATE','DELAY3','PHASE5'] if mode=='FULL' else ['IMMEDIATE']:
     for cost in [10,30]:
      x=np.load(ROOT/f'results/paths/{m}_{a}_{pol}_{mode}_C{cost}.npz');y=np.load(ROOT/f'results/paths/{m}_{b}_{pol}_{mode}_C{cost}.npz')
      diff=max(float(np.max(abs(x[k]-y[k]))) for k in ['nav','ledger','primary_units','defensive_units','free_cash','targets'])
      checks.append(dict(market=m,candidate=a,baseline=b,policy=pol,mode=mode,cost=cost,max_path_difference=diff))
 pd.DataFrame(checks).to_csv(ROOT/'results/CONTEXT_PATH_EQUALITY.csv',index=False)
 dump(ROOT/'results/ANALYSIS_COMPLETE.json',dict(actual_outer_fits=int(audit.active.sum()),inner_fits=int(audit.inner_fits.sum()),paired_native_contrasts=len(comparisons),path_equality_checks=len(checks),all_primary_context_vs_controls_identical=all(x['max_path_difference']==0 for x in checks),descriptive_regime_groups=len(groupstats)))
 print((ROOT/'results/ANALYSIS_COMPLETE.json').read_text());print(pd.DataFrame(predrows).to_string(index=False))
if __name__=='__main__':main()
