"""Paired policy comparisons and full stop-event diagnostics. Never retune parameters."""
from pathlib import Path
import json
import numpy as np,pandas as pd
ROOT=Path(__file__).resolve().parents[1];R=ROOT/'results'
C='TOP2_CONTEXT_REVALUE';S='TOP2_STATIC_REVALUE'

def main():
 f=pd.concat([pd.read_csv(p) for p in R.glob('SCORECARD_*.csv')],ignore_index=True)
 assert not f.duplicated(['key','period']).any()
 f.to_csv(R/'SCORECARD.csv',index=False)
 changes=[];events=[];requests=[];alarms=[]
 for (market,contract,fee,stress,period),g in f.groupby(['market','contract','fee','stress','period']):
  d=g.set_index('variant')
  for b in (S,'CUM_FIT','ORIGINAL'):
   changes.append(dict(market=market,contract=contract,fee=fee,stress=stress,period=period,baseline=b,
    cagr=d.at[C,'cagr'],baseline_cagr=d.at[b,'cagr'],delta_cagr=d.at[C,'cagr']-d.at[b,'cagr'],
    maxdd=d.at[C,'maxdd'],baseline_maxdd=d.at[b,'maxdd'],delta_maxdd=d.at[C,'maxdd']-d.at[b,'maxdd'],
    period_return=d.at[C,'period_return'],baseline_return=d.at[b,'period_return']))
 pd.DataFrame(changes).to_csv(R/'PAIRED_POLICY_COMPARISONS.csv',index=False)
 for a in f.drop_duplicates('key').to_dict('records'):
  p=dict(np.load(R/f"paths/{a['key']}.npz",allow_pickle=False))
  ep=R/f"events/{a['key']}.csv.gz"
  try:e=pd.read_csv(ep)
  except pd.errors.EmptyDataError:e=pd.DataFrame()
  for z in e.to_dict('records'):
   k=int(z['signal_index']);j=k+1;t=list(p['tickers']).index(z['ticker'])
   # Actual rebalance purchase before any later stop, not merely end-day holdings.
   rebuy=bool(p['ledger'][j,3] and p['targets'][j,t]*p['ledger'][j,1]>0)
   z.update(key=a['key'],market=a['market'],variant=a['variant'],contract=a['contract'],fee_rate=a['fee'],stress=a['stress'],
    rebuy_next_open=rebuy,close_recovered=z['close']>z['barrier'],next_open_recovered=z['next_open']>z['barrier'])
   events.append(z)
   if a['contract']=='LEGACY' and a['fee']==.001:
    requests.append(dict(market=a['market'],variant=a['variant'],date=z['signal_date'],ticker=z['ticker'],opening_breach=z['opening_breach'],
      required='Timestamped first prints/breadth, executable bid/ask, position order, activation-before-barrier chronology'))
  ap=R/f"events/{a['key']}_ALARMS.csv.gz"
  if ap.exists():
   try:al=pd.read_csv(ap)
   except pd.errors.EmptyDataError:al=pd.DataFrame()
   for z in al.to_dict('records'):
    j=int(z['action_index']);z.update(key=a['key'],market=a['market'],variant=a['variant'],contract=a['contract'],fee_rate=a['fee'],
     rebalance_executed=bool(p['ledger'][j,3]),rebalance_blocked=bool(p['ledger'][j,11]),actual_main_gross=float(p['ledger'][j,1]))
    alarms.append(z)
 pd.DataFrame(events).to_csv(R/'ALL_STOP_EVENTS.csv.gz',index=False)
 pd.DataFrame(alarms).to_csv(R/'ALL_NET_ALARMS.csv.gz',index=False)
 pd.DataFrame(requests).drop_duplicates().to_csv(R/'INTRADAY_VALIDATION_REQUIRED.csv',index=False)
 e=pd.DataFrame(events);e=e[e.fee_rate.eq(.001)&~e.stress&e.signal_date.between('2021-01-01','2024-12-31')]
 s=e.groupby(['market','variant','contract']).agg(stops=('ticker','size'),rebuys_next_open=('rebuy_next_open','sum'),gap_triggers=('opening_breach','sum'),intraday_recoveries=('close_recovered','sum'),same_day_increase=('newly_bought_quantity',lambda v:(v>1e-12).sum()))
 s.to_csv(R/'STOP_SUMMARY_MAIN.csv')
 rng=np.random.default_rng(20261102);ix=((rng.integers(0,48,(4000,8))[:,:,None]+np.arange(6))%48).reshape(4000,48);unc=[]
 for m in ('EU','USA'):
  for policy in ('EOD_LOW_NET','EOD_CLOSE_NET'):
   cf=f[(f.market==m)&(f.variant==C)&(f.contract==policy)&(f.fee==.001)&~f.stress].iloc[0]
   cp=np.load(R/f"paths/{cf['key']}.npz");dates=pd.to_datetime(cp['dates'][1:]);cl=np.diff(np.log(np.r_[1.,cp['nav']]))[:-1]
   for b in (S,'CUM_FIT','ORIGINAL'):
    bf=f[(f.market==m)&(f.variant==b)&(f.contract==policy)&(f.fee==.001)&~f.stress].iloc[0]
    bp=np.load(R/f"paths/{bf['key']}.npz");bl=np.diff(np.log(np.r_[1.,bp['nav']]))[:-1]
    mo=pd.Series(cl-bl,index=dates).groupby(dates.to_period('M')).sum().reindex(pd.period_range('2021-01','2024-12',freq='M')).to_numpy()
    bs=mo[ix].mean(1)*12;lo,hi=np.quantile(bs,[.025,.975])
    unc.append(dict(market=m,contract=policy,baseline=b,annual_log=mo.mean()*12,lower=lo,upper=hi,months=48,
     note='Descriptive paired6month bootstrap,4000draws;not posterior or multiplicity corrected;reused history.'))
 pd.DataFrame(unc).to_csv(R/'UNCERTAINTY.csv',index=False)
 audits=[a for p in R.glob('AUDIT_*.json') for a in json.loads(p.read_text())['completed']]
 summary=dict(paths=len(audits),intervals=sum(x['intervals'] for x in audits),metric_values=sum(len(x['metrics'])*3 for x in audits),
  maximum_nav_error=max(x['nav_error'] for x in audits),maximum_metric_error=max(z['maximum_metric_error'] for x in audits for z in x['metrics']),
  exact_parent_paths=sum(x.get('parent_arrays_exact',False) for x in audits),new_models=0,
  blocked_paths=[a for p in R.glob('AUDIT_*.json') for a in json.loads(p.read_text())['blocked']])
 (R/'VERIFIED_SUMMARY.json').write_text(json.dumps(summary,indent=2))
 print(json.dumps(summary,indent=2));print(pd.DataFrame(unc).round(6).to_string(index=False))

if __name__=='__main__':main()
