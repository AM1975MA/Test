from benchmarks21 import *

def main():
 p=np.load(ROOT/'BENCHMARK_INPUTS.npz');checks=[]
 for m,items in MAP.items():
  ds=pd.DatetimeIndex(p[m+'_dates'])
  for name in ['SP500','NASDAQ100']:
   O=p[m+'_'+name+'_O'];C=p[m+'_'+name+'_C'];obs=p[m+'_'+name+'_observed']
   a,o,s=simulate(ds,O,C,obs,'SMA10_MONTHLY')
   for date in ['2021-06-15','2023-11-15','2025-03-14']:
    cut=ds.searchsorted(date);changed=C.copy();changed[cut:]*=1.7
    b,oo,ss=simulate(ds,O,changed,obs,'SMA10_MONTHLY');n=ds.searchsorted(date)-ds.searchsorted('2020-01-02');assert np.array_equal(a[:n+1],b[:n+1]);checks.append(dict(market=m,benchmark=name,mutation_date=date,prefix_nav_identical=True))
   # Independent order replay, including pending orders executed on later observed openings.
   cash=10000.;qty=0.;bydate={x['date']:x for x in o};start=ds.searchsorted('2020-01-02');end=ds.searchsorted('2026-07-01');ind=[]
   for k in range(start,end+1):
    ind.append((cash+qty*O[k])/10000);order=bydate.get(str(ds[k].date()))
    if order:
     assert obs[k];sign=1 if order['side']=='BUY' else -1;qty+=sign*order['quantity'];cash-=sign*order['quantity']*order['price']+order['cost']
   assert np.max(abs(a-np.array(ind)))<1e-12
 (ROOT/'ADDITIONAL_QA.json').write_text(json.dumps(dict(status='PASS',prefix_checks=checks,independent_order_replays=6),indent=2))
 print('VERIFIED',len(checks),6)
if __name__=='__main__':main()
