"""OLC25 causal long-horizon momentum/persistence overlay.
Only uses OLC20 AUTH scores, already archived Close at/before signal,
and the authenticated OLC19 replay. Nothing is trained.
"""
from pathlib import Path
import sys, os, json, warnings, time, argparse
from concurrent.futures import ProcessPoolExecutor, as_completed
import numpy as np
import pandas as pd
ROOT=Path(__file__).resolve().parents[1]
P20=Path(os.environ.get('OLC20_ROOT','/mnt/data/olc20_work/stage1'))
sys.path.insert(0, str(P20/'src'))
from portfolio_validation import P16, readcsv, adapt_state, v6_inputs, rebuild, simulate, validate_book, metrics, extra_metrics

BASE=['AUTH']
MAIN=[f'{f}_W{int(w*100)}' for f in ('M126','M252','PERSIST3') for w in (.2,.4)]
NULL=[f'{f}_W40_NULL{seed}' for f in ('M126','M252','PERSIST3') for seed in range(25001,25006)]
TRIALS=BASE+MAIN+NULL


def feature_table(market):
    q=np.load(P16/f'inputs/{market}_STATE_HALF.npz',allow_pickle=False)
    C=q['C']; dates=pd.DatetimeIndex(q['dates']); tickers=np.array(q['tickers']);
    observed=q['observed'] if market=='EU' else np.isfinite(C)&(C>0)
    cal=readcsv(P16/f'inputs/{market}_CALENDAR.csv')
    base=readcsv(P20/f'results/trials/AUTH/{market}_SCORES.csv.gz')
    idx={name:i for i,name in enumerate(tickers)}
    table=[];base_sets={date:group.copy() for date,group in base.groupby('signal_date',sort=True)}
    dates_sig=sorted(base_sets)
    snapshots=[]
    for date in dates_sig:
        group=base_sets[date];tt=group.ticker.to_numpy();k=dates.get_indexer([date])[0]
        assert len(group)==len(set(tt)),('duplicate ticker',market,date)
        percentile={}
        for lag in (126,252):
            vals=np.full(len(tt),np.nan)
            if k>=lag:
                for a,t in enumerate(tt):
                    v=idx.get(t,-1)
                    if v<0:continue
                    if observed[k,v] and observed[k-lag,v] and C[k,v]>0 and C[k-lag,v]>0 and np.isfinite(C[k,v]*C[k-lag,v]):
                        vals[a]=np.log(C[k,v]/C[k-lag,v])
            p=pd.Series(vals).rank(pct=True,method='average').to_numpy()
            percentile[lag]=p
        snapshots.append(dict(date=date,tickers=tt,p126=percentile[126],p252=percentile[252]))
        for a,t in enumerate(tt):
            table.append(dict(market=market,date=str(date.date()),ticker=t,m126=percentile[126][a],m252=percentile[252][a],
                              original=float(group.iloc[a].FUSION)))
    # The previous two dates are included only if all three snapshots have observed momentum.
    pers=[]
    for i,s in enumerate(snapshots):
        if i<2:pers.extend([np.nan]*len(s['tickers']));continue
        old=[]
        for h in (i-2,i-1,i):
            old.append(dict(zip(snapshots[h]['tickers'],snapshots[h]['p126'])))
        pers.extend([np.mean([row.get(t,np.nan) for row in old]) if np.isfinite([row.get(t,np.nan) for row in old]).all() else np.nan for t in s['tickers']])
    frame=pd.DataFrame(table)
    frame['persist3']=pers
    assert len(frame)==len(base)
    assert np.array_equal(frame.ticker.to_numpy(),base.ticker.to_numpy())
    assert np.array_equal(pd.to_datetime(frame.date).to_numpy(),base.signal_date.to_numpy())
    assert np.allclose(frame.original.to_numpy(),base.FUSION.to_numpy(),equal_nan=True,rtol=0,atol=0)
    assert len(frame.groupby('date'))==90
    return base,frame,q,cal


def scores_for_trial(base,features,trial,market):
    if trial=='AUTH':return base.copy()
    family=trial.split('_W')[0]
    w=float(trial.split('_W')[1][:2])/100.
    name={'M126':'m126','M252':'m252','PERSIST3':'persist3'}[family]
    p=features[name].to_numpy(float).copy()
    if '_NULL' in trial:
        seed=int(trial.split('NULL')[1]);rng=np.random.default_rng(seed+(0 if market=='EU' else 10_000))
        for _,inds in features.groupby('date',sort=True).indices.items():
            ix=np.asarray(inds,int);valid=ix[np.isfinite(p[ix]) & np.isfinite(base.FUSION.to_numpy(float)[ix])];p[valid]=p[rng.permutation(valid)]
    p=np.where(np.isfinite(p),p,0.5)
    out=base.copy();out['FUSION']=(1-w)*out['FUSION'].to_numpy(float)+w*p
    assert np.isfinite(out['FUSION']).sum()==np.isfinite(base['FUSION']).sum()
    assert ((out.signal_date==base.signal_date)&(out.ticker==base.ticker)).all()
    return out


def replay(trial,market):
    start=time.time()
    base,feat,q,cal=feature_table(market)
    sc=scores_for_trial(base,feat,trial,market)
    if trial=='AUTH':
        np.testing.assert_array_equal(sc['FUSION'].to_numpy(),base['FUSION'].to_numpy())
    state,events,dec=adapt_state({k:v.copy() for k,v in q.items()},cal,sc,'FUSION')
    ctx,allowed=v6_inputs({k:v for k,v in q.items()},market)
    with warnings.catch_warnings():
        warnings.filterwarnings('ignore',category=RuntimeWarning)
        np.testing.assert_array_equal(rebuild(ctx,allowed=allowed),q['alt'])
        state['alt']=rebuild(ctx,state['d1'],state['d2'],state['weights'],allowed)
    assert not np.any((state['alt']>=0)&((state['alt']==state['d1'])|(state['alt']==state['d2'])))
    folder=ROOT/'results'/trial;folder.mkdir(exist_ok=True,parents=True)
    if trial=='AUTH' or '_NULL' not in trial:
        dec.to_csv(folder/f'{market}_DECISIONS.csv',index=False)
    rows=[];checks=[]
    for contract in ('ALARM','FAST_LOCK3'):
        for fee in (.001,.003):
            key=f'{market}_{contract}_{round(fee*10000)}'
            book=simulate(state,events,contract=contract,fee=fee,friction=.001)
            audit=validate_book(state,book)
            if trial=='AUTH':
                parent=np.load(P20/f'results/portfolios/AUTH/{key}.npz')
                for col in book:
                    np.testing.assert_array_equal(book[col],parent[col])
                audit['olc20_parent_arrays_exact']=True
            rows.extend(dict(trial=trial,market=market,contract=contract,fee=fee,key=key,**z)
                        for z in extra_metrics(state,book,metrics(state,book)))
            checks.append(dict(trial=trial,market=market,contract=contract,fee=fee,
                               max_metric_abs_error=audit.get('max_metric_abs_error'),
                               max_nav_abs_error=audit.get('max_nav_abs_error'),
                               audit=audit))
            if trial=='AUTH' or '_NULL' not in trial:
                # Lightweight return sequences for matched comparisons and audits.
                pd.DataFrame({'date':state['dates'][1:],
                  'log_return':np.log(book['nav'][:-1]/book['ledger'][:-1,0])}).to_csv(folder/f'{key}_RETURNS.csv.gz',index=False)
                # Only primary-stress pair full NAV to limit memory and output.
                if contract=='FAST_LOCK3' and fee==.001:
                    np.savez_compressed(folder/f'{key}.npz',dates=state['dates'],tickers=state['tickers'],nav=book['nav'],
                         ledger=book['ledger'],primary_units=book['primary_units'],targets=book['targets'],risk_trace=book['risk_trace'])
    pd.DataFrame(rows).to_csv(folder/f'{market}_SCORECARD.csv',index=False)
    (folder/f'{market}_CHECKS.json').write_text(json.dumps(checks,indent=2,default=str))
    return dict(trial=trial,market=market,rows=len(rows),checks=len(checks),seconds=time.time()-start)


def prepare_features():
    folder=ROOT/'results';folder.mkdir(parents=True,exist_ok=True)
    for market in ('EU','USA'):
        base,features,q,cal=feature_table(market)
        features.to_csv(folder/f'{market}_FEATURES.csv.gz',index=False)
        for trial in TRIALS:
            sc=scores_for_trial(base,features,trial,market)
            if trial=='AUTH' or '_NULL' not in trial:
                dest=ROOT/'results'/trial;dest.mkdir(parents=True,exist_ok=True)
                sc.to_csv(dest/f'{market}_SCORES.csv.gz',index=False)
        print(json.dumps(dict(market=market,features=len(features),source=len(base),available={k:int(features[k].notna().sum()) for k in ('m126','m252','persist3')},trials=len(TRIALS))),flush=True)


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--stage',choices=['features','replay'],default='features');parser.add_argument('--workers',type=int,default=3);parser.add_argument('--trials',nargs='*');a=parser.parse_args()
    if a.stage=='features':prepare_features();return
    trials=a.trials or TRIALS
    with ProcessPoolExecutor(max_workers=a.workers) as pool:
        futures=[pool.submit(replay,trial,market) for trial in trials for market in ('EU','USA')]
        for fut in as_completed(futures):print(json.dumps(fut.result()),flush=True)
if __name__=='__main__':main()
