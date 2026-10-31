"""Side-by-side old/new forecast diagnostics on identical observed monthly outcomes."""
from native_screen import ROOT,load,ranks
from calendar_replay import new_hybrid
import numpy as np,pandas as pd,json
O=ROOT/'results/analysis';records=[]
for market in ['EU','USA']:
 q,h,C,oldr,oldh,olde,oldx,cal=load(market)
 p=pd.read_csv(ROOT/'results/calendar'/f'{market}_FORECASTS.csv.gz',parse_dates=['signal_date'])
 ncal=pd.read_csv(ROOT/'results/calendar'/f'{market}_CALENDAR.csv',parse_dates=['signal_date','entry_date','exit_date'])
 ncal=ncal[ncal.signal_date.between('2019-01-01','2026-06-30')];dates=pd.DatetimeIndex(ncal.signal_date)
 def mat(col):return p.pivot(index='signal_date',columns='ticker',values=col).reindex(index=dates,columns=oldr.columns)
 nr=mat('RETURN');nh=new_hybrid(mat('ET'),mat('XGB'));Oraw=pd.read_pickle(ROOT/'results/calendar'/f'{market}_OPEN.pkl').reindex(columns=oldr.columns)
 for row in cal.itertuples(index=False):
  d=row.signal_date
  if d not in dates or row.entry_date not in Oraw.index or row.exit_date not in Oraw.index:continue
  r=Oraw.loc[row.exit_date]/Oraw.loc[row.entry_date]-1
  scores={'OLD_RETURN':oldr.loc[d],'NEW_RETURN':nr.loc[d],'OLD_HYBRID':oldh.loc[d],'NEW_HYBRID':nh.loc[d]}
  good=r.notna()
  for x in scores.values():good &= x.notna()
  if good.sum()<20:continue
  y=r[good];m=y.mean()
  for name,x in scores.items():
   s=x[good];top=s.nlargest(2).index
   records.append(dict(market=market,date=d,entry=row.entry_date,exit=row.exit_date,model=name,n=len(y),rank_ic=s.rank().corr(y.rank()),selected_return=y[top].mean(),selected_excess=y[top].mean()-m,loss10_rate=(y[top]<-.10).mean(),old_new_rank_correlation=oldr.loc[d,good].rank().corr(nr.loc[d,good].rank()) if 'RETURN' in name else oldh.loc[d,good].rank().corr(nh.loc[d,good].rank())))
f=pd.DataFrame(records);f.to_csv(O/'MATCHED_FORECAST_MONTHS.csv',index=False)
pre=f[f.date<'2025-01-01'];pre.groupby(['market','model']).agg(months=('date','nunique'),rank_ic=('rank_ic','mean'),selected_excess=('selected_excess','mean'),loss10_rate=('loss10_rate','mean'),old_new_rank_correlation=('old_new_rank_correlation','mean')).to_csv(O/'MATCHED_FORECAST_PRE2025.csv')
print(pre.groupby(['market','model'])[['rank_ic','selected_excess','loss10_rate','old_new_rank_correlation']].mean().to_string())
