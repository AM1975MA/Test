#!/usr/bin/env python3
"""Equal-cardinality and equal-category-cap historical comparison of archived V2/Ridge score ranking.
No parameter selection: predeclared diagnostic K=5,10,15; cap=None or 3.
Common 42 signal dates 2023-01 through 2026-06; same next-open prices, fees and dates.
"""
from pathlib import Path
import zipfile,io,os,numpy as np,pandas as pd
from math import ceil
B=Path(os.environ.get('ETF149_DATA_ROOT','/mnt/data'));HERE=Path(__file__).resolve().parent;O=Path(os.environ.get('ETF149_OUTPUT_DIR',str(B/'ETF149_Rank_to_PnL_20261030')));O.mkdir(parents=True,exist_ok=True)
z=zipfile.ZipFile(B/'etf149_forward_20261023.zip');u=pd.read_csv(io.BytesIO(z.read('universe.csv')));tick=u.ticker.tolist();cat=u.macro_category.to_numpy();n=len(tick)
D=pd.DatetimeIndex(pd.read_csv(io.BytesIO(z.read('SPY.csv')),parse_dates=['date'],usecols=['date']).date)
P=np.full((len(D),n),np.nan)
for j,t in enumerate(tick):
 d=pd.read_csv(io.BytesIO(z.read(t+'.csv')),parse_dates=['date'],usecols=['date','Open']).set_index('date')
 P[:,j]=d.Open.reindex(D).to_numpy(float)
mon=pd.Series(np.arange(len(D)),index=D).groupby(D.to_period('M')).last().to_numpy()
period={D[int(mon[j])].strftime('%Y-%m-%d'):(int(mon[j])+1,int(mon[j+1])+1) for j in range(len(mon)-1) if int(mon[j+1])+1<len(D)}
if (HERE/'v2_255_frozen_scores.csv').exists():
 v=pd.read_csv(HERE/'v2_255_frozen_scores.csv').rename(columns={'signal_date':'date'})
else:
 z2=zipfile.ZipFile(B/'v2_deep_leaf_complete_results.zip')
 v=pd.read_csv(io.BytesIO(z2.read('runs/v2_large_leaf_complete/OOS_SCORES.csv')))
 v=v[v.variant=='leaves_255'].copy()
 v['date']=pd.to_datetime(v.signal_date).dt.strftime('%Y-%m-%d')
v['model']='V2'
if (HERE/'ridge_frozen_scores.csv').exists():
 r=pd.read_csv(HERE/'ridge_frozen_scores.csv')
else:
 z3=zipfile.ZipFile(B/'ETF149_Predictive_Research_2020_2026.zip')
 r=pd.read_csv(io.BytesIO(z3.read('ETF149_predictive_research/forward_2026/monthly_predictions.csv.gz')),compression='gzip',usecols=['date','ticker','ridge_nokalman'])
r['score']=r.ridge_nokalman;r['model']='RIDGE'
s=pd.concat([v[['model','date','ticker','score']],r[['model','date','ticker','score']]])
dates=sorted(set(s[s.model=='V2'].date)&set(s[s.model=='RIDGE'].date)&set(period));assert len(dates)==42,len(dates)
rows=[]
for k in [5,10,15]:
 for cap in [None,3]:
  previous={'V2':np.zeros(n),'RIDGE':np.zeros(n)}
  for sig in dates:
   e,x=period[sig];gross=P[x]/P[e];assert np.isfinite(gross).all()
   for model in ['V2','RIDGE']:
    score=s[(s.model==model)&(s.date==sig)].set_index('ticker').reindex(tick).score.to_numpy()
    assert np.isfinite(score).all()
    rank=np.argsort(-score,kind='stable')
    chosen=[];used={}
    for j in rank:
     if cap is not None and used.get(cat[j],0)>=cap:continue
     chosen.append(j);used[cat[j]]=used.get(cat[j],0)+1
     if len(chosen)==k:break
    assert len(chosen)==k
    w=np.zeros(n);w[chosen]=1./k
    raw=float(np.dot(w,gross)-1)
    turnover=float(np.abs(w-previous[model]).sum())
    net=(1-.001*turnover)*(1+raw)-1
    drift=w*gross/(1+raw)
    previous[model]=drift
    rows.append(dict(signal_date=sig,k=k,cap='none' if cap is None else '3',model=model,top_gross=raw,
                     spy_gross=float(gross[tick.index('SPY')]-1),top_net=net,turnover=turnover,
                     top_category_count=max(used.values()),top_category_distinct=len(used)))
a=pd.DataFrame(rows);a.to_csv(O/'equal_k_same_months.csv',index=False)
summary=[]
for (k,cap),g in a.groupby(['k','cap']):
 x=g.pivot(index='signal_date',columns='model',values=['top_gross','top_net','turnover','top_category_distinct'])
 for field in ['top_gross','top_net']:
  d=(x[field]['RIDGE']-x[field]['V2']).to_numpy()
  rng=np.random.default_rng(20261030+int(k)+(3 if cap=='3' else 0))
  ix=((rng.integers(0,len(d),size=(5000,ceil(len(d)/6),1))+np.arange(6))%len(d)).reshape(5000,-1)[:,:len(d)]
  ci=np.quantile(d[ix].mean(axis=1),[.025,.975]);summary.append(dict(k=k,cap=cap,comparison=field,
    months=len(d),ridge_mean=float(x[field]['RIDGE'].mean()),v2_mean=float(x[field]['V2'].mean()),
    mean_difference=float(d.mean()),ci95_low=float(ci[0]),ci95_high=float(ci[1]),
    mean_monthly_turnover_ridge=float(x['turnover']['RIDGE'].mean()),mean_monthly_turnover_v2=float(x['turnover']['V2'].mean()),
    mean_distinct_categories_ridge=float(x['top_category_distinct']['RIDGE'].mean()),
    mean_distinct_categories_v2=float(x['top_category_distinct']['V2'].mean())))
out=pd.DataFrame(summary).sort_values(['k','cap','comparison']);out.to_csv(O/'equal_k_summary.csv',index=False)
print(out.round(4).to_string(index=False))