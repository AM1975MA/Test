"""Same frozen OLC19 execution for every authentic/null/sensitivity ranking.
V6 is recomputed for each proposed pair; no null gets its own risk policy.
"""
from pathlib import Path
import argparse,json,time,warnings
from concurrent.futures import ProcessPoolExecutor,as_completed
import numpy as np,pandas as pd
from paths import ROOT,P16,P17,P18,P19
from experiment import readcsv,dump
from portfolio_adapter import adapt_state
from run_v6_validation import v6_inputs
from v6_rebuild import rebuild
from combined_engine import simulate
from run_validation import validate_book
from portfolio_metrics_parent import metrics
import importlib.util
_spec=importlib.util.spec_from_file_location('olc19_metric_runner',P19/'src/run_experiment.py')
_parent_runner=importlib.util.module_from_spec(_spec);_spec.loader.exec_module(_parent_runner)
extra_metrics=_parent_runner.extra_metrics

REFERENCE={'AUTH':'TOP2_CONTEXT_REVALUE','STATIC':'TOP2_STATIC_REVALUE','ORIGINAL':'ORIGINAL','CUM_FIT':'CUM_FIT'}

def prepare_state(market,trial):
    q=dict(np.load(P16/f'inputs/{market}_STATE_HALF.npz',allow_pickle=False))
    cal=readcsv(P16/f'inputs/{market}_CALENDAR.csv')
    if trial in ('ORIGINAL','CUM_FIT'):
        sc=readcsv(P16/f'results/{market}_SCORES.csv.gz');sc['FUSION']=sc[trial+'_FUSION']
    else:sc=readcsv(ROOT/f'results/trials/{trial}/{market}_SCORES.csv.gz')
    st,ev,dec=adapt_state(q,cal,sc,'FUSION');ctx,allowed=v6_inputs(q,market)
    with warnings.catch_warnings():
        warnings.filterwarnings('ignore',category=RuntimeWarning)
        # A parity check comes before admitting each reconstruction.
        np.testing.assert_array_equal(rebuild(ctx,allowed=allowed),q['alt'])
        st['alt']=rebuild(ctx,st['d1'],st['d2'],st['weights'],allowed)
    if np.any((st['alt']>=0)&((st['alt']==st['d1'])|(st['alt']==st['d2']))):
        raise AssertionError('V6 overlaps a primary holding')
    return st,ev,dec

def run_case(trial,market):
    start=time.time();q,ev,dec=prepare_state(market,trial)
    folder=ROOT/f'results/portfolios/{trial}';folder.mkdir(parents=True,exist_ok=True)
    dec.to_csv(folder/f'{market}_DECISIONS.csv',index=False)
    np.savez_compressed(folder/f'{market}_TARGETS.npz',d1=q['d1'],d2=q['d2'],weights=q['weights'],alt=q['alt'],events=ev)
    rows=[];checks=[]
    for contract in ('ALARM','FAST_LOCK3'):
        for fee in (.001,.003):
            key=f'{market}_{contract}_{round(fee*10000)}';stops=[]
            r=simulate(q,ev,contract=contract,fee=fee,friction=.001,event_log=stops)
            audit=validate_book(q,r)
            for x in stops:
                t=list(q['tickers']).index(x['ticker']);k=x['signal_index'];end=min(x['lock_until']+1,len(ev))
                if contract=='FAST_LOCK3':assert not r['primary_units'][k+1:end,t].any()
            if trial in REFERENCE:
                ref=P19/f"results/paths/{market}_{REFERENCE[trial]}_{contract}_F{round(fee*10000)}_S10.npz"
                old=np.load(ref,allow_pickle=False)
                for k in r:np.testing.assert_array_equal(r[k],old[k])
                audit['parent_arrays_exact']=True
            audit.update(trial=trial,market=market,contract=contract,fee=fee,key=key,stops=len(stops))
            checks.append(audit)
            rows.extend(dict(trial=trial,market=market,contract=contract,fee=fee,key=key,**z)
                        for z in extra_metrics(q,r,metrics(q,r)))
            np.savez_compressed(folder/f'{key}.npz',dates=q['dates'],tickers=q['tickers'],**r)
            # Save compact independent interval return for all statistical comparisons.
            pd.DataFrame({'date':q['dates'][1:],'log_return':np.log(r['nav'][:-1]/r['ledger'][:-1,0])}).to_csv(folder/f'{key}_RETURNS.csv.gz',index=False)
    pd.DataFrame(rows).to_csv(folder/f'{market}_SCORECARD.csv',index=False)
    dump(folder/f'{market}_CHECKS.json',checks)
    return dict(trial=trial,market=market,paths=len(checks),seconds=time.time()-start)

def main(trials,workers):
    with ProcessPoolExecutor(max_workers=workers) as pool:
        jobs=[pool.submit(run_case,t,m) for t in trials for m in ('EU','USA')]
        for future in as_completed(jobs):print(json.dumps(future.result()),flush=True)
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--trials',nargs='*');p.add_argument('--workers',type=int,default=3);a=p.parse_args()
    names=a.trials or sorted(d.parent.name for d in (ROOT/'results/trials').glob('*/COMPLETE.json'))+['ORIGINAL','CUM_FIT']
    main(names,a.workers)
