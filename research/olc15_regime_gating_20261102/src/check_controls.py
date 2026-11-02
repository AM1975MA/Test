"""Exactly reproduce the parent signal, accounting and execution contracts."""
from io_utils import ROOT,MARKETS,readcsv,dump
from portfolio_adapter import adapt_state
from portfolio_metrics_parent import policy_args
from vector_engine import simulate
from core import compose_current
import numpy as np,pandas as pd,time

def main():
 rows=[];t=time.time()
 for m in MARKETS:
  q=dict(np.load(ROOT/f'inputs/{m}_STATE_HALF.npz',allow_pickle=False));cal=readcsv(ROOT/f'inputs/{m}_CALENDAR.csv');s=readcsv(ROOT/f'inputs/{m}_MEAN3_SCORES.csv.gz')
  dates=pd.DatetimeIndex(sorted(s.signal_date.unique()));ticks=sorted(s.ticker.unique());di=dates.get_indexer(s.signal_date);ti=pd.Index(ticks).get_indexer(s.ticker)
  mat=lambda c:s.pivot(index='signal_date',columns='ticker',values=c).reindex(index=dates,columns=ticks).to_numpy(float)
  for v in ['ORIGINAL','CUM_FIXED','CUM_FIT']:
   a,b=compose_current(mat('RETURN'),mat(v+'_MAPPED'))
   np.testing.assert_allclose(a[di,ti],s[v+'_SMOOTH'],atol=2e-15,rtol=0);np.testing.assert_allclose(b[di,ti],s[v+'_FUSION'],atol=2e-15,rtol=0)
   recomputed=s[['signal_date','ticker']].copy();recomputed['old']=s[v+'_FUSION'];recomputed['new']=b[di,ti]
   for _,gg in recomputed.groupby('signal_date'):
    assert gg.sort_values(['old','ticker'],ascending=[False,True]).ticker.head(2).tolist()==gg.sort_values(['new','ticker'],ascending=[False,True]).ticker.head(2).tolist()
   st,ev,_=adapt_state(q,cal,s,v+'_FUSION')
   for mode in ['FULL','LAG1']:
    for policy in ['IMMEDIATE','DELAY3','PHASE5'] if mode=='FULL' else ['IMMEDIATE']:
     for fee in [.001,.003]:
      key=f'{m}_{v}_{policy}_{mode}_C{round(fee*10000)}';r=simulate(st,ev,fee=fee,lag_systemic=mode=='LAG1',**policy_args(policy))
      o=np.load(ROOT/'inputs/oracles'/f'{key}.npz')
      errors={}
      for k in r:
       errors[k]=float(np.max(abs(r[k]-o[k])))
       np.testing.assert_allclose(r[k],o[k],atol=5e-12,rtol=5e-13,err_msg=f'{key}:{k}')
      for k in ['primary_units','defensive_units']:
       np.testing.assert_array_equal(np.abs(np.diff(r[k],axis=0))>1e-10,np.abs(np.diff(o[k],axis=0))>1e-10)
      np.testing.assert_array_equal(r['ledger'][:,[3,8,9,10,11,19]],o['ledger'][:,[3,8,9,10,11,19]])
      rows.append(dict(key=key,bitwise=all(x==0 for x in errors.values()),errors=errors,decisions_exact=True,intervals=len(st['dates'])-1))
      dump(ROOT/'results/PARENT_PARITY.json',dict(paths=len(rows),checks=rows,seconds=time.time()-t));print('CONTROL',len(rows),key,flush=True)
 print('CONTROLS_COMPLETE',len(rows),'seconds',round(time.time()-t,1))
if __name__=='__main__':main()
