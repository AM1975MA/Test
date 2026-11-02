"""Fixed OLC19 comparisons, checksummed inputs and independent ledger arithmetic."""
from pathlib import Path
import argparse,json,sys,time,hashlib
import numpy as np
import pandas as pd
from combined_engine import simulate,ROOT,PARENT,CONTRACTS
sys.path.append(str(PARENT/'parent_archive/src'))
sys.path.append(str(PARENT/'parent_archive/parent/olc16_contextual_rank_20261102/src'))
from run_validation import validate_book
from portfolio_metrics_parent import metrics
VARIANTS=('ORIGINAL','CUM_FIT','TOP2_STATIC_REVALUE','TOP2_CONTEXT_REVALUE')
PARENT_CONTROL={'BASE':'NO_STOP','ALARM':'EOD_LOW_NET','FAST_NOLOCK':'PREARM_ALL'}

def extra_metrics(q,r,summary):
    dates=pd.to_datetime(q['dates'][1:]);opening=r['ledger'][:-1,0];rat=r['nav'][:-1]/opening
    rows=[]
    for z in summary:
        mask=(dates>=z['first_valuation'])&(dates<=z['last_valuation']);rr=rat[mask]-1
        l=np.log1p(rr);wealth=np.r_[1.,np.exp(np.cumsum(l))];peak=np.maximum.accumulate(wealth)
        streak=maxstreak=0
        for x in wealth/peak-1:
            streak=streak+1 if x < -1e-12 else 0;maxstreak=max(maxstreak,streak)
        tail=np.sort(rr)[:max(1,int(np.ceil(.05*len(rr))))]
        def window(h):
            if len(l)<h:return np.nan
            sums=np.r_[0.,np.cumsum(l)];return np.expm1(np.min(sums[h:]-sums[:-h]))
        trace=r['risk_trace'][:-1][mask]
        rows.append(dict(**z,worst_day=float(rr.min()),cvar05=float(tail.mean()),worst5=float(window(5)),worst21=float(window(21)),
          max_underwater_sessions=maxstreak,end_underwater=float(wealth[-1]/peak[-1]-1),
          emergency_days=int((trace[:,0]==2).sum()),excluded_weight_days=float(trace[:,2].sum()),
          reentries=int(trace[:,5].sum()),fast_exits=int(trace[:,6].sum()),alarms=int(trace[:,7].sum()),
          blocked_orders=int(r['ledger'][:-1,11][mask].sum())))
    return rows

def run(market,fee,stress=False):
    out=ROOT/'results';(out/'paths').mkdir(exist_ok=True);(out/'events').mkdir(exist_ok=True)
    policies=tuple(k for k,v in CONTRACTS.items() if v[1]) if stress else tuple(CONTRACTS)
    rows=[];checks=[];s0=time.time();friction=.005 if stress else .001
    for v in VARIANTS:
        source=PARENT/f'inputs/{market}_{v}.npz';q=dict(np.load(source,allow_pickle=False));ev=q.pop('events')
        for mode in policies:
            key=f'{market}_{v}_{mode}_F{round(1e4*fee)}_S{round(1e4*friction)}'
            stops=[];alarms=[];orders=[]
            r=simulate(q,ev,contract=mode,fee=fee,friction=friction,event_log=stops,alarm_log=alarms,order_log=orders)
            a=validate_book(q,r);a.update(key=key,market=market,variant=v,contract=mode,fee=fee,stop_friction=friction,
              input_sha256=hashlib.sha256(source.read_bytes()).hexdigest())
            if mode in PARENT_CONTROL and not stress:
                pp=PARENT/f'results/paths/{market}_{v}_{PARENT_CONTROL[mode]}_F{round(1e4*fee)}_S100.npz'
                old=dict(np.load(pp,allow_pickle=False))
                for k in ['nav','ledger','primary_units','defensive_units','free_cash','targets']:
                    np.testing.assert_array_equal(r[k],old[k])
                a['parent_exact']=True
            for field,col in [('fee',6),('slippage',7)]:
                assert abs(sum(x[field] for x in stops)-r['ledger'][:,col].sum())<1e-10
            assert len(stops)==r['ledger'][:,8].sum()
            for z in stops:
                t=list(q['tickers']).index(z['ticker']);k=z['signal_index'];until=z['lock_until']
                assert not r['primary_units'][k+1:min(until+1,len(ev)),t].any()
                z['date']=str(q['dates'][k])[:10]
            for z in alarms:z['date']=str(q['dates'][z['signal_index']])[:10]
            for z in orders:z['date']=str(q['dates'][z['index']])[:10]
            for kind,log in [('stops',stops),('alarms',alarms),('orders',orders)]:
                pd.DataFrame(log).to_csv(out/f'events/{key}_{kind}.csv.gz',index=False)
            np.savez_compressed(out/f'paths/{key}.npz',dates=q['dates'],tickers=q['tickers'],**r)
            a['stops']=len(stops);a['alarms']=len(alarms);a['reentries']=sum(x['kind']=='REENTRY' for x in orders)
            checks.append(a)
            rows.extend(dict(market=market,variant=v,contract=mode,fee=fee,stop_friction=friction,stress=stress,key=key,**z)
                        for z in extra_metrics(q,r,metrics(q,r)))
        stem=f'{market}_{round(1e4*fee)}_{int(stress)}'
        pd.DataFrame(rows).to_csv(out/f'SCORECARD_{stem}.csv',index=False)
        (out/f'CHECKS_{stem}.json').write_text(json.dumps(checks,indent=2))
        print('DONE',market,v,'paths',len(checks),'elapsed',round(time.time()-s0,1),flush=True)

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--market',required=True,choices=['EU','USA']);p.add_argument('--fee',default=.001,type=float);p.add_argument('--stress',action='store_true');a=p.parse_args();run(a.market,a.fee,a.stress)
