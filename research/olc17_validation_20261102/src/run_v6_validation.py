"""Holdings-consistent V6, admitted only after exact parent alternate-stream parity."""
from pathlib import Path
import json,warnings
import numpy as np,pandas as pd
from run_validation import ROOT,PARENT,VARIANTS,read,adapt_state,simulate,validate_book,monthly_attribution,metrics
from v6_rebuild import rebuild

def v6_inputs(q,market):
 v=dict(q);allowed=None
 if market=='EU':
  extra=dict(np.load(ROOT/'inputs/EU_V6_CONTEXT.npz'));np.testing.assert_array_equal(extra['dates'],q['dates'])
  assert (extra['SPY_source_date']<q['dates']).all()
  v['C']=extra['C'];v['tickers']=extra['tickers'];allowed=extra['allowed']
 return v,allowed

def run(market):
 checks=json.loads((ROOT/'results/V6_PARENT_PARITY_FINAL.json').read_text());assert all(x['parent_alt_exact'] for x in checks)
 q=dict(np.load(PARENT/f'inputs/{market}_STATE_HALF.npz'));cal=read(PARENT/f'inputs/{market}_CALENDAR.csv');scores=read(PARENT/f'results/{market}_SCORES.csv.gz')
 ctx,allowed=v6_inputs(q,market);rows=[];audits=[];stream=[]
 with warnings.catch_warnings():
  warnings.filterwarnings('ignore',message='All-NaN slice encountered');warnings.filterwarnings('ignore',message='Degrees of freedom <= 0 for slice.');warnings.filterwarnings('ignore',message='Mean of empty slice')
  np.testing.assert_array_equal(rebuild(ctx,allowed=allowed),q['alt'])
  for v in VARIANTS:
   st,ev,_=adapt_state(q,cal,scores,v+'_FUSION');alt=rebuild(ctx,st['d1'],st['d2'],st['weights'],allowed)
   assert not np.any((alt>=0)&((alt==st['d1'])|(alt==st['d2'])))
   change=(alt!=q['alt'])[0]
   for k in np.flatnonzero(change):stream.append(dict(market=market,variant=v,date=str(q['dates'][k])[:10],old=str(q['tickers'][q['alt'][0,k]]) if q['alt'][0,k]>=0 else 'CASH',new=str(q['tickers'][alt[0,k]]) if alt[0,k]>=0 else 'CASH'))
   st['alt']=alt
   for mode in ['LEGACY','ALL_PREOPEN']:
    for fee in [.001,.003]:
     tag=mode+'_V6';key=f'{market}_{v}_{tag}_{round(fee*10000)}'
     ex='NOW' if mode=='LEGACY' else 'PREVIOUS'
     r=simulate(st,ev,fee=fee,exposure_timing=ex,stop_timing=ex)
     a=validate_book(st,r);a.update(key=key,market=market,variant=v,scenario=tag,fee=fee);audits.append(a)
     np.savez_compressed(ROOT/f'results/paths/{key}.npz',dates=st['dates'],tickers=st['tickers'],**r)
     monthly_attribution(st,r).to_csv(ROOT/f'results/daily/{key}.csv.gz',index=False)
     rows.extend(dict(market=market,variant=v,scenario=tag,fee=fee,**z) for z in metrics(st,r))
   print(market,v,'alt changes',int(change.sum()),flush=True)
 pd.DataFrame(rows).to_csv(ROOT/f'results/V6_SCORECARD_{market}.csv',index=False)
 pd.DataFrame(stream).to_csv(ROOT/f'results/V6_CHANGED_STREAM_{market}.csv',index=False)
 (ROOT/f'results/V6_CHECKS_{market}.json').write_text(json.dumps(audits,indent=2))
if __name__=='__main__':
 import sys;run(sys.argv[1])
