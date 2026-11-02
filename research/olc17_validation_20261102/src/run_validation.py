"""Frozen candidate replays, timing attribution and independently checked metrics.
No ranking/model is refitted. Every path and source audit is persisted.
"""
from pathlib import Path
import sys,json,argparse,time,hashlib
import numpy as np,pandas as pd
ROOT=Path(__file__).resolve().parents[1]
PARENT=ROOT/'parent/olc16_contextual_rank_20261102'
sys.path.append(str(PARENT/'src'))
from portfolio_adapter import adapt_state
from portfolio_metrics_parent import metrics
from vector_engine import simulate as original_simulate
from validated_engine import simulate
from accounting import decompose
VARIANTS=('ORIGINAL','CUM_FIT','TOP2_STATIC_REVALUE','TOP2_CONTEXT_REVALUE')
SCENARIOS={'LEGACY':('NOW','NOW'),'EXPOSURE_PREOPEN':('PREVIOUS','NOW'),
 'STOP_PREOPEN':('NOW','PREVIOUS'),'ALL_PREOPEN':('PREVIOUS','PREVIOUS'),
 'NO_GAP_LAYER':('OFF','OFF')}

def read(p):
 f=pd.read_csv(p,float_precision='round_trip')
 for c in ['signal_date','entry_date','exit_date']:
  if c in f:f[c]=pd.to_datetime(f[c])
 return f

def monthly_attribution(st,r):
 a=decompose(st,r);D=len(st['dates'])-1
 components=pd.DataFrame(a['log_components'],columns=a['names'])
 components['primary']=components[['old_only','new_only','shared','other_primary']].sum(axis=1)
 components['interval_start']=pd.to_datetime(st['dates'][:-1]);components['date']=pd.to_datetime(st['dates'][1:])
 components['log_return']=a['log_return'];components['month']=components.date.dt.to_period('M').astype(str)
 for name,j in [('stops',8),('systemic',9),('rebalances',3),('blocked',11),('exposure',12),('turnover',4)]:components[name]=r['ledger'][:-1,j]
 components['nav']=r['nav'][:-1]
 return components

def validate_book(st,r):
 O=st['O'];L=r['ledger'];U=r['primary_units'];DU=r['defensive_units'];F=r['free_cash']
 next_nav=((U[:-1]+DU[:-1])*O[1:]).sum(axis=1)+F[:-1]
 opening=np.r_[1.,((U[:-1]+DU[:-1])*O[1:]).sum(axis=1)+F[:-1]]
 assert np.max(abs(next_nav-r['nav'][:-1]))<1e-10
 assert np.max(abs(opening-L[:,0]))<1e-10
 assert np.max(abs(L[:-1,25]))<1e-10
 lr=np.log(next_nav/opening[:-1]);dates=pd.to_datetime(st['dates'][1:]);checks=[]
 for z in metrics(st,r):
  mask=(dates>=pd.Timestamp(z['first_valuation']))&(dates<=pd.Timestamp(z['last_valuation']))
  growth=np.prod(next_nav[mask]/opening[:-1][mask]);wealth=np.r_[1.,np.cumprod(np.exp(lr[mask]))]
  values={'cagr':growth**(252/mask.sum())-1,'period_return':growth-1,
    'maxdd':np.min(wealth/np.maximum.accumulate(wealth)-1)}
  err=max(abs(values[k]-z[k]) for k in values)
  assert err<5e-11,(z['period'],err)
  checks.append(dict(period=z['period'],maximum_metric_error=err))
 return dict(intervals=len(lr),nav_error=float(np.max(abs(next_nav-r['nav'][:-1]))),metrics=checks)

def main(market,fee):
 out=ROOT/'results';(out/'paths').mkdir(parents=True,exist_ok=True);(out/'daily').mkdir(exist_ok=True)
 q=dict(np.load(PARENT/f'inputs/{market}_STATE_HALF.npz',allow_pickle=False))
 cal=read(PARENT/f'inputs/{market}_CALENDAR.csv');scores=read(PARENT/f'results/{market}_SCORES.csv.gz')
 rows=[];checks=[];props=[];start=time.time()
 for v in VARIANTS:
  st,ev,dec=adapt_state(q,cal,scores,v+'_FUSION');dec['variant']=v;dec['market']=market;props.append(dec)
  for mode,(ex,sp) in SCENARIOS.items():
   key=f'{market}_{v}_{mode}_{round(fee*10000)}'
   r=simulate(st,ev,fee=fee,exposure_timing=ex,stop_timing=sp)
   audit=validate_book(st,r);audit.update(key=key,market=market,variant=v,scenario=mode,fee=fee)
   if mode in ['LEGACY','ALL_PREOPEN']:
    old=original_simulate(st,ev,fee=fee,lag_systemic=mode=='ALL_PREOPEN')
    for k in old:np.testing.assert_array_equal(r[k],old[k])
    audit['parent_engine_exact']=True
    if v in ['ORIGINAL','CUM_FIT']:
     oracle=np.load(PARENT/f'inputs/oracles/{market}_{v}_IMMEDIATE_{"FULL" if mode=="LEGACY" else "LAG1"}_C{round(fee*10000)}.npz')
     for k in r:np.testing.assert_array_equal(r[k],oracle[k])
     audit['archived_path_exact']=True
   np.savez_compressed(out/f'paths/{key}.npz',dates=st['dates'],tickers=st['tickers'],**r)
   daily=monthly_attribution(st,r);daily.to_csv(out/f'daily/{key}.csv.gz',index=False)
   rows.extend(dict(market=market,variant=v,scenario=mode,fee=fee,**z) for z in metrics(st,r))
   checks.append(audit)
   pd.DataFrame(rows).to_csv(out/f'SCORECARD_{market}_{round(fee*10000)}.csv',index=False)
   (out/f'CHECKS_{market}_{round(fee*10000)}.json').write_text(json.dumps(checks,indent=2))
  print('DONE',market,v,fee,round(time.time()-start,1),flush=True)
 pd.concat(props).to_csv(out/f'PROPOSALS_{market}.csv',index=False)
if __name__=='__main__':
 a=argparse.ArgumentParser();a.add_argument('--market',choices=['EU','USA'],required=True);a.add_argument('--fee',type=float,required=True);x=a.parse_args();main(x.market,x.fee)
