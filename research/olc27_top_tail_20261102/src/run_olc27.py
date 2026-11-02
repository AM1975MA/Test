"""OLC27: pre-registered conditional tail-leader selection among AUTH Top5.

Only train on complete, strictly matured historical labels; reuse frozen OLC26
features, OLC20 AUTH scores and OLC19 portfolio engine. This is research only.
"""
from pathlib import Path
import sys, os, json, time, warnings
from concurrent.futures import ProcessPoolExecutor, as_completed
import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import StandardScaler

ROOT=Path(__file__).resolve().parents[1]
P26=Path(os.environ.get('OLC26_ROOT','/mnt/data/olc26_work'))
P20=Path(os.environ.get('OLC20_ROOT','/mnt/data/olc20_work/stage1'))
sys.path.insert(0,str(P20/'src'))
from portfolio_validation import P16,readcsv,adapt_state,v6_inputs,rebuild,simulate,validate_book,metrics,extra_metrics

FEATURES=['FUSION','m63','m126','m252','persist3','interaction']
TRIALS=['AUTH','AUTH_ONLY','LONG_POOL','LONG_STRAT','LONG_POOL_NULL27001','LONG_POOL_NULL27002','LONG_POOL_NULL27003']

def data():
    frames={m:pd.read_csv(P26/'results'/f'{m}_FRAME.csv.gz',parse_dates=['signal_date','maturity_date']) for m in ('EU','USA')}
    base={m:readcsv(P26/'results'/'AUTH'/f'{m}_SCORES.csv.gz') for m in ('EU','USA')}
    for m in ('EU','USA'):
        f=frames[m];s=base[m]
        assert len(f)==len(s),m
        assert f.ticker.astype(str).equals(s.ticker.astype(str))
        assert np.array_equal(f.signal_date.to_numpy(),pd.to_datetime(s.signal_date).to_numpy())
        # The two saved CSVs have harmless decimal round-trip differences (~1e-16);
        # use the canonical AUTH score array for every fit and decision.
        np.testing.assert_allclose(f.FUSION.to_numpy(float),s.FUSION.to_numpy(float),rtol=0,atol=2e-16,equal_nan=True)
        f['FUSION']=s['FUSION'].to_numpy(float)
    return frames,base

def fit_cutoff(frames,year,trial,market=None):
    cols=['FUSION'] if trial=='AUTH_ONLY' else FEATURES
    cutoff=pd.Timestamp(year,1,1)
    df=pd.concat([frames[m] for m in ('EU','USA')],ignore_index=True) if market is None else frames[market].copy()
    valid=(df.maturity_date.notna()&(df.maturity_date<cutoff)&df.future126.notna()&
           np.isfinite(df[cols].to_numpy(float)).all(axis=1)&np.isfinite(df.FUSION))
    train=df.loc[valid].copy().reset_index(drop=True)
    markets=('EU','USA') if market is None else (market,)
    counts={m:train.loc[train.market==m,'signal_date'].nunique() for m in markets}
    base_meta=dict(year=year,market=market,trial=trial,cutoff=str(cutoff.date()),n_rows=len(train),months=counts)
    if not counts or min(counts.values())<12:
        return None,{**base_meta,'fallback':True}
    assert (train.maturity_date<cutoff).all()
    assert (train.signal_date<train.maturity_date).all()
    train['grp_n']=train.groupby(['market','signal_date']).ticker.transform('size')
    train['months']=train.groupby('market').signal_date.transform('nunique')
    weights=(1.0/(train.grp_n*train.months)).to_numpy(float)
    weights*=len(weights)/weights.sum()
    grp_weights={m:float(weights[train.market.to_numpy()==m].sum()/weights.sum()) for m in markets}
    if market is None:
        assert abs(grp_weights['EU']-.5)<1e-12 and abs(grp_weights['USA']-.5)<1e-12
    y=(train.future126.to_numpy(float)>=.9).astype(int)
    if 'NULL' in trial:
        seed=int(trial.split('NULL')[1]);rng=np.random.default_rng(seed+year*1000)
        for g in train.groupby(['market','signal_date'],sort=True).indices.values():
            ix=np.asarray(g,dtype=int)
            y[ix]=y[rng.permutation(ix)]
    X=train[cols].to_numpy(float)
    scaler=StandardScaler().fit(X,sample_weight=weights)
    Z=scaler.transform(X)
    mdl=LogisticRegression(C=.1,penalty='l2',solver='lbfgs',max_iter=500,class_weight=None).fit(Z,y,sample_weight=weights)
    meta={**base_meta,'fallback':False,'last_maturity':str(train.maturity_date.max().date()),'labels_positive':int(y.sum()),
          'positive_rate':float(np.average(y,weights=weights)),'groups_weight':grp_weights,
          'coefs':mdl.coef_.ravel().tolist(),'intercept':float(mdl.intercept_[0]),
          'scale_mean':scaler.mean_.tolist(),'scale_std':scaler.scale_.tolist(), 'features':cols}
    return (scaler,mdl,cols),meta

def rank_top(scores,limit):
    vals=scores[np.isfinite(scores.FUSION.to_numpy(float))].sort_values(['FUSION','ticker'],ascending=[False,True],kind='mergesort')
    return vals.head(limit)

def choose_top5(sub,prob):
    """Pure decision; one candidate among AUTH ranks 3-5 and at most one swap."""
    top=rank_top(sub,5)
    out=list(top.head(2).ticker)
    if len(top)<5:return out,None
    pp=prob.reindex(top.index)
    if pp.isna().any():return out,None
    pick=top.iloc[2:].copy();pick['p']=pp.iloc[2:].to_numpy(float)
    best=pick.sort_values(['p','FUSION','ticker'],ascending=[False,False,True],kind='mergesort').iloc[0]
    inc=top.iloc[:2].copy();inc['p']=pp.iloc[:2].to_numpy(float)
    worst=inc.sort_values(['p','FUSION','ticker'],ascending=[True,True,True],kind='mergesort').iloc[0]
    diff=float(best.p-worst.p)
    gap=float(worst.FUSION-best.FUSION)
    if diff<.05 or gap>.05:return out,None
    proposal=[x for x in out if x!=worst.ticker]+[best.ticker]
    assert len(set(proposal))==2
    return proposal,dict(add=str(best.ticker),drop=str(worst.ticker),p_diff=diff,auth_gap=gap,threshold=float(top.iloc[1].FUSION))

def apply_swaps(frames,base,trial):
    out={m:base[m].copy() for m in ('EU','USA')}
    decisions={m:[] for m in ('EU','USA')}
    preds={m:pd.Series(np.nan,index=frames[m].index,dtype=float) for m in ('EU','USA')}
    meta=[]
    if trial=='AUTH':return out,decisions,preds,meta
    mode='STRAT' if trial=='LONG_STRAT' else 'POOL'
    for year in range(2021,2027):
        for market in (('EU','USA') if mode=='STRAT' else (None,)):
            fm,details=fit_cutoff(frames,year,trial,market)
            meta.append(details)
            for m in (('EU','USA') if market is None else (market,)):
                f=frames[m]
                mask=(f.signal_date.dt.year==year)
                if fm is None:continue
                scaler,mdl,cols=fm
                good=mask & np.isfinite(f[cols].to_numpy(float)).all(axis=1)
                if good.any():preds[m].loc[good]=mdl.predict_proba(scaler.transform(f.loc[good,cols].to_numpy(float)))[:,1]
    for m in ('EU','USA'):
        f=frames[m];s=out[m]
        for date,ix in f.groupby('signal_date',sort=True).indices.items():
            idx=np.asarray(ix,int)
            tab=s.iloc[idx].copy()
            proposed,swap=choose_top5(tab,preds[m].iloc[idx])
            if swap:
                # Propose exact one insertion using a frozen deterministic adapter shift.
                loc=idx[np.flatnonzero(tab.ticker.to_numpy()==swap['add'])[0]]
                orig=float(s.at[loc,'FUSION'])
                s.at[loc,'FUSION']=swap['threshold']+1e-8
                actual=list(rank_top(s.iloc[idx],2).ticker)
                if set(actual)!=set(proposed):
                    s.at[loc,'FUSION']=orig
                    swap=None
            if swap:decisions[m].append(dict(date=str(date.date()),market=m,**swap))
        assert np.array_equal(np.isfinite(s.FUSION.to_numpy(float)),np.isfinite(base[m].FUSION.to_numpy(float)))
    return out,decisions,preds,meta

def score_and_write():
    frames,base=data()
    for trial in TRIALS:
        start=time.time();out,changes,pred,models=apply_swaps(frames,base,trial)
        folder=ROOT/'results'/trial;folder.mkdir(parents=True,exist_ok=True)
        for market in ('EU','USA'):
            out[market].to_csv(folder/f'{market}_SCORES.csv.gz',index=False)
            pd.DataFrame(changes[market],columns=['date','market','add','drop','p_diff','auth_gap','threshold']).to_csv(folder/f'{market}_SWAPS.csv',index=False)
            d=frames[market][['signal_date','ticker','future126','maturity_date']].copy()
            d['p_tail']=pred[market]
            d.to_csv(folder/f'{market}_PREDICTIONS.csv.gz',index=False)
        (folder/'ANNUAL_MODELS.json').write_text(json.dumps(models,indent=2,default=str))
        print(json.dumps(dict(trial=trial,swaps={m:len(changes[m]) for m in ('EU','USA')},models=sum(not x['fallback'] for x in models),seconds=round(time.time()-start,1))),flush=True)

def replay_one(trial,market):
    start=time.time()
    sc=readcsv(ROOT/f'results/{trial}/{market}_SCORES.csv.gz')
    q=dict(np.load(P16/f'inputs/{market}_STATE_HALF.npz',allow_pickle=False))
    cal=readcsv(P16/f'inputs/{market}_CALENDAR.csv')
    st,events,dec=adapt_state(q,cal,sc,'FUSION')
    ctx,allowed=v6_inputs(q,market)
    with warnings.catch_warnings():
        warnings.filterwarnings('ignore',category=RuntimeWarning)
        np.testing.assert_array_equal(rebuild(ctx,allowed=allowed),q['alt'])
        st['alt']=rebuild(ctx,st['d1'],st['d2'],st['weights'],allowed)
    assert not np.any((st['alt']>=0)&((st['alt']==st['d1'])|(st['alt']==st['d2'])))
    folder=ROOT/'results'/trial
    dec.to_csv(folder/f'{market}_DECISIONS.csv',index=False)
    results=[];audits=[]
    for contract in ('ALARM','FAST_LOCK3'):
        for fee in (.001,.003):
            key=f'{market}_{contract}_{round(fee*10000)}'
            rv=simulate(st,events,contract=contract,fee=fee,friction=.001)
            audit=validate_book(st,rv)
            if trial=='AUTH':
                parent=np.load(P20/f'results/portfolios/AUTH/{key}.npz',allow_pickle=False)
                for k in rv:np.testing.assert_array_equal(rv[k],parent[k])
            results.extend(dict(trial=trial,market=market,contract=contract,fee=fee,key=key,**a) for a in extra_metrics(st,rv,metrics(st,rv)))
            audits.append(dict(market=market,trial=trial,contract=contract,fee=fee,audit=audit))
            if '_NULL' not in trial:
                pd.DataFrame({'date':st['dates'][1:],'log_return':np.log(rv['nav'][:-1]/rv['ledger'][:-1,0])}).to_csv(folder/f'{key}_RETURNS.csv.gz',index=False)
                if contract=='FAST_LOCK3' and fee==.001:
                    np.savez_compressed(folder/f'{key}.npz',dates=st['dates'],nav=rv['nav'],ledger=rv['ledger'],risk_trace=rv['risk_trace'])
    pd.DataFrame(results).to_csv(folder/f'{market}_SCORECARD.csv',index=False)
    (folder/f'{market}_CHECKS.json').write_text(json.dumps(audits,indent=2,default=str))
    return dict(trial=trial,market=market,account_paths=4,metric_rows=len(results),seconds=round(time.time()-start,2))

def replay_all(workers=3):
    with ProcessPoolExecutor(max_workers=workers) as pool:
        fut=[pool.submit(replay_one,t,m) for t in TRIALS for m in ('EU','USA')]
        for x in as_completed(fut):print(json.dumps(x.result()),flush=True)

if __name__=='__main__':
    import argparse
    a=argparse.ArgumentParser();a.add_argument('--stage',required=True,choices=['scores','replay']);a.add_argument('--workers',type=int,default=3);x=a.parse_args()
    score_and_write() if x.stage=='scores' else replay_all(x.workers)
