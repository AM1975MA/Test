#!/usr/bin/env python3
"""OLC101 controlled exploratory experiment: monthly frozen score + later DAILY
PRICE-momentum percentile rank confirmations.  NOT re-fitting the full ET/XGB
Hybrid42 every day.  Native OLC19 accounting, V6 alternatives recomputed from
new candidates, same-state timing controls; no trading, no new alpha proof.
"""
from __future__ import annotations
import sys,math,json,hashlib,warnings,time
from pathlib import Path
import numpy as np,pandas as pd
from scipy.stats import rankdata
OUT=Path('/mnt/data/olc102/results');OUT.mkdir(parents=True,exist_ok=True)
ROOT=Path('/mnt/data/olc102/runtime/olc19_combined_risk_20261102')
NATIVE=ROOT/'restore/olc18_execution_20261102'
SRC=Path('/mnt/data/olc102/runtime/srcfreeze')
sys.path[:0]=[str(SRC),str(ROOT/'src'),str(NATIVE/'parent_archive/parent/olc16_contextual_rank_20261102/src')]
from combined_engine import _impl
import v6
from portfolio_metrics_parent import metrics
F=['nav','ledger','primary_units','defensive_units','free_cash','targets','risk_trace']

POLICIES={
  'OLC19_IMMEDIATE':('fixed',0,0.0),
  'OLC19_NATIVE_DELAY3':('native_delay',3,0.0),
  'FIXED_DAY1':('fixed',1,0.0),
  'RANK_DAY1_25':('day1',1,0.25),
  'FIXED_DAY2':('fixed',2,0.0),
  'RANK_DAY2_25':('day2',2,0.25),
  'RANK_AVG_25':('avg',2,0.25),
  'RANK_RECENT_25':('recent',2,0.25),
  'RANK_RECENT_40':('recent',2,0.40),
}

def source(m):
 with np.load(NATIVE/f'inputs/{m}_TOP2_CONTEXT_REVALUE.npz',allow_pickle=False) as z:q={k:z[k].copy() for k in z.files}
 dec=pd.read_csv(NATIVE/f'inputs/{m}_TOP2_CONTEXT_REVALUE_DECISIONS.csv',parse_dates=['signal_date','entry_date'])
 score=pd.read_csv(NATIVE/f'parent_archive/parent/olc16_contextual_rank_20261102/results/{m}_SCORES.csv.gz',usecols=['signal_date','ticker','TOP2_CONTEXT_REVALUE_FUSION'])
 return q,dec,score

def orig_ref(m):
 with np.load(ROOT/f'results/paths/{m}_TOP2_CONTEXT_REVALUE_FAST_LOCK3_F10_S10.npz',allow_pickle=False) as z:return {k:z[k].copy() for k in z.files}

def percentile(arr):
 arr=np.asarray(arr,float); y=np.full(len(arr),np.nan)
 good=np.isfinite(arr)
 if good.sum()>0:y[good]=rankdata(arr[good],method='average')/good.sum()
 return y

def derive_decisions(m,q,dec,scores,lambda_=0.25):
 """At k=open t0, R0 known (prior completed close); R1 updated only
 after Close[k]; R2 only after Close[k+1]. Earliest legal trade k+1 or k+2.
 """
 mapping={str(t):i for i,t in enumerate(q['tickers'])};by={str(date):g for date,g in scores.groupby('signal_date')}
 events=np.flatnonzero(q['events']);assert len(events)==len(dec)==90
 result={style:[] for style in ['fixed','day1','day2','avg','recent']}
 detail=[]
 for j,k in enumerate(events):
  sig=str(dec.iloc[j].signal_date.date());g=by[sig].dropna(subset=['TOP2_CONTEXT_REVALUE_FUSION']).copy()
  tick=g.ticker.to_numpy(str);idx=np.array([mapping[t] for t in tick]);
  r0=percentile(g.TOP2_CONTEXT_REVALUE_FUSION.to_numpy(float))
  # Dates immediately following entry open; future prices only used for
  # an execution opening strictly AFTER their close.
  def rank_new(k1):
   if k==0 or k1>=len(q['dates']):return r0.copy()
   cprev=q['C'][k-1,idx];cnow=q['C'][k1,idx]
   valid=np.isfinite(cprev)&np.isfinite(cnow)&(cprev>0)&(cnow>0)
   if 'observed' in q:
    obs=q['observed'];valid &= obs[k-1,idx]&obs[k1,idx]
   price=np.full(len(idx),np.nan);price[valid]=np.log(cnow[valid]/cprev[valid]);p=percentile(price)
   # missing quotes do not confer a perfect negative or positive price rank
   return np.where(np.isfinite(p), (1.-lambda_)*r0+lambda_*p, r0)
  r1=rank_new(k);r2=rank_new(k+1)
  old=(str(dec.iloc[j].ticker1),str(dec.iloc[j].ticker2));
  formulas={'fixed':r0,'day1':r1,'day2':r2,'avg':0.50*r0+0.30*r1+0.20*r2,
            'recent':0.20*r0+0.30*r1+0.50*r2}
  for style,r in formulas.items():
   ix=np.lexsort((tick,-r))[:2];pair=(str(tick[ix[0]]),str(tick[ix[1]]))
   if style=='fixed' and pair!=old:raise AssertionError((m,j,style,old,pair))
   result[style].append(pair)
   detail.append(dict(market=m,event=j,signal_date=sig,entry_date=str(pd.Timestamp(q['dates'][k]).date()),
                     style=style,lambda_price=lambda_,pair1=pair[0],pair2=pair[1],
                     origin1=old[0],origin2=old[1],same_pair_set=set(pair)==set(old),
                     same_pair_order=pair==old,rank_leader_score=float(r[np.where(tick==pair[0])[0][0]]),
                     original_score=float(r0[np.where(tick==old[0])[0][0]])))
 return result,pd.DataFrame(detail)

def w_minvar(q,idx1,idx2,k):
 if k<64 or idx1==idx2:return .5
 c=q['C'][k-64:k][:,[idx1,idx2]]
 observed=q.get('observed',np.ones(q['C'].shape,bool))[k-64:k][:,[idx1,idx2]]
 ok=np.all(observed[1:]&observed[:-1],axis=1)&np.isfinite(c).all(axis=1)[1:]&np.isfinite(c).all(axis=1)[:-1]&np.all((c[1:]>0)&(c[:-1]>0),axis=1)
 if ok.sum()<math.ceil(.8*63):return .5
 lr=np.log(c[1:][ok]/c[:-1][ok]);var=np.cov(lr.T,ddof=1)
 va,vb,co=float(var[0,0]),float(var[1,1]),float(var[0,1]);den=va+vb-2*co
 return .5 if den<=1e-13 or min(va,vb)<=1e-15 else float(np.clip((vb-co)/den,.25,.75))

def staged(q,events,pairs,style,delay,allocation):
 z={k:v.copy() for k,v in q.items()}
 names=list(map(str,z['tickers']));name_to_idx={t:i for i,t in enumerate(names)}
 vals=[];prev_pair=(names[int(q['d1'][0,0])],names[int(q['d2'][0,0])]);prev_weight=.5
 for j,k in enumerate(events):
  nxt=int(events[j+1]) if j+1<len(events) else len(q['dates'])
  target=(name_to_idx[pairs[j][0]],name_to_idx[pairs[j][1]])
  # Never trade using the last day's Close at the same day's Open.
  # Last signal has no future 2-close observation, so leave it unchanged.
  actual=delay if j>0 and k+delay<nxt else 0
  if j==len(events)-1:actual=0
  if actual>0:
   z['d1'][0,k:k+actual]=name_to_idx[prev_pair[0]]
   z['d2'][0,k:k+actual]=name_to_idx[prev_pair[1]]
   z['weights'][0,k:k+actual]=prev_weight
   z['basew'][0,k:k+actual]=.5
  weight=w_minvar(q,target[0],target[1],int(k+actual)) if allocation=='MINVAR63' else .5
  z['d1'][0,k+actual:nxt]=target[0];z['d2'][0,k+actual:nxt]=target[1]
  z['weights'][0,k+actual:nxt]=weight;z['basew'][0,k+actual:nxt]=.5
  prev_pair=pairs[j];prev_weight=weight
  vals.append({'event':j,'market':'','style':style,'k':int(k),'effective_idx':int(k+actual),'effective_date':str(pd.Timestamp(q['dates'][min(k+actual,len(q['dates'])-1)]).date()),'pair1':pairs[j][0],'pair2':pairs[j][1],'weight1':weight,'allocation':allocation,'n_delayed':actual})
 return z,pd.DataFrame(vals)

def v6_alt(m,q,q_usa):
 idx=pd.DatetimeIndex(q['dates']);cols=list(map(str,q['tickers']))
 C=pd.DataFrame(q['C'],index=idx,columns=cols)
 with warnings.catch_warnings():
  warnings.simplefilter('ignore')
  if m=='USA':alt=v6.build_v6_state(C,q['d1'],q['d2'],q['basew'],q['gross']).alt_idx
  else:
   usi=pd.DatetimeIndex(q_usa['dates']);i=list(q_usa['tickers']).index('SPY');spy=q_usa['C'][:,i]
   pos=usi.searchsorted(idx,side='left')-1
   v=np.full(len(idx),np.nan);valid=pos>=0;v[valid]=spy[pos[valid]]
   C=C.rename(columns={'EUR_CASH_A':'BIL','EUR_CASH_B':'SHV'});C['SPY']=v
   allowed=np.column_stack([q['observed'][:,:-2],np.zeros((len(idx),3),bool)])
   ns=v6.__dict__.copy();exec((SRC/'V6_PORT_SOURCE.py').read_text(),ns)
   alt=ns['build_v6_state'](C,q['d1'],q['d2'],q['basew'],q['gross'],allowed=allowed).alt_idx
 return alt

def simulate(q,fee,stop_friction,policy='IMMEDIATE'):
 return _impl({k:v for k,v in q.items() if k!='events'},q['events'],policy=policy,fraction=(3 if policy=='DELAY' else 1),fee=fee,exposure_timing='PREVIOUS',stop_timing='NOW',stop_friction=stop_friction,ordinary_alarm=False,fast_stop=True,lock_days=3)

def navmetrics(r,dates,start=None,end=None):
 nav=r['nav'];mask=np.ones(len(nav),bool)
 idx=pd.DatetimeIndex(dates)
 if start:mask &= idx>=pd.Timestamp(start)
 if end:mask &= idx<=pd.Timestamp(end)
 ii=np.flatnonzero(mask)
 if len(ii)<2:return dict(CAGR=np.nan,MaxDD=np.nan,Return=np.nan,n_days=len(ii))
 nv=nav[ii];lr=np.log(nv[1:]/nv[:-1]);cagr=float(np.expm1(np.mean(lr)*252));dd=float(np.min(nv/np.maximum.accumulate(nv)-1.));ret=float(nv[-1]/nv[0]-1)
 return dict(CAGR=cagr,MaxDD=dd,Return=ret,n_days=len(ii))

def main():
 t0=time.time();data={m:source(m) for m in ('EU','USA')};qu=data['USA'][0];saved=[];detail=[];econ=[];comparisons=[];verifiers=[]
 for m in ('EU','USA'):
  print('MARKET',m,flush=True);q,dec,scores=data[m];events=np.flatnonzero(q['events']);ref=orig_ref(m)
  source_s=simulate(q,.001,.001,'IMMEDIATE')
  for f in F:
   if not np.array_equal(source_s[f],ref[f]):raise AssertionError((m,f,'baseline bitwise mismatch',np.max(np.abs(source_s[f]-ref[f]))))
  original_alt=v6_alt(m,q,qu)
  assert np.array_equal(original_alt,q['alt']),(m,'V6 original alt mismatch')
  print('BASELINE_PARITY_PASS',m,len(events),len(q['dates']),flush=True)
  verifiers.append(dict(market=m,baseline_bitwise_arrays=len(F),v6_alt_bitwise=True,events=len(events)))
  original_pairs=[(str(row.ticker1),str(row.ticker2)) for row in dec.itertuples()]
  base_dec,pdet=derive_decisions(m,q,dec,scores,.25)
  d40,p40=derive_decisions(m,q,dec,scores,.40)
  pdet=pdet[pdet['style']!='fixed'].copy();p40=p40[p40['style']=='recent'].copy();p40['style']='recent40'
  detail.append(pd.concat([pdet,p40]))
  policy_c={
   'OLC19_IMMEDIATE':('fixed',0,'HALF','IMMEDIATE',.25),
   'OLC19_NATIVE_DELAY3':('fixed',0,'HALF','DELAY',.25),
   'OLC67_NATIVE':('fixed',0,'MINVAR63','DELAY',.25),
   'FIXED_DAY1_HALF':('fixed',1,'HALF','IMMEDIATE',.25),
   'RANK_DAY1_25_HALF':('day1',1,'HALF','IMMEDIATE',.25),
   'FIXED_DAY2_HALF':('fixed',2,'HALF','IMMEDIATE',.25),
   'RANK_DAY2_25_HALF':('day2',2,'HALF','IMMEDIATE',.25),
   'RANK_AVG_25_HALF':('avg',2,'HALF','IMMEDIATE',.25),
   'RANK_RECENT_25_HALF':('recent',2,'HALF','IMMEDIATE',.25),
   'RANK_RECENT_40_HALF':('recent',2,'HALF','IMMEDIATE',.40),
   'FIXED_DAY2_MV63':('fixed',2,'MINVAR63','IMMEDIATE',.25),
   'RANK_AVG_25_MV63':('avg',2,'MINVAR63','IMMEDIATE',.25),
   'RANK_RECENT_25_MV63':('recent',2,'MINVAR63','IMMEDIATE',.25),
   'RANK_RECENT_40_MV63':('recent',2,'MINVAR63','IMMEDIATE',.40),
  }
  for name,(style,delay,alloc,timing,alpha) in policy_c.items():
   pairs=(base_dec if alpha==.25 else d40)[style]
   if name=='OLC19_IMMEDIATE':z=q
   else:
    # for historical OLC67 control, proposal is original from event start, engine delays unchanged
    z,weights=staged(q,events,pairs,style,delay,alloc)
    z['alt'][:]=v6_alt(m,z,qu)
    weights['market']=m;weights['arm']=name;econ.append(weights)
   for fee,friction in [(.001,.001),(.003,.005)]:
    # tests include original policy at exact original schedule; native OLC67 from original q with original MinVar63 event weights
    if name=='OLC67_NATIVE':
     zz,wt=staged(q,events,original_pairs,'fixed',0,'MINVAR63')
     zz['alt'][:]=v6_alt(m,zz,qu);pp='DELAY'
    else:zz=z;pp=timing
    r=simulate(zz,fee,friction,pp)
    met=navmetrics(r,q['dates']);main=navmetrics(r,q['dates'],'2021-01-01','2024-12-31')
    saved.append(dict(market=m,arm=name,fee=fee,stop_friction=friction,CAGR_FULL=met['CAGR'],MaxDD_FULL=met['MaxDD'],CAGR_MAIN=main['CAGR'],MaxDD_MAIN=main['MaxDD'],last_nav=r['nav'][-1],n_days=met['n_days'],n_stops=int(np.sum(r['ledger'][:,8])),annual_turnover=float(np.sum(r['ledger'][:,4])/((len(q['dates'])-1)/252)),annual_fees=float(np.sum(r['ledger'][:,5])/((len(q['dates'])-1)/252))))
    rr=np.r_[np.nan,np.diff(np.log(r['nav']))]
    comparisons.extend([dict(market=m,arm=name,fee=fee,stop_friction=friction,date=str(pd.Timestamp(dt).date()),daily_log_return=float(v) if np.isfinite(v) else np.nan,nav=float(n)) for dt,v,n in zip(q['dates'],rr,r['nav'])])
   print('  ',name,'CAGR',round(100*saved[-2]['CAGR_FULL'],2),'DD',round(100*saved[-2]['MaxDD_FULL'],2),flush=True)
  print('MARKET DONE',m,'secs',round(time.time()-t0,1),flush=True)
 pd.DataFrame(saved).to_csv(OUT/'OLC101_NATIVE_SCORECARD.csv',index=False)
 pd.concat(detail).to_csv(OUT/'OLC101_SELECTIONS.csv',index=False)
 pd.concat(econ).to_csv(OUT/'OLC101_IMPLEMENTED_DECISIONS.csv',index=False)
 pd.DataFrame(comparisons).to_csv(OUT/'OLC101_NATIVE_DAILY.csv',index=False)
 (OUT/'OLC101_QA.json').write_text(json.dumps(dict(status='ACCOUNTING_ENGINE_AND_V6_PARITY_PASS_PRICE_RANK_EXPLORATORY',verifiers=verifiers,
   timing_contract='Close k-1 available at first open k; Close k available first at open k+1; Close k+1 at open k+2',
   retrospective_only=True,daily_ml_rerank=False,total_native_replays=len(saved)),indent=2))
 print('FINISH',len(saved),'replays',round(time.time()-t0,1),flush=True)
if __name__=='__main__':main()
