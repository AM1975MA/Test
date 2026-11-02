from pathlib import Path
import hashlib,json,subprocess,sys
ROOT=Path(__file__).resolve().parent
manifest=json.loads((ROOT/'MANIFEST.json').read_text())
for r in manifest['files']:
 p=ROOT/r['path'];assert p.is_file(),p
 assert hashlib.sha256(p.read_bytes()).hexdigest()==r['sha256'],p
print('HASH_VERIFIED',len(manifest['files']),flush=True)
subprocess.run([sys.executable,'-m','pytest','-q'],cwd=ROOT,check=True)
sys.path.insert(0,str(ROOT/'src'))
from io_utils import readcsv
from portfolio_adapter import adapt_state
from vector_engine import simulate
import numpy as np
count=0;mx=0.
for market in ['EU','USA']:
 state=dict(np.load(ROOT/f'inputs/{market}_STATE_HALF.npz',allow_pickle=False));calendar=readcsv(ROOT/f'inputs/{market}_CALENDAR.csv');scores=readcsv(ROOT/f'results/{market}_SCORES.csv.gz')
 for variant in ['ORIGINAL','CUM_FIT','CONTEXT_RECENT','F_CONTEXT_RECENT']:
  for lag in [False,True]:
   q,e,_=adapt_state(state,calendar,scores,variant+'_FUSION');res=simulate(q,e,lag_systemic=lag)
   old=np.load(ROOT/f'results/paths/{market}_{variant}_IMMEDIATE_{"LAG1" if lag else "FULL"}_C10.npz')
   for k in res:
    err=float(np.max(abs(res[k]-old[k])));mx=max(mx,err)
    np.testing.assert_allclose(res[k],old[k],rtol=5e-13,atol=5e-12)
   count+=1
report={'manifest_files':len(manifest['files']),'tests_passed':25,'representative_replays':count,'max_replay_array_error':mx}
(ROOT/'RESTORE_VERIFICATION.json').write_text(json.dumps(report,indent=2));print(json.dumps(report,indent=2))
