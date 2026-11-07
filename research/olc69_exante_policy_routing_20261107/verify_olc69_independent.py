#!/usr/bin/env python3
"""Independent numpy least-squares and daily-ledger QA of the OLC69 route.

Does not import OLC69 model/engine. Reconstructs standardization/ridge prediction
and the annual/period financial metrics from frozen exported tables.
"""
from pathlib import Path
import numpy as np,pandas as pd,json
ROOT=Path(__file__).resolve().parent
RES=ROOT/'results'
raw=pd.read_csv(ROOT/'OLC68_PRESIGNAL_EVENT_DIAGNOSTIC.csv')
fts=['universe_breadth_63','pair_avg_mom63','pair_prior_mom_weighted_tilt','pair_corr63']
tgt={'B':'weightonly_logbp','C':'timingonly_logbp','D':'paired_logbp'}
QA={'manual_ridge_max_error_bp':0.,'years_checked':0,'periods_checked':0,'routes_checked':0,'maturity_checks':0}

def matrix_pred(X,y,x,alpha=25.):
 mu=X.mean(axis=0)
 sigma=X.std(axis=0,ddof=0)
 sigma=np.where(sigma>0,sigma,1.)
 Z=(X-mu)/sigma
 center=y.mean()
 beta=np.linalg.solve(Z.T@Z+alpha*np.eye(Z.shape[1]),Z.T@(y-center))
 return float(center+((x-mu)/sigma)@beta)

for market in ['EU','USA']:
 data=raw[raw.market==market].sort_values('signal_month').copy()
 decisions=pd.read_csv(RES/f'OLC69_{market}_PRESIGNAL_ROUTING.csv')
 assert len(data)==len(decisions)==82
 assert np.array_equal(data.signal_month.to_numpy(),decisions.month.to_numpy())
 for i,r in enumerate(data.itertuples(index=False)):
  now=pd.Period(r.signal_month,'M')
  earlier=data[pd.PeriodIndex(data.signal_month,freq='M')<=now-2]
  assert len(earlier)==int(decisions.loc[i,'train_n'])
  assert pd.Timestamp(decisions.loc[i,'asof'])<pd.Period(r.signal_month,'M').start_time
  QA['maturity_checks']+=1
  forecasts={'A':0.}
  if len(earlier)>=24:
   for action,target in tgt.items():
    p=matrix_pred(earlier[fts].to_numpy(float),earlier[target].to_numpy(float),data.iloc[i][fts].to_numpy(float))
    ref=float(decisions.loc[i,'predict_'+action+'_logbp'])
    error=abs(p-ref)
    QA['manual_ridge_max_error_bp']=max(QA['manual_ridge_max_error_bp'],error)
    assert error<1e-7,(market,r.signal_month,action,error)
    forecasts[action]=p
   winner=max(['A','B','C','D'],key=lambda a:forecasts[a])
   chosen=winner if winner!='A' and forecasts[winner]>5.0 else 'A'
  else: chosen='A'
  assert chosen==decisions.loc[i,'action'],(market,r.signal_month,chosen,decisions.loc[i,'action'])
  QA['routes_checked']+=1
 daily=pd.read_csv(RES/'OLC69_DAILY_LOGRET.csv.gz')
 year=pd.read_csv(RES/'OLC69_ANNUAL.csv')
 sc=pd.read_csv(RES/'OLC69_SCORECARD.csv')
 for fee in [0.001,0.003]:
  d=daily[(daily.market==market)&(np.isclose(daily.fee,fee))].copy()
  assert d.date.is_unique and len(d)>1500
  d.date=pd.to_datetime(d.date)
  for yr,grp in d.groupby(d.date.dt.year):
   target=year[(year.market==market)&(np.isclose(year.fee,fee))&(year.year==yr)]
   assert len(target)==1
   actual=np.expm1(grp.logr.sum())
   assert abs(actual-float(target.annual_return.iloc[0]))<2e-12
   QA['years_checked']+=1
  for row in sc[(sc.market==market)&(np.isclose(sc.fee,fee))].itertuples(index=False):
   x=d[(d.date>=row.first_valuation)&(d.date<=row.last_valuation)].logr.to_numpy(float)
   assert len(x)==row.n
   cagr=float(np.expm1(x.mean()*252))
   eq=np.exp(x.cumsum());dd=float((eq/np.maximum.accumulate(np.r_[1.,eq])[1:]-1).min())
   assert abs(cagr-row.cagr)<1e-12,(market,fee,row.period,'cagr')
   assert abs(dd-row.maxdd)<1e-12,(market,fee,row.period,'dd',dd,row.maxdd)
   QA['periods_checked']+=1
QA['status']='PASS'
(RES/'OLC69_INDEPENDENT_QA.json').write_text(json.dumps(QA,indent=2))
print(QA)