"""Frozen engine; score-level gating only. Reconcile every daily account."""
import numpy as np,pandas as pd,time
from io_utils import ROOT,MARKETS,VARIANTS,readcsv,dump,sha
from portfolio_adapter import adapt_state
from portfolio_metrics_parent import metrics,policy_args
from vector_engine import simulate
from accounting import decompose

def adaptive_metrics(q,r):
 ds=pd.DatetimeIndex(q['dates']);actual=ds[1:];log=np.diff(np.log(np.r_[1.,r['nav']]))[:-1];rows=[]
 for period,start,end in [('ADAPTIVE2023_2024','2023-01-01','2024-12-31'),('ADAPTIVE_FULL','2023-01-01','2026-07-01'),('ADAPTIVE_FIRST_TRADE_2023_2024','2023-02-01','2024-12-31'),('ADAPTIVE_FIRST_TRADE_FULL','2023-02-01','2026-07-01')]:
  mask=(actual>=pd.Timestamp(start))&(actual<=pd.Timestamp(end));x=log[mask]
  if not len(x):continue
  eq=np.exp(x.cumsum());dd=eq/np.maximum.accumulate(np.r_[1.,eq])[1:]-1;ll=r['ledger'][:-1][mask]
  rows.append(dict(period=period,first_valuation=str(actual[mask][0].date()),last_valuation=str(actual[mask][-1].date()),n=len(x),cagr=float(np.expm1(x.mean()*252)),annual_log=float(x.mean()*252),period_return=float(np.expm1(x.sum())),maxdd=float(dd.min()),turnover_annual=float(ll[:,4].mean()*252),actual_risk_exposure=float(ll[:,12].mean()),mean_positions=float(ll[:,14].mean()),effective_positions=float(ll[:,15].mean()),stops=int(ll[:,8].sum()),blocked=int(ll[:,11].sum()),rebalances=int(ll[:,3].sum()),fee_drag_sum=float(np.sum(ll[:,5:8].sum(1)/ll[:,0]))))
 return rows

def main():
 rows=[];checks=[];decisions=[];out=ROOT/'results';(out/'paths').mkdir(exist_ok=True);t=time.time()
 for m in MARKETS:
  q=dict(np.load(ROOT/f'inputs/{m}_STATE_HALF.npz',allow_pickle=False));cal=readcsv(ROOT/f'inputs/{m}_CALENDAR.csv');scores=readcsv(out/f'{m}_SCORES.csv.gz')
  for v in VARIANTS:
   st,ev,dd=adapt_state(q,cal,scores,v+'_FUSION');dd['market']=m;dd['variant']=v;decisions.append(dd)
   for mode in ['FULL','LAG1']:
    for pol in ['IMMEDIATE','DELAY3','PHASE5'] if mode=='FULL' else ['IMMEDIATE']:
     for fee in [.001,.003]:
      key=f'{m}_{v}_{pol}_{mode}_C{round(fee*10000)}';res=simulate(st,ev,fee=fee,lag_systemic=mode=='LAG1',**policy_args(pol))
      capital=((res['primary_units'][:-1]+res['defensive_units'][:-1])*st['O'][1:]).sum(1)+res['free_cash'][:-1]
      err=float(np.max(abs(capital-res['nav'][:-1])));assert err<1e-10
      attr=decompose(st,res);le=float(np.max(abs(attr['log_components'].sum(1)-attr['log_return'])));assert le<1e-12
      pe=None
      if v in ['ORIGINAL','CUM_FIXED','CUM_FIT']:
       old=np.load(ROOT/'inputs/oracles'/f'{key}.npz');pe=max(float(np.max(abs(res[k]-old[k]))) for k in res)
       for k in res:np.testing.assert_allclose(res[k],old[k],atol=5e-12,rtol=5e-13)
       for k in ['primary_units','defensive_units','targets','free_cash']:np.testing.assert_array_equal(res[k],old[k])
      obs=st.get('observed',np.ones_like(st['O'],bool));before=np.vstack([np.zeros(st['O'].shape[1]),res['primary_units'][:-1]])
      bad=(np.abs(res['primary_units']-before)>1e-12)&(~obs);assert not bad.any()
      p=out/'paths'/f'{key}.npz';np.savez_compressed(p,dates=st['dates'],tickers=st['tickers'],**res)
      rr=metrics(st,res)+adaptive_metrics(st,res);rows.extend(dict(market=m,variant=v,policy=pol,mode=mode,fee=fee,config=key,**r) for r in rr)
      checks.append(dict(config=key,intervals=len(st['dates'])-1,nav_error=err,log_error=le,parent_error=pe,missing_quote_trades=int(bad.sum()),sha256=sha(p)))
      pd.DataFrame(rows).to_csv(out/'SCORECARD.csv',index=False);pd.DataFrame(checks).to_csv(out/'PATH_VERIFICATION.csv',index=False)
   print('REPLAY',m,v,'paths',len(checks),'elapsed',round(time.time()-t,1),flush=True)
 pd.concat(decisions).to_csv(out/'PORTFOLIO_PROPOSALS.csv',index=False)
 dump(out/'REPLAY_COMPLETE.json',dict(paths=len(checks),parent_controls=48,nav_intervals=sum(c['intervals'] for c in checks),max_nav_error=max(c['nav_error'] for c in checks),engine_changed=False))
 print('REPLAY_COMPLETE',len(checks),flush=True)
if __name__=='__main__':main()
