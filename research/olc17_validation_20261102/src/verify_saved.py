"""Reload complete saved paths and reproduce with the final hash-checked engine."""
import json,sys,warnings
import numpy as np
from run_validation import ROOT,PARENT,read,adapt_state,simulate,SCENARIOS
from run_v6_validation import v6_inputs
from v6_rebuild import rebuild

def main(m):
 checks=[]
 for pattern in ['CHECKS_*.json','V6_CHECKS_*.json']:
  checks += [x for p in (ROOT/'results').glob(pattern) for x in json.loads(p.read_text()) if x['market']==m]
 q=dict(np.load(PARENT/f'inputs/{m}_STATE_HALF.npz'));cal=read(PARENT/f'inputs/{m}_CALENDAR.csv');sc=read(PARENT/f'results/{m}_SCORES.csv.gz')
 states={};results=[];ctx,allow=v6_inputs(q,m)
 with warnings.catch_warnings():
  warnings.filterwarnings('ignore',category=RuntimeWarning)
  for a in checks:
   v=a['variant'];withv6=a['scenario'].endswith('_V6');mode=a['scenario'].removesuffix('_V6');key=(v,withv6)
   if key not in states:
    st,ev,_=adapt_state(q,cal,sc,v+'_FUSION')
    if withv6:st['alt']=rebuild(ctx,st['d1'],st['d2'],st['weights'],allow)
    states[key]=(st,ev)
   st,ev=states[key];ex,sp=SCENARIOS[mode];r=simulate(st,ev,fee=a['fee'],exposure_timing=ex,stop_timing=sp)
   saved=np.load(ROOT/f"results/paths/{a['key']}.npz")
   for col in r:np.testing.assert_array_equal(r[col],saved[col])
   results.append(a['key'])
  st,ev=states['TOP2_CONTEXT_REVALUE',False];k=1000;prefix=[]
  for mode in ['LEGACY','ALL_PREOPEN']:
   ex,sp=SCENARIOS[mode];base=simulate(st,ev,exposure_timing=ex,stop_timing=sp);pert={n:v.copy() for n,v in st.items()}
   for name in ['O','C','L']:pert[name][k:]*=1.37
   pert['gap'][k:]=-.3;pert['ud1'][k:]=1.;pert['uneg'][k:]=1.
   new=simulate(pert,ev,exposure_timing=ex,stop_timing=sp)
   np.testing.assert_array_equal(base['primary_units'][:k],new['primary_units'][:k]);np.testing.assert_array_equal(base['nav'][:k-1],new['nav'][:k-1]);prefix.append(mode)
  v=dict(ctx);v['C']=ctx['C'].copy();v['C'][k:]*=1.51
  np.testing.assert_array_equal(rebuild(ctx,allowed=allow)[:,:k],rebuild(v,allowed=allow)[:,:k])
 result=dict(market=m,paths_reproduced_exactly=len(results),keys=results,execution_prefix_checks=prefix,v6_prefix_check=True)
 (ROOT/f'results/FINAL_RELOAD_{m}.json').write_text(json.dumps(result,indent=2));print(m,len(results),'EXACT; prefix checks pass')
if __name__=='__main__':main(sys.argv[1])
