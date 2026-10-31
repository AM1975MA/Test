from pathlib import Path
import numpy as np,pandas as pd
from scipy.stats import spearmanr
ROOT=Path(__file__).resolve().parent
p=pd.read_csv(ROOT/'PREQUENTIAL_MULTIHORIZON_PREDICTIONS.csv.gz',parse_dates=['signal_date'])
f=pd.read_pickle(ROOT/'PIT_MONTHLY_ETF_FEATURES.pkl')
sc=f[['signal_date','ticker','V3_PAIR25_HYBRID_PCT','V3_PAIR127_PCT','MOM252_PCT']]
p=p.merge(sc,on=['signal_date','ticker'],how='left',validate='many_to_one')
# Score skill always on paired months/eligible ticker; 4 predictions each.
records=[];series=[]
for (h,yr,m),g in p.groupby(['horizon','year','model']):
 g=g.dropna(subset=['true_log','mu','true_alpha','mu_alpha']);
 if len(g)<5: continue
 for label,sub in [('YEAR',g),('PRE2025',g[g.year<=2024]),('YEAR2025',g[g.year==2025])]:
  if len(sub)==0:continue
  gr=[]
  for date,x in sub.groupby('signal_date'):
   if len(x)<25:continue
   try:
    rank=float(spearmanr(x.mu,x.true_log).statistic)
    alpha_rank=float(spearmanr(x.mu_alpha,x.true_alpha).statistic)
   except Exception:continue
   order=x.sort_values('mu',ascending=False);grab=float(order.head(5).true_log.mean());allmean=float(x.true_log.mean());
   z={'date':date,'h':h,'year':yr,'model':m,'ic':rank,'alpha_ic':alpha_rank,
      'top5_excess':grab-allmean,'top5_avg_ret':grab,'mae':float(np.mean(abs(x.mu-x.true_log))),
      'rmse':float(np.mean((x.mu-x.true_log)**2))**.5,'alpha_rmse':float(np.mean((x.mu_alpha-x.true_alpha)**2))**.5,
      'n':len(x)}
   series.append(z);gr.append(z)
  if len(gr):
   a=pd.DataFrame(gr);rec={'group':label,'horizon':h,'year':yr,'model':m,'months':len(a)}
   rec.update(a[['ic','alpha_ic','top5_excess','top5_avg_ret','rmse','alpha_rmse']].mean().to_dict());records.append(rec)
monthly=pd.DataFrame(series).drop_duplicates(['date','h','model']);monthly.to_csv(ROOT/'MONTHLY_PREDICTIVE_SKILL.csv',index=False)
pre=monthly[(monthly.year<=2024)&(monthly.year>=2021)]
full=monthly[monthly.year<=2025]
for name,df in [('PRE2025',pre),('THROUGH2025',full)]:
 tab=df.groupby(['h','model']).agg(months=('date','nunique'),ic=('ic','mean'),alpha_ic=('alpha_ic','mean'),top5_excess=('top5_excess','mean'),top5_avg_ret=('top5_avg_ret','mean'),rmse=('rmse','mean'),alpha_rmse=('alpha_rmse','mean')).reset_index()
 tab.to_csv(ROOT/f'{name}_PREDICTIVE_SCORECARD.csv',index=False)
 print(name,tab.to_string(index=False,float_format=lambda x:f'{x:.4f}'),flush=True)
# Evaluate same exact 21-d sample raw native V3 vs V5 on monthly paired 2021-24.
base=f[['signal_date','ticker','V3_PAIR25_HYBRID_PCT','V3_PAIR127_PCT','MOM252_PCT','y21']]
rows=[]
for date,g in base[(base.signal_date.dt.year>=2021)&(base.signal_date.dt.year<=2024)].groupby('signal_date'):
 g=g.dropna(subset=['y21','V3_PAIR25_HYBRID_PCT','V3_PAIR127_PCT','MOM252_PCT'])
 if len(g)<25: continue
 for mod in ['V3_PAIR25_HYBRID_PCT','V3_PAIR127_PCT','MOM252_PCT']:
  chosen=g.sort_values(mod,ascending=False)
  rows.append({'date':date,'h':21,'model':mod,'ic':spearmanr(g[mod],g.y21).statistic,'top5_excess':chosen.head(5).y21.mean()-g.y21.mean(),'top5_avg_ret':chosen.head(5).y21.mean(),'n':len(g)})
raw=pd.DataFrame(rows);raw.to_csv(ROOT/'SOURCE_RANKER_21D_SCORECARD_MONTHLY.csv',index=False)
print('SOURCE 21D',raw.groupby('model')[['ic','top5_excess','top5_avg_ret']].mean().to_string(),flush=True)
# Month bootstrap contrasts: +V2/V3 ridge vs factor+historical-only and factor-only, 6-mo blocks on paired date scores.
rng=np.random.default_rng(321029);cs=[]
for h in [21,42,63]:
 x=pre[pre.h==h]
 for metric in ['ic','alpha_ic','top5_excess','rmse']:
  pt=x.pivot(index='date',columns='model',values=metric)
  for challenger,control in [('V5_FACTOR_PLUS_EXPERT_RIDGE','FACTOR_PLUS_BASIC_RIDGE'),('V5_FACTOR_PLUS_EXPERT_GBM','FACTOR_PLUS_BASIC_RIDGE'),('V5_FACTOR_PLUS_EXPERT_RIDGE','FACTOR_ONLY')]:
   d=(pt[challenger]-pt[control]).dropna().to_numpy(float);n=len(d)
   if n<8: continue
   bt=np.empty(1800)
   for k in range(len(bt)):
    ix=np.concatenate([np.arange(z,z+6)%n for z in rng.integers(0,n,size=(n+5)//6)])[:n]
    bt[k]=d[ix].mean()
   cs.append(dict(horizon=h,metric=metric,challenger=challenger,control=control,months=n,mean_delta=float(d.mean()),lo=float(np.quantile(bt,.025)),hi=float(np.quantile(bt,.975))))
pd.DataFrame(cs).to_csv(ROOT/'PAIRED_MONTH_BLOCK_CI.csv',index=False)
