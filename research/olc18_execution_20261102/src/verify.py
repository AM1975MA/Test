"""Fresh model-free replay verification, event-fee checks and chronological boundaries."""
from pathlib import Path
import json,sys
import numpy as np
from run_experiment import ROOT,VARIANTS
from stop_engine import simulate

def main():
 checks=[x for p in (ROOT/'results').glob('AUDIT_*.json') for x in json.loads(p.read_text())['completed']]
 verified=[];prefix=[];zero=[]
 for m in ('EU','USA'):
  for v in VARIANTS:
   q=dict(np.load(ROOT/f'inputs/{m}_{v}.npz',allow_pickle=False));ev=q.pop('events')
   for a in [x for x in checks if x['market']==m and x['variant']==v]:
    r=simulate(q,ev,contract=a['contract'],fee=a['fee'],friction=a['friction'])
    s=dict(np.load(ROOT/f"results/paths/{a['key']}.npz",allow_pickle=False))
    for k in r:np.testing.assert_array_equal(r[k],s[k])
    verified.append(a['key'])
   for policy in ('EOD_LOW','EOD_CLOSE'):
    gross=simulate(q,ev,contract=policy,fee=0,friction=0)
    net=simulate(q,ev,contract=policy+'_NET',fee=0,friction=0)
    err=float(np.max(abs(gross['nav']-net['nav'])))
    assert err<1e-10
    zero.append(dict(market=m,variant=v,contract=policy,max_nav_error=err))
  q=dict(np.load(ROOT/f'inputs/{m}_TOP2_CONTEXT_REVALUE.npz'));ev=q.pop('events');k=1100
  for policy in ('PREARM_WEAK','PREARM_ALL','EOD_LOW','EOD_CLOSE','EOD_LOW_NET','EOD_CLOSE_NET'):
   a=[];base=simulate(q,ev,contract=policy,event_log=a)
   pert={n:z.copy() for n,z in q.items()}
   for name in ('O','L','C'):pert[name][k:]*=1.31
   pert['gap'][k:]=-.4;pert['ud1'][k:]=1.;pert['uneg'][k:]=1.
   b=[];new=simulate(pert,ev,contract=policy,event_log=b)
   np.testing.assert_array_equal(base['nav'][:k-1],new['nav'][:k-1])
   np.testing.assert_array_equal(base['primary_units'][:k-1],new['primary_units'][:k-1])
   prefix.append(dict(market=m,contract=policy,checked_before_index=k-1))
  print('VERIFIED',m,flush=True)
 result=dict(paths=len(verified),keys=verified,zero_cost_gross_net=zero,prefix_checks=prefix,
             note='Zero-cost gross/net economic equivalence is not calibrated live transaction costs.')
 (ROOT/'results/FINAL_VERIFICATION.json').write_text(json.dumps(result,indent=2))
 print('TOTAL',len(verified),'zero_cost_pairs',len(zero),'prefix',len(prefix))
if __name__=='__main__':main()
