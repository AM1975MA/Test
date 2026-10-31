"""Full frozen-score policy factorial. No fitting or optimization."""
from pathlib import Path
import json,itertools,time,hashlib,warnings
import numpy as np,pandas as pd
from engine_prepare import B,SRC,stage,producer,v6,prepare
from instrumented_engine import simulate_instrumented
from reconcile_math import log_returns
warnings.filterwarnings('ignore',message='Mean of empty slice')
warnings.filterwarnings('ignore',category=FutureWarning)
OUT=B/'results';OUT.mkdir(exist_ok=True)
NAMES=['CONCENTRATION','DD_GROSS','V6','SYSTEMIC_GAP','STOPS','COSTS']
LEDGER=['opening_nav','target_gross','weight1','alt_weight','rebalance','turnover','rebalance_fee','stop1','stop2','stop_fee','stop_slippage','poststop_open_value1','poststop_open_value2','poststop_open_alt_value','poststop_open_BIL','poststop_open_SHV','free_cash','systemic_trigger','cooldown','proposed1','proposed2','alternate','stopped_notional','postrebalance_nav']
rows=[];parities=[];t=time.time()
for arm in ['B_T1_H1','R_T0_H1']:
 for vintage in (1,2,3):
  q=prepare(vintage,arm)
  folder=OUT/'policy_paths'/arm/f'r{vintage}';folder.mkdir(parents=True,exist_ok=True)
  built={}
  for W,G in itertools.product((False,True),repeat=2):
   alloc=q['alloc'] if W else producer.AllocationResult(q['alloc'].d1,q['alloc'].d2,np.full_like(q['alloc'].weight1,.5),np.zeros_like(q['alloc'].margin))
   gross=q['gross'] if G else np.ones_like(q['gross']);g=q['g'] if G else np.ones_like(q['g'])
   weight=stage.confidence_weights(alloc,g,q['agreement'],np.zeros_like(q['agreement']),mode='current_plus_models_riskoff') if W else alloc.weight1
   alt=v6.build_v6_state(q['close'],alloc.d1,alloc.d2,alloc.weight1,gross).alt_idx
   built[(W,G)]=(alloc,weight,g,alt)
  for mask in range(64):
   W,G,V,S,P,C=[bool(mask&(1<<i)) for i in range(6)]
   alloc,w,g,alt=built[(W,G)];ex=q['ex']
   args=[alloc.d1,alloc.d2,w]+[ex[k] for k in ['O','L','C','PC','gap','ud1','uneg','UH','SA']]+[q['tickers'].index('BIL'),q['tickers'].index('SHV'),np.tile(g,(1,1)),g,alt,V]
   E,T,X,AW,ledger=simulate_instrumented(*args,cost=.001 if C else 0.,stop=.055,slip=.001 if C else 0.,systemic_enabled=S,stops_enabled=P)
   assert np.isfinite(E).all() and (E>0).all()
   if mask==63:
    err={name:float(np.max(np.abs(x-y))) for name,x,y in zip(['equity','turnover','gross','alt_weight'],[E,T,X,AW],q['canonical'])}
    assert max(err.values())<1e-12,(arm,vintage,err)
    parities.append(dict(arm=arm,vintage=vintage,original_vs_archive=q['errors'],instrumented_vs_original=err))
   lr=log_returns(E[0]);dd=E[0]/np.maximum.accumulate(np.r_[1.,E[0]])[1:]-1
   before=ledger[0,:,0];valid=before>0;fees=ledger[0,:,6]+ledger[0,:,9]+ledger[0,:,10]
   row=dict(arm=arm,vintage=vintage,mask=mask,**dict(zip(NAMES,[int(W),int(G),int(V),int(S),int(P),int(C)])),cagr=float(np.expm1(lr.mean()*252)),ann_log=float(lr.mean()*252),maxdd=float(dd.min()),terminal_equity=float(E[0,-1]),annual_turnover=float(T.mean()*252),n_rebalances=int(ledger[0,:,4].sum()),n_systemic_triggers=int(ledger[0,:,17].sum()),n_stop_executions=int(ledger[0,:,7:9].sum()),mean_target_gross=float(X[0,:-1].mean()),mean_alt_weight=float(AW[0,:-1].mean()),days_alt=int(np.count_nonzero(AW[0,:-1])),normalized_fee_slippage_sum=float(np.divide(fees,before,out=np.zeros_like(fees),where=valid).sum()))
   rows.append(row)
   np.savez_compressed(folder/f'{mask:02d}.npz',dates=q['dates'].values,nav=E[0],turnover=T[0],gross=X[0],alt_weight=AW[0],ledger=ledger[0])
  pd.DataFrame(rows).to_csv(OUT/'POLICY_FACTORIAL.csv',index=False)
  (OUT/'PARITY.json').write_text(json.dumps(parities,indent=2))
  (folder/'TICKERS.json').write_text(json.dumps(q['tickers']))
  print('FINISHED',arm,'vintage',vintage,'n_replays',len(rows),'seconds',round(time.time()-t,2),flush=True)
(OUT/'LEDGER_COLUMNS.json').write_text(json.dumps(LEDGER,indent=2))
manifest=dict(frozen_engine_commit='13443836649d0f107d2063eb7acc1039135d6e9b',n_new_policy_replays=len(rows),new_model_fits=0,policy_names=NAMES,archive_inputs={name:hashlib.sha256((B.parent/name).read_bytes()).hexdigest() for name in ['compact21-tail-factorial-full.zip','tail-only-allocation-counterfactual-full.zip','yfinance-repeatability-v1-raw.zip']},code_hashes={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in (B/'work').glob('*.py')},source_files={str(p.relative_to(SRC)):hashlib.sha256(p.read_bytes()).hexdigest() for p in [SRC/'vendor/p45/v2_stage19_kernel.py',SRC/'vendor/etf_trader_v2/src/etf_trader/ma3/producer.py',SRC/'vendor/etf_trader_v2/src/etf_trader/ma3/ddfirst.py',SRC/'vendor/etf_trader_v2/src/etf_trader/ma3/v6.py']},warning='Frozen-score historical replay; raw data quality and new model training not independently validated; three raw revisions are correlated, not three markets.')
(OUT/'RUN_MANIFEST.json').write_text(json.dumps(manifest,indent=2))
print('ALL_DONE',len(rows),time.time()-t,flush=True)
