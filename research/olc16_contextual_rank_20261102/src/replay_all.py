"""Frozen portfolio accounting and executable-quote checks for OLC16."""
import argparse,time,json
import numpy as np,pandas as pd
from experiment import ROOT,MARKETS,VARIANTS,CONTROLS,readcsv,dump
from portfolio_adapter import adapt_state
from portfolio_metrics_parent import metrics,policy_args
from vector_engine import simulate
from accounting import decompose

def main(controls_only=False,partition=None):
    rows=[];checks=[];decisions=[];out=ROOT/'results';(out/'paths').mkdir(exist_ok=True);t=time.time()
    for m in MARKETS:
        q=dict(np.load(ROOT/f'inputs/{m}_STATE_HALF.npz',allow_pickle=False));cal=readcsv(ROOT/f'inputs/{m}_CALENDAR.csv')
        scores=readcsv(ROOT/f'inputs/{m}_MEAN3_SCORES.csv.gz') if controls_only else readcsv(out/f'{m}_SCORES.csv.gz')
        for v in CONTROLS if controls_only else (VARIANTS[4*partition:4*partition+4] if partition is not None else VARIANTS):
            st,ev,dd=adapt_state(q,cal,scores,v+'_FUSION');dd['market']=m;dd['variant']=v;decisions.append(dd)
            for mode in ['FULL','LAG1']:
                for pol in ['IMMEDIATE','DELAY3','PHASE5'] if mode=='FULL' else ['IMMEDIATE']:
                    for fee in [.001,.003]:
                        key=f'{m}_{v}_{pol}_{mode}_C{round(fee*10000)}'
                        r=simulate(st,ev,fee=fee,lag_systemic=mode=='LAG1',**policy_args(pol))
                        cap=((r['primary_units'][:-1]+r['defensive_units'][:-1])*st['O'][1:]).sum(1)+r['free_cash'][:-1]
                        err=float(np.max(abs(cap-r['nav'][:-1])));assert err<1e-10
                        attr=decompose(st,r);logerr=float(np.max(abs(attr['log_components'].sum(1)-attr['log_return'])));assert logerr<1e-12
                        parenterr=None
                        if v in CONTROLS:
                            old=np.load(ROOT/f'inputs/oracles/{key}.npz');parenterr=max(float(np.max(abs(r[k]-old[k]))) for k in r)
                            for k in r:np.testing.assert_allclose(r[k],old[k],atol=5e-12,rtol=5e-13)
                            for k in ['primary_units','defensive_units','targets','free_cash']:np.testing.assert_array_equal(r[k],old[k])
                        obs=st.get('observed',np.ones_like(st['O'],bool));before=np.vstack([np.zeros(st['O'].shape[1]),r['primary_units'][:-1]])
                        assert not ((abs(r['primary_units']-before)>1e-12)&(~obs)).any()
                        np.savez_compressed(out/f'paths/{key}.npz',dates=st['dates'],tickers=st['tickers'],**r)
                        rows.extend(dict(market=m,variant=v,policy=pol,mode=mode,fee=fee,config=key,**z) for z in metrics(st,r))
                        checks.append(dict(config=key,intervals=len(st['dates'])-1,nav_error=err,log_error=logerr,parent_error=parenterr))
            print('PORTFOLIO',m,v,'paths',len(checks),'seconds',round(time.time()-t,1),flush=True)
    if controls_only:
        dump(out/'PARITY.json',dict(paths=len(checks),max_error=max(c['parent_error'] for c in checks),holdings_exact=True,checks=checks))
    else:
        suffix=f'_part{partition}' if partition is not None else ''
        pd.DataFrame(rows).to_csv(out/f'SCORECARD{suffix}.csv',index=False);pd.DataFrame(checks).to_csv(out/f'PATH_VERIFICATION{suffix}.csv',index=False)
        pd.concat(decisions).to_csv(out/f'PORTFOLIO_PROPOSALS{suffix}.csv',index=False)
        dump(out/f'REPLAY_COMPLETE{suffix}.json',dict(paths=len(checks),controls=48,intervals=sum(c['intervals'] for c in checks),
             max_nav_error=max(c['nav_error'] for c in checks),max_log_error=max(c['log_error'] for c in checks)))
if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('--controls',action='store_true');ap.add_argument('--partition',type=int);args=ap.parse_args();main(args.controls,args.partition)
