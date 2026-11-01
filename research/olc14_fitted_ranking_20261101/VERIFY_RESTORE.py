"""Verify restored manifests and reproduce twelve real saved paths without network."""
from pathlib import Path
import hashlib,json,sys,time
import numpy as np
ROOT=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT/'src'))

def digest(p):
 h=hashlib.sha256()
 with p.open('rb') as f:
  for b in iter(lambda:f.read(4*1024*1024),b''):h.update(b)
 return h.hexdigest()

def main():
 started=time.time();verified={}
 for name in ['HEADS_MANIFEST.json','RESULTS_MANIFEST.json']:
  manifest=json.loads((ROOT/name).read_text())
  for r in manifest['files']:
   p=ROOT/r['path']
   if not p.is_file() or p.stat().st_size!=r['bytes'] or digest(p)!=r['sha256']:
    raise RuntimeError('Restored file mismatch: '+r['path'])
  verified[name]=len(manifest['files'])
 from common import P12,readcsv
 from portfolio_adapter import adapt_state
 from portfolio_metrics_parent import policy_args
 from vector_engine import simulate
 checks=[]
 for market in ['EU','USA']:
  state=dict(np.load(P12/f'inputs/{market}_STATE_HALF.npz',allow_pickle=False))
  calendar=readcsv(P12/f'inputs/{market}_CALENDAR.csv')
  scores=readcsv(ROOT/f'results/{market}_MEAN3_SCORES.csv.gz')
  for variant in ['ORIGINAL','CUM_FIT','INC_FIT']:
   scores[variant]=scores[variant+'_FUSION']
   q,events,_=adapt_state(state,calendar,scores,variant)
   for fee in [.001,.003]:
    result=simulate(q,events,fee=fee,lag_systemic=False,**policy_args('IMMEDIATE'))
    name=f'{market}_{variant}_IMMEDIATE_FULL_C{round(fee*10000)}'
    with np.load(ROOT/'results/paths'/f'{name}.npz',allow_pickle=False) as old:
     for k,v in result.items():np.testing.assert_array_equal(v,old[k],err_msg=name+'/'+k)
    checks.append({'path':name,'all_arrays_identical':True})
 report={'manifest_file_counts':verified,'real_portfolio_replays':checks,'elapsed_seconds':time.time()-started,'scope':'Hash verification of all archived files and twelve exact real replays; full model reload was separately completed in original verification.'}
 (ROOT/'RESTORE_VERIFICATION.json').write_text(json.dumps(report,indent=2))
 print(json.dumps(report,indent=2))
if __name__=='__main__':main()
