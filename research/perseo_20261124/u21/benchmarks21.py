from pathlib import Path
import sys,json,hashlib
import numpy as np,pandas as pd
ROOT=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT.parent/'perseo_u19_work'))
def metrics(ds,nav):
 years=(pd.Timestamp(ds[-1])-pd.Timestamp(ds[0])).days/365.2425
 return dict(cagr=float((nav[-1]/nav[0])**(1/years)-1),maxdd=float(min(nav/np.maximum.accumulate(nav)-1)),final_capital=float(10000*nav[-1]/nav[0]),start=str(pd.Timestamp(ds[0]).date()),end=str(pd.Timestamp(ds[-1]).date()))

def market_data(m):
 saved=ROOT/'BENCHMARK_INPUTS.npz'
 if saved.exists():
  with np.load(saved) as z:
   names=list(MAP[m]);return dict(dates=z[m+'_dates'].copy(),tickers=np.array([MAP[m][n] for n in names]),O=np.column_stack([z[m+'_'+n+'_O'] for n in names]),C=np.column_stack([z[m+'_'+n+'_C'] for n in names]),observed=np.column_stack([z[m+'_'+n+'_observed'] for n in names]))
 from accounts19 import base
 return base(m)
MAP={
 'USA':{'SP500':'SPY','NASDAQ100':'QQQ','SEMICONDUCTORS':'SMH','USA_MOMENTUM':'MTUM','GOLD':'GLD'},
 'EU':{'SP500':'SXR8.DE','NASDAQ100':'SXRV.DE','US_TECHNOLOGY':'QDVE.DE','WORLD':'EUNL.DE'},
 'TR':{'SP500':'IE00B5BMR087','NASDAQ100':'IE00B53SZB19','US_TECHNOLOGY':'IE00B3WJKG14','WORLD':'IE00B4L5Y983','WORLD_MOMENTUM':'IE00BP3QZ825','USA_MOMENTUM':'IE00BD1F4N50'}}

def simulate(ds,O,C,observed,strategy):
 start=ds.searchsorted('2020-01-02');assert ds[start]==pd.Timestamp('2020-01-02');end=ds.searchsorted('2026-07-01');qty=0.;cash=10000.;nav=[];orders=[];signal=[];prevmonth=None;target=0;desired=0
 monthly=pd.Series(C,index=ds).groupby(ds.to_period('M')).last()
 avg=monthly.rolling(10,min_periods=10).mean()
 for k in range(start,end+1):
  val=cash+qty*O[k];nav.append(val/10000)
  if k==end:break
  month=ds[k].to_period('M');newmonth=month!=prevmonth
  if strategy=='BUY_HOLD':desired=1
  elif newmonth:
   past=monthly[monthly.index<month];assert len(past)>=10
   prev=past.index[-1];desired=int(past.iloc[-1]>avg.loc[prev]);signal.append(dict(execution_date=str(ds[k].date()),last_signal_month=str(prev),signal_close=float(past.iloc[-1]),average10=float(avg.loc[prev]),desired=desired))
  # On an unavailable opening, retain prior holding and try on the next session.
  if desired!=target and observed[k]:
   if desired:
    invest=(cash-1)/(1+.0015);qty=invest/O[k];cost=1+.0015*invest;cash-=invest+cost
    orders.append(dict(date=str(ds[k].date()),side='BUY',quantity=qty,price=float(O[k]),cost=cost))
   else:
    notional=qty*O[k];cost=1+.0015*notional;cash+=notional-cost
    orders.append(dict(date=str(ds[k].date()),side='SELL',quantity=qty,price=float(O[k]),cost=cost));qty=0.
   target=desired
  prevmonth=month
  assert cash>=-1e-8 and qty>=0
 return np.array(nav),orders,signal

def main():
 rows=[];regimes=[];all_orders=[];all_signals=[];series=[];panels={};qa=[]
 for m,items in MAP.items():
  q=market_data(m);ds=pd.DatetimeIndex(q['dates']);ticks=list(q['tickers']);obs=q.get('observed',np.ones_like(q['O'],bool));start=ds.searchsorted('2020-01-02');end=ds.searchsorted('2026-07-01')
  for name,t in items.items():
   j=ticks.index(t);assert obs[start,j],(m,name,'unobserved initial');assert np.isfinite(q['O'][start:end+1,j]).all()
   panels[m+'_'+name+'_O']=q['O'][:,j];panels[m+'_'+name+'_C']=q['C'][:,j];panels[m+'_'+name+'_observed']=obs[:,j];panels[m+'_dates']=ds.values
   for st in (['BUY_HOLD','SMA10_MONTHLY'] if name in ['SP500','NASDAQ100'] else ['BUY_HOLD']):
    a,o,sg=simulate(ds,q['O'][:,j],q['C'][:,j],obs[:,j],st);dates=ds[start:end+1]
    if st=='BUY_HOLD':
     expected=9999/(1.0015)/10000*q['O'][start:end+1,j]/q['O'][start,j];expected[0]=1;assert np.allclose(a,expected,rtol=0,atol=1e-14)
    meta=dict(market=m,benchmark=name,ticker=t,strategy=st);row=dict(**meta,**metrics(dates,a),orders=len(o),cost_currency=sum(x['cost'] for x in o),missing_opens=int((~obs[start:end+1,j]).sum()));rows.append(row)
    frame=pd.DataFrame(dict(date=dates,nav=a));frame.to_csv(ROOT/f'{m}_{name}_{st}_NAV.csv',index=False)
    for x in o:all_orders.append(dict(**meta,**x))
    for x in sg:all_signals.append(dict(**meta,**x))
    for label,lo,hi in [('2020_2022','2020-01-02','2023-01-03'),('2023_2026','2023-01-03','2026-07-01')]:
     take=(dates>=lo)&(dates<=hi);b=a[take];regimes.append(dict(**meta,period=label,**metrics(dates[take],b/b[0])))
    qa.append(dict(**meta,initial_quote_observed=True,positive_nav=bool((a>0).all()),signal_before_execution=all(x['last_signal_month']<x['execution_date'][:7] for x in sg)))
    print(m,name,st,round(row['cagr']*100,2),round(row['maxdd']*100,2),flush=True)
 np.savez_compressed(ROOT/'BENCHMARK_INPUTS.npz',**panels);pd.DataFrame(rows).to_csv(ROOT/'BENCHMARKS_2020_2026.csv',index=False);pd.DataFrame(regimes).to_csv(ROOT/'BENCHMARKS_REGIMES.csv',index=False);pd.DataFrame(all_orders).to_csv(ROOT/'BENCHMARK_ORDERS.csv',index=False);pd.DataFrame(all_signals).to_csv(ROOT/'BENCHMARK_SIGNALS.csv',index=False);(ROOT/'BENCHMARK_QA.json').write_text(json.dumps(qa,indent=2))
if __name__=='__main__':main()
