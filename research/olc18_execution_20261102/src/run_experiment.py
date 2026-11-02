"""Preregistered stop-contract matrix. No refits, no parameter search."""
from pathlib import Path
import sys,json,argparse,warnings,time,hashlib
import numpy as np,pandas as pd
ROOT=Path(__file__).resolve().parents[1];P=ROOT/'parent_archive';P16=P/'parent/olc16_contextual_rank_20261102'
sys.path.append(str(P/'src'));sys.path.append(str(P16/'src'))
from stop_engine import simulate
from stop_contract import POLICIES
from run_validation import validate_book
from portfolio_adapter import adapt_state
from portfolio_metrics_parent import metrics
from v6_rebuild import rebuild
from run_v6_validation import v6_inputs
VARIANTS=('ORIGINAL','CUM_FIT','TOP2_STATIC_REVALUE','TOP2_CONTEXT_REVALUE')

def read(p):
 f=pd.read_csv(p,float_precision='round_trip')
 for c in ('signal_date','entry_date','exit_date'):
  if c in f:f[c]=pd.to_datetime(f[c])
 return f

def prepare():
 out=ROOT/'inputs';out.mkdir(exist_ok=True);audit=[]
 for m in ('EU','USA'):
  q=dict(np.load(P16/f'inputs/{m}_STATE_HALF.npz',allow_pickle=False));cal=read(P16/f'inputs/{m}_CALENDAR.csv');scores=read(P16/f'results/{m}_SCORES.csv.gz')
  ctx,allow=v6_inputs(q,m)
  with warnings.catch_warnings():
   warnings.simplefilter('ignore',RuntimeWarning)
   np.testing.assert_array_equal(rebuild(ctx,allowed=allow),q['alt'])
   for v in VARIANTS:
    st,ev,dec=adapt_state(q,cal,scores,v+'_FUSION')
    st['alt']=rebuild(ctx,st['d1'],st['d2'],st['weights'],allow)
    assert not np.any((st['alt']>=0)&((st['alt']==st['d1'])|(st['alt']==st['d2'])))
    np.savez_compressed(out/f'{m}_{v}.npz',events=ev,**st)
    dec.to_csv(out/f'{m}_{v}_DECISIONS.csv',index=False)
    p=out/f'{m}_{v}.npz';audit.append(dict(market=m,variant=v,sha256=hashlib.sha256(p.read_bytes()).hexdigest(),rows=len(st['dates']),columns=len(st['tickers'])))
 (ROOT/'results/INPUT_AUDIT.json').write_text(json.dumps(audit,indent=2))

def run(m,fee,stress=False,net=False):
 out=ROOT/'results';(out/'paths').mkdir(parents=True,exist_ok=True);(out/'events').mkdir(exist_ok=True)
 ps=('EOD_LOW_NET','EOD_CLOSE_NET') if net else (('PREARM_WEAK','PREARM_ALL','EOD_LOW','EOD_CLOSE') if stress else tuple(x for x in POLICIES if not x.endswith('_NET')))
 rows=[];audits=[];failures=[];start=time.time()
 for v in VARIANTS:
  q=dict(np.load(ROOT/f'inputs/{m}_{v}.npz',allow_pickle=False));ev=q.pop('events');ds=pd.to_datetime(q['dates'])
  for policy in ps:
   friction=.005 if stress else (None if policy in ('LEGACY','PREVIOUS','NO_STOP') else .001)
   key=f'{m}_{v}_{policy}_F{int(fee*10000)}_S{500 if stress else 100}'
   log=[];alarms=[]
   try:r=simulate(q,ev,contract=policy,friction=friction,fee=fee,event_log=log,alarm_log=alarms)
   except ValueError as exc:
    failures.append(dict(key=key,error=str(exc)));print('BLOCKED',key,str(exc),flush=True);continue
   checks=validate_book(q,r);checks.update(key=key,market=m,variant=v,contract=policy,fee=fee,friction=friction)
   if policy in ('LEGACY','PREVIOUS'):
    oldmode='LEGACY' if policy=='LEGACY' else 'ALL_PREOPEN'
    path=P/f'results/paths/{m}_{v}_{oldmode}_V6_{round(fee*10000)}.npz'
    old=dict(np.load(path,allow_pickle=False))
    for k in r:np.testing.assert_array_equal(r[k],old[k])
    checks['parent_arrays_exact']=True
   e=pd.DataFrame(log)
   if len(e):
    e['signal_date']=[str(ds[k].date()) for k in e.signal_index];e['execution_date']=[str(ds[k].date()) for k in e.execution_index]
    for k,idx in [('fee',6),('slippage',7)]:
     assert abs(e[k].sum()-r['ledger'][:,idx].sum())<1e-10
   assert len(log)==r['ledger'][:,8].sum()
   e.to_csv(out/f'events/{key}.csv.gz',index=False)
   al=pd.DataFrame(alarms)
   if len(al):
    al['signal_date']=[str(ds[k].date()) for k in al.signal_index];al['action_date']=[str(ds[k].date()) for k in al.action_index]
   al.to_csv(out/f'events/{key}_ALARMS.csv.gz',index=False)
   checks['alarms']=len(alarms)
   np.savez_compressed(out/f'paths/{key}.npz',dates=q['dates'],tickers=q['tickers'],**r)
   rows.extend(dict(key=key,market=m,variant=v,contract=policy,fee=fee,friction=friction,stress=stress,**z) for z in metrics(q,r))
   audits.append(checks)
  stem=f'{m}_{round(fee*10000)}_{int(stress)}'+('_NET' if net else '')
  pd.DataFrame(rows).to_csv(out/f'SCORECARD_{stem}.csv',index=False)
  (out/f'AUDIT_{stem}.json').write_text(json.dumps({'completed':audits,'blocked':failures},indent=2))
  print('DONE',m,v,'paths',len(audits),'blocked',len(failures),'seconds',round(time.time()-start,1),flush=True)

if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--prepare',action='store_true');p.add_argument('--market',choices=['EU','USA']);p.add_argument('--fee',type=float,default=.001);p.add_argument('--stress',action='store_true');p.add_argument('--net',action='store_true');a=p.parse_args()
 if a.prepare:prepare()
 else:run(a.market,a.fee,a.stress,a.net)
