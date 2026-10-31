from research_common import B
from run_audited_replays import replay,OUT
import numpy as np,pandas as pd,json
rows=[]
for name in ['RETURN_MATCHED','HYBRID_MATCHED','MOM252_MATCHED']:
 q=dict(np.load(B/'inputs'/f'EU_STATE_{name}_HALF.npz',allow_pickle=False))
 for mode in ['full','no_risk','zero_cost']:
  rr,_=replay(q,name+'_HALF'+('' if mode=='full' else '_'+mode),'EU',mode=mode);rows+=rr
for weight in ['ORIGINAL','HALF']:
 q=dict(np.load(B/'inputs'/f'EU_STATE_ASOF1_RETURN_H_{weight}.npz',allow_pickle=False))
 for mode in ['full','no_risk']:
  rr,_=replay(q,'ASOF1_'+weight+('' if mode=='full' else '_'+mode),'EU',mode=mode);rows+=rr
# On the authenticated complete US score matrix, the identical missing-forecast operation has no effect.
a=pd.read_csv(B/'factorial/R_T0_H1/r1/ENSEMBLE_TAIL_OOS.csv',parse_dates=['signal_date'])
errs={}
for col in ['BASE','ET_TAIL','XGB_TAIL']:
 z=a.pivot(index='signal_date',columns='ticker',values=col)
 errs[col]={'missing_before':int(z.isna().sum().sum()),'max_abs_change':float(np.nanmax(abs(z.ffill(limit=1).to_numpy()-z.to_numpy())))}
assert all(r['missing_before']==0 and r['max_abs_change']==0 for r in errs.values())
(OUT/'ASOF1_US_UNCHANGED.json').write_text(json.dumps(errs,indent=2))
pd.DataFrame(rows).to_csv(OUT/'ADDITIONAL_SCORECARD.csv',index=False)
print('ADDITIONAL_DONE')
