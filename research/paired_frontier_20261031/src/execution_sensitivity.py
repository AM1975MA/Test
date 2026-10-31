"""Predeclared one-session-lag stress on legacy systemic-gap decisions; no retuning."""
from calendar_replay import crop
from native_screen import ROOT,load,simulate,metrics
import numpy as np,pandas as pd,json
O=ROOT/'results/execution';(O/'paths').mkdir(parents=True,exist_ok=True)
rows=[];n=0
for market in ['EU','USA']:
 q,h,C,rr,hy,et,xx,cal=load(market)
 for stage,configs in [('native',[('NATIVE_LEGACY','LEGACY'),('NATIVE_CAL2','CAL2')]),('rebuilt',[('LEGACY','LEGACY'),('R25','R25'),('CAL2','CAL2')])]:
  base=crop(q,'2019-02-01') if stage=='rebuilt' else q
  for prefix,selector in configs:
   for weight in ['ORIGINAL','HALF']:
    fname=f'{market}_{prefix}_PLAIN_{weight}.npz'
    st={k:v.copy() for k,v in base.items()};new=np.load(ROOT/'results'/stage/'states'/fname)
    for k in new.files:st[k]=new[k]
    for fld in ['gap','ud1','uneg']:st[fld]=np.concatenate([np.zeros_like(st[fld][:1]),st[fld][:-1]],axis=0)
    for fee in [.001,.003]:
     config=f'{stage}_{selector}_{weight}_LAG1_C{int(fee*10000)}';E,T,X,AW,L=simulate(st,np.ones(len(st['dates'])),fee,market)
     assert np.max(abs(L[0,:-1,46]))<1e-9
     np.savez_compressed(O/'paths'/f'{market}_{config}.npz',dates=st['dates'],nav=E[0],ledger=L[0])
     for row in metrics(E[0],L[0],pd.DatetimeIndex(st['dates'])):rows.append(dict(market=market,stage=stage,selector=selector,weight=weight,fee=fee,config=config,**row))
     n+=1
 print('LAG_DONE',market,n,flush=True)
pd.DataFrame(rows).to_csv(O/'SCORECARD.csv',index=False)
(O/'SUMMARY.json').write_text(json.dumps({'paths':n,'definition':'Only systemic gap/breadth inputs shifted one session. Not a definitive real-world fill model or systematic late-fill correction. All other legacy contracts held fixed.','no_retuning':True},indent=2))
