#!/usr/bin/env python3
"""OLC100 research-only native OLC19/OLC67 forward bridge.
No trading, no retrospective refitting. Frozen Top2 July-Oct are replayed
with original 2019-Jul account history. OHLC quality & execution not certified.
"""
from __future__ import annotations
import sys,math,io,json,hashlib,warnings,gzip
from pathlib import Path
from zipfile import ZipFile
import pandas as pd,numpy as np
BASE=Path('/mnt/data/olc100_full_native')
OUT=BASE/'results';OUT.mkdir(parents=True,exist_ok=True)
FROZEN=Path('/mnt/data/frozen_sources/OLC19_Rischio_Rientro_Checkpoint_20261102.zip')
REFROOT=Path('/mnt/data/olc100_workspace/OLC98_Model_Review_20261112/native/olc19_combined_risk_20261102')
QROOT=REFROOT/'restore/olc18_execution_20261102/inputs'
P0=Path('/mnt/data/olc100_native/p0')
FORWARD=Path('/mnt/data/OLC100_FORWARD_RESULT_20261112')
REFERENCE=REFROOT/'results/paths'
CAP=Path('/mnt/data/OLC100_CAPTURE_RECHECK_20261112.zip')
SRC=BASE/'srcfreeze'
sys.path[:0]=[str(SRC),str(REFROOT/'src'),str(REFROOT/'restore/olc18_execution_20261102/parent_archive/parent/olc16_contextual_rank_20261102/src')]
import ddfirst,v6
from combined_engine import _impl

ARMS={
'B_BASE':('CONTEXT','HALF','IMMEDIATE','FAST_LOCK3'),
'C_CANDIDATE':('CONTEXT','MINVAR63','DELAY3','FAST_LOCK3'),
'D_SELECTION':('ORIGINAL','HALF','IMMEDIATE','FAST_LOCK3'),
'D_ALLOCATION':('CONTEXT','MINVAR63','IMMEDIATE','FAST_LOCK3'),
'D_TIMING':('CONTEXT','HALF','DELAY3','FAST_LOCK3'),
'D_PROTECTION':('CONTEXT','HALF','IMMEDIATE','BASE'),
}
FIELDS=['nav','ledger','primary_units','defensive_units','free_cash','targets','risk_trace']
FREEZE_SHA='3b5799dae060c104408f581c70280cef8ce4d84c3978434d4e6ba81108f16540'

def read_q(m,which):
 with np.load(QROOT/f'{m}_{which}.npz',allow_pickle=False) as z:return {k:z[k].copy() for k in z.files}

def load_raw_new(m,t,days):
 p=(P0/'legacy/inputs/eu/source_v4/input/EU165_SPECIALISTS_20261029/prices' if m=='EU' else P0/'legacy/raw/_repeat1')/(t+'.csv')
 s=pd.read_csv(p,parse_dates=['date'],float_precision='round_trip').set_index('date').sort_index()
 s=s.reindex(days)
 return s

def external_macro_frame(dates,us):
 out=pd.DataFrame(index=dates)
 for t in ['SPY','HYG','IEF']:
  s=us[t].dropna();pos=s.index.searchsorted(dates,side='left')-1
  v=np.full(len(dates),np.nan);q=pos>=0;v[q]=s.to_numpy(float)[pos[q]]
  out[t]=v
 return out

def gross_stream(m,all_dates,orig,US_ALL):
 panel=pd.read_pickle(P0/f'results/calendar/{m}_CLOSE.pkl')
 if m=='EU':
  macro=external_macro_frame(panel.index,US_ALL)
  base=ddfirst.market_state
  import inspect
  ss=inspect.getsource(base).replace('def market_state(','def market_state_port(').replace('spy=close["SPY"]','spy=MACRO["SPY"]').replace('hygief=close["HYG"]/close["IEF"]','hygief=MACRO["HYG"]/MACRO["IEF"]')
  ns=ddfirst.__dict__.copy();ns['MACRO']=macro;exec(ss,ns)
  ddfirst.market_state=ns['market_state_port']
  try:gg=ddfirst.sync_c95_m75_gross(panel.ffill())
  finally:ddfirst.market_state=base
 else:gg=ddfirst.sync_c95_m75_gross(panel.ffill())
 rr=pd.Series(gg,index=panel.index).reindex(all_dates).to_numpy(float)
 if not np.isfinite(rr).all():raise AssertionError((m,'risk gross missing'))
 N=len(orig['dates']); old=orig['gross']
 # Verify clean last 180 days against original checkpoint; full early data need not be overwritten.
 assert np.array_equal(rr[N-180:N],old[-180:]),(m,'gross mismatch at frozen boundary')
 mapped=np.where(np.isclose(rr,.95),1.,np.where(np.isclose(rr,.75),.945,np.where(rr<=.251,.66,1.)))
 assert np.array_equal(mapped[N-180:N],orig['g'][-180:]),(m,'gross transformed mismatch')
 return rr[N:],mapped[N:],dict(last180_equals_frozen=True,forward_gross_counts={str(v):int(n) for v,n in zip(*np.unique(rr[N:],return_counts=True))})

def pair_from_original(m):
 x=pd.read_csv(FORWARD/f'{m}_OLC19_ORIGINAL_FORWARD_SCORES.csv')
 dates=[]
 for sig,group in x.groupby('signal_date',sort=True):
  gg=group.sort_values(['ORIGINAL_FUSION_REPRO','ticker'],ascending=[False,True],kind='mergesort').head(2)
  assert len(gg)==2
  dates.append(dict(signal_date=pd.Timestamp(sig),ticker1=gg.ticker.iloc[0],ticker2=gg.ticker.iloc[1]))
 return pd.DataFrame(dates)

def minvar_at(q,k):
 # OLC56 frozen B1_MINVAR63_CAP25, strictly from Close before the entry opening.
 if k<64:return .5,0
 a,b=int(q['d1'][0,k]),int(q['d2'][0,k]);
 if a==b or min(a,b)<0:return .5,0
 c=q['C'][k-64:k][:,[a,b]]
 obs=q.get('observed',np.ones_like(q['C'],bool))[k-64:k][:,[a,b]]
 good=np.all(obs[1:]&obs[:-1],axis=1)&np.all(np.isfinite(c[1:])&np.isfinite(c[:-1]),axis=1)&np.all((c[1:]>0)&(c[:-1]>0),axis=1)
 if good.sum()<math.ceil(.8*63):return .5,int(good.sum())
 xx=np.log(c[1:][good]/c[:-1][good]);cov=np.cov(xx.T,ddof=1)
 v1,v2,c12=float(cov[0,0]),float(cov[1,1]),float(cov[0,1]);den=v1+v2-2*c12
 return (.5 if den<=1e-13 or min(v1,v2)<=1e-15 else float(np.clip((v2-c12)/den,.25,.75))),int(good.sum())

def build_extended(m,source,US_ALL):
 q=read_q(m,source); old_D=len(q['dates']);original_end=pd.Timestamp(q['dates'][-1]);tickers=list(q['tickers'])
 panel_O=pd.read_pickle(P0/f'results/calendar/{m}_OPEN.pkl');panel_C=pd.read_pickle(P0/f'results/calendar/{m}_CLOSE.pkl');days=panel_O.index[panel_O.index>original_end]
 assert len(days)>70 and days[-1].date().isoformat()=='2026-11-12'
 # Main-price original OHLC must be exactly retained prior to the anchor.
 assert all(t in panel_O for t in tickers if not t.startswith(('EUR_CASH_',)))
 N=len(tickers);D=len(days)
 O=np.zeros((D,N));L=O.copy();C=O.copy();obs=np.zeros((D,N),bool);lobs=obs.copy()
 anomalies=[];source_availability=[]
 for j,t in enumerate(tickers):
  if t in ('EUR_CASH_A','EUR_CASH_B'):
   O[:,j]=L[:,j]=C[:,j]=1.;obs[:,j]=lobs[:,j]=True;continue
  raw=load_raw_new(m,t,days)
  c_tail=panel_C[t].loc[original_end:].ffill()
  pc=c_tail.shift(1).reindex(days).to_numpy(float)
  op=panel_O[t].reindex(days).to_numpy(float);cp=c_tail.reindex(days).to_numpy(float)
  # Pure previous-Close carry for missing quotes, never silently claim an observed fill.
  op=np.where(np.isfinite(op)&(op>0),op,pc)
  assert np.isfinite(op).all() and np.isfinite(cp).all() and np.min(op)>0 and np.min(cp)>0,(m,t,'bad asof OHLC')
  O[:,j]=op;C[:,j]=cp
  rr=raw.Low.to_numpy(float);seen=raw.Open.notna().to_numpy() & raw.Close.notna().to_numpy() & (raw.Open.to_numpy(float)>0)&(raw.Close.to_numpy(float)>0)
  lo=np.isfinite(rr)&(rr>0);obs[:,j]=seen;lobs[:,j]=seen&lo
  # Carry previous observed close purely for portfolio valuation when the quote is unavailable.
  prior=np.r_[q['C'][-1,j],cp[:-1]]
  L[:,j]=np.where(lo,rr,prior)
  # Distinguish quote-origin incoherence explicitly. No OHLC repair.
  is_invalid=seen&lo&((rr>op+1e-7*np.maximum(op,1))|(rr>cp+1e-7*np.maximum(cp,1)))
  for day,flag in zip(days,is_invalid):
   if flag:anomalies.append({'market':m,'ticker':t,'date':str(day.date()),'type':'LOW_ABOVE_OPEN_OR_CLOSE'})
  source_availability.append({'ticker':t,'missing_new':int((~seen).sum()),'anomalous_low_new':int(is_invalid.sum())})
 # Verify sources and latest historical anchor; build only continuation arrays.
 q['events']=np.r_[q['events'],np.zeros(D,bool)];q['dates']=np.r_[q['dates'],days.to_numpy('datetime64[ns]')]
 for key,values in [('O',O),('L',L),('C',C)]:q[key]=np.vstack([q[key],values])
 for key,v in [('observed',obs),('low_observed',lobs)]:q[key]=np.vstack([q.get(key,np.ones((old_D,N),bool)),v])
 # Rebuild daily risk signals strictly from historical Close and current-open OHLC;
 # retain every frozen value, verify last 250 sessions of the entire original engine.
 idx=pd.DatetimeIndex(q['dates']);cols=tickers
 with warnings.catch_warnings():
  warnings.simplefilter('ignore',FutureWarning)
  all_input=ddfirst.daily_execution_inputs(pd.DataFrame(q['O'],index=idx,columns=cols),pd.DataFrame(q['L'],index=idx,columns=cols),pd.DataFrame(q['C'],index=idx,columns=cols))
 if m=='EU':
  all_input['gap'][~q['observed']]=0.
  all_input['ud1']=np.mean(all_input['gap']<-.01,axis=1)
  all_input['uneg']=np.mean(all_input['gap']<0,axis=1)
 for key in ['PC','gap','ud1','uneg','UH','SA']:
  d=all_input[key]
  assert np.array_equal(d[old_D-250:old_D],q[key][-250:]),(m,key,'last250 source input parity')
  q[key]=np.concatenate([q[key],d[old_D:]],axis=0)
 gross,g,rg=gross_stream(m,idx,read_q(m,source),US_ALL)
 q['gross']=np.r_[q['gross'],gross];q['g']=np.r_[q['g'],g]
 # Rebuild prescribed monthly targets without any fit or outcome labels.
 pairs=pd.read_csv(FORWARD/f'{m}_OLC19_CONTEXTUAL_FORWARD_TOP2.csv',parse_dates=['signal_date']) if source=='TOP2_CONTEXT_REVALUE' else pair_from_original(m)
 pairs=pairs.sort_values('signal_date').reset_index(drop=True)
 assert list(map(str,pairs.signal_date.dt.date))==['2026-07-31','2026-08-31','2026-09-30','2026-10-30']
 updated={x:q[x][-1] for x in ['g']}
 old_t={key:q[key].copy() for key in ['d1','d2','weights','alt','margin','basew']}
 for k in ['d1','d2','weights','alt','margin','basew']:
  if k=='alt':fill=-1
  elif k in ['d1','d2']:fill=int(q[k][0,old_D-1])
  elif k in ['weights','basew']:fill=.5
  else:fill=0.
  q[k]=np.concatenate([q[k],np.full((1,D),fill,dtype=q[k].dtype)],axis=1)
 for row in pairs.itertuples(index=False):
  i=idx.searchsorted(row.signal_date,side='right')
  assert i>=old_D and i<len(idx) and idx[i]>row.signal_date
  a=tickers.index(row.ticker1);b=tickers.index(row.ticker2)
  q['d1'][0,i:]=a;q['d2'][0,i:]=b;q['events'][i]=True
  # No effect of forward price outcomes on decision formation; stored ranking is frozen.
 # Frozen V6 ALT internal model. Uses previous completed Close and frozen g.
 if source=='TOP2_CONTEXT_REVALUE':
  if m=='EU':
   macro=external_macro_frame(idx,US_ALL)
   vclose=pd.DataFrame(q['C'],index=idx,columns=tickers).copy();vclose.rename(columns={'EUR_CASH_A':'BIL','EUR_CASH_B':'SHV'},inplace=True)
   vclose['SPY']=macro.SPY.to_numpy()
   allowed=np.column_stack([q['observed'][:,:-2],np.zeros((len(idx),3),bool)])
   ns=v6.__dict__.copy();exec((SRC/'V6_PORT_SOURCE.py').read_text(),ns)
   with warnings.catch_warnings():warnings.simplefilter('ignore');alt=ns['build_v6_state'](vclose,q['d1'],q['d2'],q['basew'],q['gross'],allowed=allowed).alt_idx
  else:
   vclose=pd.DataFrame(q['C'],index=idx,columns=tickers)
   with warnings.catch_warnings():warnings.simplefilter('ignore');alt=v6.build_v6_state(vclose,q['d1'],q['d2'],q['basew'],q['gross']).alt_idx
  assert np.array_equal(alt[0,old_D-250:old_D],q['alt'][0,old_D-250:old_D]),(m,'V6 ALT last250 parity')
  q['alt'][:,old_D:]=alt[:,old_D:]
 else:
  # Recompute V6 alternative for ORIGINAL selections with original risk path.
  if m=='EU':
   macro=external_macro_frame(idx,US_ALL)
   vclose=pd.DataFrame(q['C'],index=idx,columns=tickers).rename(columns={'EUR_CASH_A':'BIL','EUR_CASH_B':'SHV'});vclose['SPY']=macro.SPY.to_numpy()
   allowed=np.column_stack([q['observed'][:,:-2],np.zeros((len(idx),3),bool)])
   ns=v6.__dict__.copy();exec((SRC/'V6_PORT_SOURCE.py').read_text(),ns)
   with warnings.catch_warnings():warnings.simplefilter('ignore');alt=ns['build_v6_state'](vclose,q['d1'],q['d2'],q['basew'],q['gross'],allowed=allowed).alt_idx
  else:
   vclose=pd.DataFrame(q['C'],index=idx,columns=tickers)
   with warnings.catch_warnings():warnings.simplefilter('ignore');alt=v6.build_v6_state(vclose,q['d1'],q['d2'],q['basew'],q['gross']).alt_idx
  assert np.array_equal(alt[0,old_D-250:old_D],q['alt'][0,old_D-250:old_D]),(m,'ORIGINAL V6 ALT last250 parity')
  q['alt'][:,old_D:]=alt[:,old_D:]
 # ORIGINAL branch is used only for 50/50 D_SELECTION; OLC56 weights were fitted to CONTEXT pairs.
 if source=='ORIGINAL':
  return q,q['weights'].copy(),old_D,pd.DataFrame(),pd.DataFrame(anomalies),pd.DataFrame(source_availability),rg
 # Continue original OLC56 MinVar weights from frozen old event weights.
 w=q['weights'].copy(); checks=[]
 old_w=pd.read_csv(f'/mnt/data/olc100_workspace/OLC56_ROBUST_20261106/results/{m}_DECISIONS.csv')
 old_ids=np.flatnonzero(q['events'][:old_D]);assert len(old_ids)==len(old_w)==90
 for j,k in enumerate(old_ids):
  trial,nvalid=minvar_at(q,int(k)); expected=float(old_w.iloc[j]['weight__B1_MINVAR63_CAP25'])
  if abs(trial-expected)>=1e-10:
   raw_chk=read_q(m,source)
   print('MISMATCH_W',m,source,j,int(k),trial,expected,
       'original d',raw_chk['d1'][0,k],raw_chk['d2'][0,k],
       'now d',q['d1'][0,k],q['d2'][0,k],
       'C parity?',np.array_equal(q['C'][:old_D],raw_chk['C']),
       'OBS?',np.array_equal(q['observed'][:old_D],raw_chk['observed']) if m=='EU' else '-',flush=True)
  assert abs(trial-expected)<1e-10,(m,j,trial,expected)
  e=int(old_ids[j+1]) if j<len(old_ids)-1 else len(idx)
  w[0,int(k):e]=trial
  checks.append(dict(market=m,signal_date=str(idx[int(k)].date()),weight1=trial,previous_close_ok=nvalid))
 newer=[];new_ids=np.flatnonzero(q['events'][old_D:])+old_D;assert len(new_ids)==4
 for j,k in enumerate(new_ids):
  trial,nvalid=minvar_at(q,int(k));w[0,int(k):]=trial
  newer.append(dict(market=m,signal_date=str(idx[int(k-1)].date()),entry_date=str(idx[int(k)].date()),ticker1=tickers[int(q['d1'][0,k])],ticker2=tickers[int(q['d2'][0,k])],minvar_w1=trial,valid_return_count=nvalid,signal_generated_retroactively=True))
 return q,w,old_D,pd.DataFrame(newer),pd.DataFrame(anomalies),pd.DataFrame(source_availability),rg

def sim(q,fee,arm,friction=.001):
 select,alloc,timing,risk=ARMS[arm];fast=risk=='FAST_LOCK3';ev=q['events']
 r=_impl({k:v for k,v in q.items() if k!='events'},ev,policy=('DELAY' if timing=='DELAY3' else 'IMMEDIATE'),fraction=(3 if timing=='DELAY3' else 1),fee=fee,exposure_timing='PREVIOUS',stop_timing='NOW',stop_friction=friction,ordinary_alarm=False,fast_stop=fast,lock_days=3 if fast else 0)
 return r

def native_value(r,idx):return float(r['ledger'][idx,0])

def main():
 assert hashlib.sha256(FROZEN.read_bytes()).hexdigest()==FREEZE_SHA
 us_all=pd.read_pickle(P0/'results/calendar/USA_CLOSE.pkl')
 with ZipFile('/mnt/data/frozen_sources/OLC67_Strategia_ETF_Verificata.zip') as z:
  ref67=pd.read_csv(io.BytesIO(gzip.decompress(z.read('OLC67/results/OLC67_DAILY_LOGRET.csv.gz'))),parse_dates=['date'])
 reference_errors=[];parity_checks=[]
 results=[];decision=[];risk_qa=[];bad=[];access=[];all_daily=[];stop_diags=[]
 for m in ['EU','USA']:
  srcs={}
  for src in ['TOP2_CONTEXT_REVALUE','ORIGINAL']:
   q,w,old_D,new,an,miss,rg=build_extended(m,src,us_all)
   srcs[src]=(q,w,old_D,rg)
   if src=='TOP2_CONTEXT_REVALUE':decision.append(new);bad.append(an);access.append(miss.assign(market=m));risk_qa.append(dict(market=m,**rg,extra=len(q['dates'])-old_D,old_dates=old_D))
  for arm,(_,a,_,_) in ARMS.items():
   src='ORIGINAL' if arm=='D_SELECTION' else 'TOP2_CONTEXT_REVALUE'
   q,w,old_D,rg=srcs[src];q={k:v.copy() for k,v in q.items()}
   if a=='MINVAR63':q['weights']=w
   assert len(q['dates'])==len(q['g'])==len(q['events'])
   old_i=old_D-1;ds=pd.DatetimeIndex(q['dates']);start=ds.get_loc('2026-08-03') if m=='EU' else ds.get_loc('2026-08-03')
   completed_end=ds.get_loc('2026-11-02');last=ds.get_loc('2026-11-12')
   for fee in [.001,.003]:
    for friction in [.001,.005]:
     rr=sim(q,fee,arm,friction)
     # Prefix exact checkpoint verification: the former final opening became an active session.
     if arm in ['B_BASE','D_SELECTION'] and fee==.001 and friction==.001:
      path=REFERENCE/f'{m}_{"ORIGINAL" if arm=="D_SELECTION" else "TOP2_CONTEXT_REVALUE"}_FAST_LOCK3_F10_S10.npz'
      with np.load(path) as old:
       for col in FIELDS:
        assert np.array_equal(rr[col][:old_i],old[col][:old_i]),(m,arm,col,'historical accounting mutated')
        if col=='nav':
         assert abs(rr['ledger'][old_i,0]-float(old['nav'][old_i]))<1e-12,(m,arm,'carry NAV anchor mismatch')
      print('FROZEN_ACCOUNT_PREFIX_PASS',m,arm,flush=True)
     if friction==.001 and arm!='D_SELECTION':
      timing='DELAY3' if ARMS[arm][2]=='DELAY3' else 'IMMEDIATE'
      weight='MINVAR63' if a=='MINVAR63' else 'HALF'
      risk=ARMS[arm][3]
      old=ref67[(ref67.market==m)&(ref67.weight==weight)&(ref67.timing==timing)&(ref67.risk==risk)&(np.isclose(ref67.fee,fee))].sort_values('date')
      expected_date=ds[1:old_D]
      assert len(old)==old_i and np.array_equal(old.date.to_numpy('datetime64[ns]'),expected_date.to_numpy('datetime64[ns]')),(m,arm,'OLC67 date mismatch')
      actual_log=np.log(rr['nav'][:old_i]/rr['ledger'][:old_i,0])
      dmax=float(np.max(np.abs(actual_log-old.logr.to_numpy(float))))
      assert dmax<1e-12,(m,arm,fee,'OLC67 daily prefix mismatch',dmax)
      reference_errors.append({'market':m,'arm':arm,'fee':fee,'n_days':int(old_i),'max_abs_daily_log_error':dmax})
      print('OLC67_DAILY_REFERENCE_PASS',m,arm,fee,dmax,flush=True)
     for start_s,start_idx,end_idx in [('JUL1_NOV2',old_i,completed_end),('AUG3_NOV2',start,completed_end),('AUG3_NOV12',start,last)]:
      a0=native_value(rr,end_idx)/native_value(rr,start_idx)-1
      log=float(np.log1p(a0))
      sub=rr['ledger'][start_idx:end_idx]
      logd=np.log(rr['nav'][start_idx:end_idx-1]/rr['ledger'][start_idx:end_idx-1,0]) if end_idx>start_idx+1 else np.array([])
      risk_gross=sub[:,1].mean() if len(sub) else None
      results.append(dict(market=m,arm=arm,fee=fee,stop_friction=friction,period=start_s,open_start=str(ds[start_idx].date()),open_end=str(ds[end_idx].date()),gross_return=a0,log_return=log,stop_events=int(sub[:,8].sum()),turnover=float(sub[:,4].sum()),rebalance_fees=float(sub[:,5].sum()),stop_fees=float(sub[:,6].sum()),stop_slippage=float(sub[:,7].sum()),mean_target_gross=risk_gross,maxdd_local=float(np.min(np.cumprod(np.exp(np.log(rr['nav'][start_idx:end_idx]/rr['ledger'][start_idx:end_idx,0])))/np.maximum.accumulate(np.cumprod(np.exp(np.log(rr['nav'][start_idx:end_idx]/rr['ledger'][start_idx:end_idx,0]))))-1)) if end_idx>start_idx else 0.,data_not_certified=True))
     if fee==.001 and friction==.001:
      rr_idx=np.arange(old_i,last)
      for ix in rr_idx:
       all_daily.append(dict(market=m,arm=arm,date=str(ds[ix].date()),next_date=str(ds[ix+1].date()),daily_net_log=float(np.log(rr['nav'][ix]/rr['ledger'][ix,0])),opening_nav=float(rr['ledger'][ix,0]),next_nav=float(rr['nav'][ix]),main_gross=float(rr['ledger'][ix,1]),risk_fast_exits=int(rr['ledger'][ix,8]),stop_slip=float(rr['ledger'][ix,7]),fee=float(rr['ledger'][ix,5]+rr['ledger'][ix,6])))
  print('NATIVE_FORWARD_MARKET_PASS',m,len(ds),flush=True)
 df=pd.DataFrame(results);df.to_csv(OUT/'OLC100_NATIVE_FORWARD_SCORECARD.csv',index=False)
 pd.concat(decision,ignore_index=True).to_csv(OUT/'OLC100_NATIVE_FORWARD_WEIGHTS.csv',index=False)
 pd.DataFrame(risk_qa).to_csv(OUT/'OLC100_NATIVE_RISK_QA.csv',index=False)
 pd.DataFrame(reference_errors).to_csv(OUT/'OLC100_OLC67_DAILY_PARITY.csv',index=False)
 pd.concat(bad,ignore_index=True).to_csv(OUT/'OLC100_NATIVE_SUSPECT_LOW.csv',index=False)
 pd.concat(access,ignore_index=True).to_csv(OUT/'OLC100_NATIVE_SOURCE_COVERAGE.csv',index=False)
 pd.DataFrame(all_daily).to_csv(OUT/'OLC100_NATIVE_FORWARD_DAILY.csv.gz',index=False)
 primary=df[(df.fee==.001)&(df.stop_friction==.001)&(df.period=='AUG3_NOV2')].sort_values(['market','arm'])
 print('NATIVE_FORWARD_PRIMARY_BASECOST',flush=True)
 print(primary[['market','arm','gross_return','stop_events','mean_target_gross','maxdd_local']].to_string(index=False, float_format=lambda v:f'{v:.6f}'),flush=True)
 qa={'status':'NATIVE_ACCOUNT_REPLAY_COMPLETED_NOT_CERTIFIED','note':'Retrospective 2026H2, 79 raw OHLC anomalies, historical universe PIT and broker stops unverified','market_risk_streams':risk_qa,'matured_new_decisions_per_market':3,'full_native_paths':len(ARMS)*2*2*2,'olc67_full_daily_prefix_parity':reference_errors,'period':'2026-08-03 through 2026-11-02 (three mature decisions)','original_baseline_prefix_parity':'7/7 each market selection BASE + ORIGINAL','accounting_replay':True,'source_end':'2026-11-12','prospective':False,'promoted':False,'main_unmodified':True}
 (OUT/'OLC100_NATIVE_FORWARD_QA.json').write_text(json.dumps(qa,indent=2)+'\n')
if __name__=='__main__':main()
