from research_common import B
import os
os.environ['RECONCILIATION_ROOT']=str(B)
from engine_prepare import prepare,stage
from instrumented_engine import simulate_instrumented
import numpy as np,json,time
q=prepare(1,'R_T0_H1')
np.savez_compressed(B/'inputs/US_STATE.npz',dates=q['dates'].values,tickers=q['tickers'],d1=q['alloc'].d1,d2=q['alloc'].d2,margin=q['alloc'].margin,basew=q['alloc'].weight1,weights=q['weights'],g=q['g'],gross=q['gross'],alt=q['alt'],**q['ex'])
print('ORIGINAL39_PARITY',q['errors'],flush=True)
a=q['alloc'];g=q['g'];ex=q['ex'];T=q['tickers'];x=[a.d1,a.d2,np.full_like(a.weight1,.5)]+[ex[k] for k in ['O','L','C','PC','gap','ud1','uneg','UH','SA']]+[T.index('BIL'),T.index('SHV'),np.tile(g,(1,1)),g,q['alt'],True,.001]
# RH50 recalculates V6 from equal base weights and zero margin.
from engine_prepare import v6
s=v6.build_v6_state(q['close'],a.d1,a.d2,np.full_like(a.weight1,.5),q['gross']);x[-3]=s.alt_idx
res=stage.simulate_arch(*x)
ref=np.load(B/'mediation/R_HALF/r1/FULL_UNIVERSE_PATH.npz',allow_pickle=False)
err=float(np.max(abs(res[0]-ref['equity'])));print('RH50_PARITY',err,flush=True);assert err<1e-12
np.savez_compressed(B/'inputs/US_RH50_ALT.npz',alt=s.alt_idx)
(B/'results/US_ORIGINAL_PARITY.json').write_text(json.dumps({'original39':q['errors'],'RH50_equity_error':err,'ref_full_original39_cagr':float(np.expm1(np.log(q['canonical'][0][0,-1])*252/len(q['dates']))),'ref_full_RH50_cagr':float(np.expm1(np.log(res[0][0,-1])*252/len(q['dates'])))},indent=2))
