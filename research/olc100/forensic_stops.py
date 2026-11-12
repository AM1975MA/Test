import sys,json
from pathlib import Path
import numpy as np,pandas as pd
sys.path.insert(0,'/mnt/data/olc100_full_native')
import run_forward_native as x
us=pd.read_pickle('/mnt/data/olc100_native/p0/results/calendar/USA_CLOSE.pkl')
results=[]
for m in ['EU','USA']:
 q,w,old_D,_,_,_,_=x.build_extended(m,'TOP2_CONTEXT_REVALUE',us)
 ds=pd.DatetimeIndex(q['dates'])
 for arm in ['B_BASE','C_CANDIDATE','D_TIMING','D_ALLOCATION']:
  y={k:v.copy() for k,v in q.items()}
  if x.ARMS[arm][1]=='MINVAR63':y['weights']=w
  rec=[];order=[]
  r=x._impl({k:v for k,v in y.items() if k!='events'},y['events'],policy='DELAY' if x.ARMS[arm][2]=='DELAY3' else 'IMMEDIATE',fraction=3 if x.ARMS[arm][2]=='DELAY3' else 1,fee=.001,exposure_timing='PREVIOUS',stop_timing='NOW',stop_friction=.001,ordinary_alarm=False,fast_stop=True,lock_days=3,event_log=rec,order_log=order)
  for e in rec:
   i=e['signal_index']
   if i<old_D-1:continue
   results.append({**{'market':m,'arm':arm,'date':str(ds[i].date())},**{k:v for k,v in e.items() if k!='signal_index'}})
   if pd.Timestamp('2026-08-03')<=ds[i]<pd.Timestamp('2026-09-01'):
    print('AUG STOP',m,arm,str(ds[i].date()),e['ticker'],'openbreach',e['opening_breach'],'barrier',round(e['barrier'],4),'rawfill',round(e['raw_price'],4),'newly_bought',e['newly_bought_quantity'],'carried',e['carried_quantity'],flush=True)
  if m=='USA' and arm in ['B_BASE','D_TIMING']:
   ix=ds.get_loc('2026-08-03');iy=ds.get_loc('2026-09-01')
   print(m,arm,'Aug gross',r['ledger'][ix:iy,1].mean(),'Aug stop',r['ledger'][ix:iy,8].sum(),flush=True)
pd.DataFrame(results).to_csv('/mnt/data/olc100_full_native/results/OLC100_NEW_NATIVE_STOPS.csv',index=False)
