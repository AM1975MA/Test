from research_common import B
from audit_engine import simulate_audited
import numpy as np,pandas as pd,json,time,os
OUT=B/'results';PATHS=OUT/'paths';PATHS.mkdir(exist_ok=True);LOGS=OUT/'daily';LOGS.mkdir(exist_ok=True)
COLS=['opening_nav','target_gross','target_weight1','target_alt_weight','rebalance','turnover','rebalance_fee','stop1','stop2','stop_fee','stop_slippage','poststop_value1','poststop_value2','poststop_alt_value','poststop_cash_A','poststop_cash_B','free_cash','systemic_trigger','cooldown','proposed_id1','proposed_id2','proposed_alt_id','stopped_notional','postrebalance_nav','blocked_rebalance','actual_id1','actual_id2','actual_alt_id','prestop_value1','prestop_value2','prestop_alt_value','pnl1_no_stop','pnl2_no_stop','pnl_alt','pnl_cash_A','pnl_cash_B','stop1_effect_before_slip','stop2_effect_before_slip','net_pnl','next_nav','cash_weight','risky_weight_before_stop','quote1_observed','quote2_observed','stale_held_count','fees_slip_total','accounting_residual','risky_weight_after_stop']
fields=['O','L','C','PC','gap','ud1','uneg','UH','SA']
def summary(nav,dates,ledger,name,market):
 lr=np.diff(np.log(np.r_[1.,nav]));rows=[]
 intervals={'FULL':(dates[0],dates[-1]),'2019_2024':(pd.Timestamp('2019-02-01'),pd.Timestamp('2024-12-31')),'2019Apr_2024':(pd.Timestamp('2019-04-01'),pd.Timestamp('2024-12-31')),'2021_2024':(pd.Timestamp('2021-02-01'),pd.Timestamp('2024-12-31'))}
 intervals.update({str(y):(pd.Timestamp(y,1,1),pd.Timestamp(y,12,31)) for y in range(2017,2027)})
 for period,(start,end) in intervals.items():
  mask=(dates>=start)&(dates<=end)
  if mask.sum()<10:continue
  log=lr[mask];eq=np.exp(np.cumsum(log));peak=np.maximum.accumulate(np.r_[1.,eq])[1:];dd=eq/peak-1
  simple=np.expm1(log);annualized=np.expm1(log.sum()*252/len(log))
  rows.append(dict(market=market,strategy=name,period=period,first=str(dates[mask][0].date()),last=str(dates[mask][-1].date()),n=len(log),cagr=annualized,return_period=np.expm1(log.sum()),annual_log=log.mean()*252,maxdd=dd.min(),sharpe=simple.mean()/simple.std(ddof=1)*np.sqrt(252) if simple.std()>0 else 0,ann_turnover=ledger[mask,5].mean()*252,stop_executions=int(ledger[mask,7:9].sum()),sysm_days=int(ledger[mask,17].sum()),rebalances=int(ledger[mask,4].sum()),blocked=int(ledger[mask,24].sum()),avg_risky_weight=float(ledger[mask,41].mean()),stale_held_days=int((ledger[mask,44]>0).sum())))
 return rows

def replay(q,name,market,mode='full',cash0=False,strict=True):
 q={k:v.copy() for k,v in q.items()};T=q['tickers'].tolist();dates=pd.DatetimeIndex(q['dates']);D=len(dates)
 if market=='USA':bil=T.index('BIL');shv=T.index('SHV')
 else:bil=T.index('EUR_CASH_A');shv=T.index('EUR_CASH_B')
 if cash0:
  for fld in ['O','L','C','PC']:q[fld][:,[bil,shv]]=1.
 # Cash0 USA is a residual-sleeve diagnostic; if bills themselves are selected this also affects those holdings, disclosed.
 riskoff=mode=='no_risk'
 G=np.ones(D) if riskoff else q['g'];GALT=np.ones(D) if riskoff else q['g']
 if mode=='lag_systemic':
  # Causal conservative one-session-lag stress, not claimed equivalent.
  for fld in ['gap','ud1','uneg']:q[fld]=np.concatenate([q[fld][:1]*0,q[fld][:-1]],axis=0)
 cost=0. if mode=='zero_cost' else .001;slip=0. if mode=='zero_cost' else .001
 args=[q['d1'],q['d2'],q['weights']]+[q[k] for k in fields]+[bil,shv,G[None,:],GALT,q['alt'],not riskoff]
 observed=q.get('observed',np.ones_like(q['O'],bool));lowobs=q.get('low_observed',observed)
 E,tr,X,AW,led=simulate_audited(*args,cost=cost,slip=slip,systemic_enabled=not(riskoff or mode=='no_systemic'),stops_enabled=not(riskoff or mode=='no_stop'),observed=observed,low_observed=lowobs,strict_quotes=strict)
 assert np.isfinite(E).all() and E.min()>0
 err=np.max(abs(led[0,:-1,46]));assert err<1e-10,(name,err)
 np.savez_compressed(PATHS/f'{market}_{name}.npz',dates=dates.values,nav=E[0],ledger=led[0],tickers=T)
 frame=pd.DataFrame(led[0,:-1],columns=COLS)
 frame.insert(0,'decision_date',dates[:-1]);frame.insert(1,'valuation_date',dates[1:])
 for f in ['proposed_id1','proposed_id2','proposed_alt_id','actual_id1','actual_id2','actual_alt_id']:
  frame[f.replace('_id','_ticker')]=[T[int(i)] if int(i)>=0 else 'CASH' for i in frame[f]]
 r=frame.net_pnl/frame.opening_nav;log=np.log1p(r)
 assert np.max(abs(log.to_numpy()-np.diff(np.log(np.r_[1.,E[0]]))[:-1]))<1e-12
 scale=np.ones(len(r));nz=np.abs(r)>1e-14;scale[nz]=log[nz]/r[nz]
 for f in ['pnl1_no_stop','pnl2_no_stop','pnl_alt','pnl_cash_A','pnl_cash_B','stop1_effect_before_slip','stop2_effect_before_slip','rebalance_fee','stop_fee','stop_slippage']:
  sign=-1 if f in ['rebalance_fee','stop_fee','stop_slippage'] else 1
  frame['log_contribution_'+f]=sign*frame[f]/frame.opening_nav*scale
 frame['net_return']=r;frame['net_log_return']=log
 contributions=frame.filter(like='log_contribution_').sum(axis=1)
 assert np.max(abs(contributions-log))<1e-12
 frame.to_csv(LOGS/f'{market}_{name}.csv.gz',index=False,compression='gzip')
 stats=summary(E[0],dates,led[0],name,market)
 print(market,name,'CAGR',stats[0]['cagr'],'DD',stats[0]['maxdd'],'blocked',stats[0]['blocked'],'pnlerr',err,flush=True)
 return stats,E[0]
def main():
 allrows=[];parity={}
 for market in ['USA','EU']:
  if market=='USA':
   q=dict(np.load(B/'inputs/US_STATE.npz',allow_pickle=False));h={k:v.copy() for k,v in q.items()};h['weights']=np.full_like(h['weights'],.5);h['alt']=np.load(B/'inputs/US_RH50_ALT.npz')['alt']
  else:
   q=dict(np.load(B/'inputs/EU_STATE_RETURN_H_ORIGINAL.npz',allow_pickle=False));h=dict(np.load(B/'inputs/EU_STATE_RETURN_H_HALF.npz',allow_pickle=False))
  for strategy,st in [('ORIGINAL39',q),('RH50',h)]:
   for mode in ['full','no_risk','zero_cost','no_stop','no_systemic','lag_systemic']:
    name=strategy if mode=='full' else strategy+'_'+mode
    rr,nav=replay(st,name,market,mode);allrows+=rr
    if market=='USA' and mode=='full':
     path=B/('factorial/R_T0_H1/r1' if strategy=='ORIGINAL39' else 'mediation/R_HALF/r1')/'FULL_UNIVERSE_PATH.npz'
     ref=np.load(path)['equity'][0];err=float(np.max(abs(ref-nav)));assert err<1e-12;parity[name]=err
   if market=='USA':
    rr,_=replay(st,strategy+'_zero_cash',market,cash0=True);allrows+=rr
   else:
    rr,_=replay(st,strategy+'_filled_quote_diagnostic',market,strict=False);allrows+=rr
  if market=='EU':
   for name in ['RETURN_ONLY','HYBRID_ONLY','MOM252']:
    st=dict(np.load(B/'inputs'/f'EU_STATE_{name}_HALF.npz',allow_pickle=False))
    rr,_=replay(st,name+'_HALF','EU');allrows+=rr
    rr,_=replay(st,name+'_HALF_no_risk','EU',mode='no_risk');allrows+=rr
   for ticker in ['EXSA.DE','SXR8.DE','SXRV.DE']:
    st={k:v.copy() for k,v in h.items()};j=st['tickers'].tolist().index(ticker)
    st['d1'][:]=j;st['d2'][:]=j;st['weights'][:]=1.;st['alt'][:]=-1
    rr,_=replay(st,'PASSIVE_'+ticker,'EU',mode='no_risk');allrows+=rr
  pd.DataFrame(allrows).to_csv(OUT/'SCORECARD.csv',index=False)
 (OUT/'AUDITED_US_PARITY.json').write_text(json.dumps(parity,indent=2));(OUT/'LEDGER_COLUMNS.json').write_text(json.dumps(COLS,indent=2))
 print('DONE',len(allrows),flush=True)
if __name__=='__main__':main()
