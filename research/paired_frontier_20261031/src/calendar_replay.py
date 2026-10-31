"""Component grafts and matched full-calendar tests, preserving original risk engine."""
from native_screen import *
CAL=ROOT/'results/calendar';DEST=ROOT/'results/rebuilt';DEST.mkdir(exist_ok=True)
for sub in ['paths','states']:(DEST/sub).mkdir(exist_ok=True)
def new_hybrid(et,x):
 t=.6*et.to_numpy()+.4*x.to_numpy();h=available_lag_hybrid(et.to_numpy(),x.to_numpy())
 return pd.DataFrame(h,index=et.index,columns=et.columns)
def crop(q,first):
 ds=pd.DatetimeIndex(q['dates']);ok=ds>=pd.Timestamp(first);D=len(ds);out={}
 for k,v in q.items():
  if k=='tickers':out[k]=v.copy()
  elif v.ndim==2 and v.shape[0]==1 and v.shape[1]==D:out[k]=v[:,ok].copy()
  elif v.shape[0]==D:out[k]=v[ok].copy()
  else:out[k]=v.copy()
 return out

def run():
 global OUT
 # make_selectors writes model audit under native_screen.OUT; redirect that module explicitly.
 import native_screen as ns;ns.OUT=DEST
 rows=[];supportrows=[];start=time.time();count=0;bridges=[]
 for market in ['EU','USA']:
  assert (CAL/f'{market}_FIT_COMPLETE.json').exists()
  q,h,C,oldr,oldh,olde,oldx,oldcal=load(market)
  q=crop(q,'2019-02-01');h=crop(h,'2019-02-01')
  p=pd.read_csv(CAL/f'{market}_FORECASTS.csv.gz',parse_dates=['signal_date'])
  fullcal=pd.read_csv(CAL/f'{market}_CALENDAR.csv',parse_dates=['signal_date','entry_date','exit_date']);fullcal=fullcal[(fullcal.signal_date>='2019-01-01')&(fullcal.signal_date<='2026-06-30')].reset_index(drop=True)
  oldcal=oldcal[oldcal.signal_date>='2019-01-01'].reset_index(drop=True)
  def matrix(col,cal):return p.pivot(index='signal_date',columns='ticker',values=col).reindex(index=cal.signal_date,columns=oldr.columns)
  # Complete current predictions mandatory; missing lags handled identically to AVAILABLE control.
  r=matrix('RETURN',fullcal);et=matrix('ET',fullcal);xx=matrix('XGB',fullcal);hy=new_hybrid(et,xx)
  cal=fullcal;dates=pd.DatetimeIndex(q['dates']);rawO=pd.read_pickle(CAL/f'{market}_OPEN.pkl')
  for i,sd in enumerate(r.index):supportrows.append({'market':market,'signal_date':sd,'return':int(r.iloc[i].notna().sum()),'hybrid':int(hy.iloc[i].notna().sum()),'combined':int((r.iloc[i].notna()&hy.iloc[i].notna()).sum())})
  # Graft controls share the archived native monthly schedule, isolating substituted forecast streams.
  rold=oldr.reindex(oldcal.signal_date);hold=oldh.reindex(oldcal.signal_date);eold=olde.reindex(oldcal.signal_date);xold=oldx.reindex(oldcal.signal_date)
  rn=r.reindex(oldcal.signal_date);en=et.reindex(oldcal.signal_date);xn=xx.reindex(oldcal.signal_date);hn=hy.reindex(oldcal.signal_date)
  grafts=[('NATIVE_REFERENCE',rold,hold,eold,xold,oldcal),('RETURN_REFIT',rn,hold,eold,xold,oldcal),('HYBRID_REFIT',rold,hn,en,xn,oldcal),('BOTH_REFIT_NATIVE_DATES',rn,hn,en,xn,oldcal)]
  for name,rr0,hh0,ee0,xx0,cc0 in grafts:
   score=.475*rr0+.525*hh0
   for half in [False,True]:
    wt='HALF' if half else 'ORIGINAL';st=state_with_score(q,C.copy(),score,ee0,xx0,cc0,market,half)
    for fee in [.001,.003]:
     config=f'{name}_PLAIN_{wt}_NONE_C{int(fee*10000)}';E,T,X,AW,L=simulate(st,np.ones(len(st['dates'])),fee,market)
     assert np.max(abs(L[0,:-1,46]))<1e-9
     np.savez_compressed(DEST/'paths'/f'{market}_{config}.npz',dates=st['dates'],nav=E[0],ledger=L[0])
     for row in metrics(E[0],L[0],pd.DatetimeIndex(st['dates'])):rows.append(dict(market=market,support='GRAFT',selector=name,construction='PLAIN',weight=wt,defense='NONE',fee=fee,config=config,**row))
     count+=1
  scoremap,yy=make_selectors(market,C,r,hy,cal,rawO,'REBUILT')
  caps0=market_defenses(C,dates)
  for selector,score in scoremap.items():
   score.to_csv(DEST/f'{market}_{selector}_SCORES.csv')
   methods=['PLAIN','CORR','BUFFER','CORR_BUFFER'] if selector in ['LEGACY','CAL2'] else ['PLAIN']
   for method in methods:
    s=construction(score,C,cal,method)
    for half in [False,True]:
     wt='HALF' if half else 'ORIGINAL';st=state_with_score(q,C.copy(),s,et,xx,cal,market,half)
     caps=dict(caps0) if selector in ['LEGACY','CAL2'] else {'NONE':np.ones(len(dates))}
     if selector in ['LEGACY','CAL2']:
      v=volcap(C,st);caps.update(VOL20=v,SYS_VOL=np.minimum(caps0['SYS_FAST'],v))
     np.savez_compressed(DEST/'states'/f'{market}_{selector}_{method}_{wt}.npz',dates=st['dates'],d1=st['d1'],d2=st['d2'],weights=st['weights'],alt=st['alt'])
     for defense,cap in caps.items():
      for fee in [.001,.003]:
       config=f'REBUILT_{selector}_{method}_{wt}_{defense}_C{int(fee*10000)}';E,T,X,AW,L=simulate(st,cap,fee,market)
       assert np.max(abs(L[0,:-1,46]))<1e-9 and np.isfinite(E).all() and E.min()>0
       assert np.max(X[0,:-1]+AW[0,:-1]-cap[:-1])<1e-12
       np.savez_compressed(DEST/'paths'/f'{market}_{config}.npz',dates=st['dates'],nav=E[0],ledger=L[0],cap=cap)
       for row in metrics(E[0],L[0],pd.DatetimeIndex(st['dates'])):rows.append(dict(market=market,support='REBUILT',selector=selector,construction=method,weight=wt,defense=defense,fee=fee,config=config,**row))
       count+=1
    print('REPLAY',market,selector,method,'paths',count,'elapsed',round(time.time()-start),flush=True)
  pd.DataFrame(rows).to_csv(DEST/'SCORECARD.csv',index=False);pd.DataFrame(supportrows).to_csv(DEST/'COVERAGE.csv',index=False)
 print('REBUILT_COMPLETE',count,flush=True)
if __name__=='__main__':run()
