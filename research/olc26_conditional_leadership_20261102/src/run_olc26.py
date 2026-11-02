"""OLC26 supervised, causally annual refit long-leadership residual ranker.
Parent: frozen OLC20 AUTH + original prepared panels. No new base ETF fits.
"""
from pathlib import Path
import sys, os, json, warnings, argparse, time
from concurrent.futures import ProcessPoolExecutor,as_completed
import numpy as np
import pandas as pd
from sklearn.linear_model import Ridge
from sklearn.preprocessing import StandardScaler
ROOT=Path(__file__).resolve().parents[1]
P20=Path(os.environ.get('OLC20_ROOT','/mnt/data/olc20_work/stage1'))
P25=Path(os.environ.get('OLC25_ROOT','/mnt/data/olc25_work'))
sys.path.insert(0,str(P20/'src'))
from portfolio_validation import P16,readcsv,adapt_state,v6_inputs,rebuild,simulate,validate_book,metrics,extra_metrics
from run_olc25 import feature_table
FEATS=['FUSION','m63','m126','m252','persist3','interaction']
TRIALS=['AUTH','POOL','STRAT']+[f'{v}_NULL{s}' for v in ('POOL','STRAT') for s in range(26001,26006)]


def make_panel(market):
    scores,f,q,cal=feature_table(market)
    C=q['C']; dates=pd.DatetimeIndex(q['dates']);ticks=list(q['tickers']);mp={t:i for i,t in enumerate(ticks)}
    observed=q['observed'] if market=='EU' else np.isfinite(C)&(C>0)
    o=f.copy().rename(columns={'original':'FUSION','date':'signal_date'})
    o['signal_date']=pd.to_datetime(o.signal_date)
    o['m63']=np.nan;o['maturity_date']=pd.NaT;o['future126']=np.nan
    for date,ix in o.groupby('signal_date',sort=True).indices.items():
        inds=np.asarray(ix,int);j=dates.get_indexer([date])[0]
        if j<0:continue
        ids=np.array([mp[t] for t in o.ticker.iloc[inds]])
        if j>=63:
            valid=observed[j,ids]&observed[j-63,ids]&np.isfinite(C[j,ids])&np.isfinite(C[j-63,ids])&(C[j,ids]>0)&(C[j-63,ids]>0)
            v=np.where(valid,np.log(C[j,ids]/C[j-63,ids]),np.nan)
            o.loc[inds,'m63']=pd.Series(v).rank(pct=True,method='average').to_numpy()
        if j+126<len(dates):
            valid=observed[j,ids]&observed[j+126,ids]&np.isfinite(C[j,ids])&np.isfinite(C[j+126,ids])&(C[j,ids]>0)&(C[j+126,ids]>0)
            v=np.where(valid,np.log(C[j+126,ids]/C[j,ids]),np.nan)
            o.loc[inds,'future126']=pd.Series(v).rank(pct=True,method='average').to_numpy()
            o.loc[inds,'maturity_date']=dates[j+126]
    o['interaction']=o.m126*o.persist3
    o['market']=market
    assert len(o)==len(scores)
    return scores,o,q,cal


def candidates_all():
    frames={};scores={};states={};calendars={}
    for market in ['EU','USA']:
        sc,fr,q,cal=make_panel(market)
        frames[market]=fr;scores[market]=sc;states[market]=q;calendars[market]=cal
    return frames,scores,states,calendars


def train_cutoff(frames,year,trial,market=None):
    cutoff=pd.Timestamp(year,1,1)
    if market is None: df=pd.concat([frames['EU'],frames['USA']],ignore_index=True)
    else:df=frames[market].copy()
    good=df['maturity_date'].notna()&(df.maturity_date<cutoff)&df.future126.notna()&np.isfinite(df[FEATS]).all(axis=1)
    fit=df.loc[good].copy()
    months={m:fit[fit.market==m].signal_date.nunique() for m in (('EU','USA') if market is None else (market,))}
    if min(months.values(),default=0)<12:return None,dict(fallback=True,year=year,market=market,nrows=len(fit),months=months)
    # Balanced market monthly query groups. Same market/date weight, even if distinct quote coverage.
    fit['grp_n']=fit.groupby(['market','signal_date']).ticker.transform('size')
    fit['market_months']=fit.groupby('market').signal_date.transform('nunique')
    fit['raw_weight']=1/(fit.grp_n*fit.market_months)
    weights=(fit.raw_weight/fit.raw_weight.mean()).to_numpy()
    target=fit.future126.to_numpy(float).copy()
    if '_NULL' in trial:
        seed=int(trial.split('NULL')[1]); rng=np.random.default_rng(seed+1000*year+(0 if market is None else (1 if market=='EU' else 2)))
        for inds in fit.groupby(['market','signal_date'],sort=True).indices.values():
            ix=np.asarray(inds,int);target[ix]=target[rng.permutation(ix)]
    y=target-fit.FUSION.to_numpy(float)
    X=fit[FEATS].to_numpy(float)
    scaler=StandardScaler().fit(X,sample_weight=weights)
    Z=scaler.transform(X)
    model=Ridge(alpha=50,fit_intercept=True).fit(Z,y,sample_weight=weights)
    d=dict(fallback=False,year=year,market=market,cutoff=str(cutoff.date()),nrows=len(fit),months=months,
       last_maturity=str(fit.maturity_date.max()),mean=scaler.mean_.tolist(),scale=scaler.scale_.tolist(),
       coef=model.coef_.tolist(),intercept=float(model.intercept_),alpha=50,
       weight_by_market={m:float(weights[fit.market.to_numpy()==m].sum()/weights.sum()) for m in fit.market.unique()},
       features=FEATS)
    assert fit.maturity_date.max()<cutoff
    return (scaler,model),d


def scores_one(frames,scores,trial):
    out={m:scores[m].copy() for m in ('EU','USA')};models=[]
    if trial=='AUTH':return out,models
    mode=trial.split('_')[0]
    for year in range(2021,2027):
        for market in (('EU','USA') if mode=='STRAT' else (None,)):
            mdl,meta=train_cutoff(frames,year,trial,market)
            models.append(meta)
            affected=('EU','USA') if market is None else (market,)
            for m in affected:
                if mdl is None:continue
                fr=frames[m];mask=(fr.signal_date.dt.year==year)&np.isfinite(fr[FEATS]).all(axis=1)
                if not mask.any():continue
                scaler,model=mdl
                pred=model.predict(scaler.transform(fr.loc[mask,FEATS].to_numpy(float)))
                pred=np.clip(pred,-.10,+.10)
                out[m].loc[mask.to_numpy(),'FUSION']=out[m].loc[mask.to_numpy(),'FUSION'].to_numpy(float)+.5*pred
    for m in ('EU','USA'):
        assert len(out[m])==len(scores[m]);assert out[m].signal_date.equals(scores[m].signal_date)
        assert out[m].ticker.equals(scores[m].ticker)
        assert np.array_equal(np.isfinite(out[m].FUSION.to_numpy()),np.isfinite(scores[m].FUSION.to_numpy()))
    return out,models


def write_scores():
    frames,base,_,_=candidates_all()
    for m in ('EU','USA'):
        frames[m].to_csv(ROOT/f'results/{m}_FRAME.csv.gz',index=False)
    for trial in TRIALS:
        out,models=scores_one(frames,base,trial)
        folder=ROOT/'results'/trial;folder.mkdir(parents=True,exist_ok=True)
        for m in ('EU','USA'):out[m].to_csv(folder/f'{m}_SCORES.csv.gz',index=False)
        (folder/'ANNUAL_MODELS.json').write_text(json.dumps(models,indent=2,default=str))
        print(json.dumps(dict(trial=trial,models=sum(not a['fallback'] for a in models),fallback=sum(a['fallback'] for a in models))),flush=True)


def replay_one(trial,market):
    start=time.time()
    sc=readcsv(ROOT/f'results/{trial}/{market}_SCORES.csv.gz')
    q=dict(np.load(P16/f'inputs/{market}_STATE_HALF.npz',allow_pickle=False));cal=readcsv(P16/f'inputs/{market}_CALENDAR.csv')
    st,events,dec=adapt_state(q,cal,sc,'FUSION');ctx,allowed=v6_inputs(q,market)
    with warnings.catch_warnings():
        warnings.filterwarnings('ignore',category=RuntimeWarning)
        np.testing.assert_array_equal(rebuild(ctx,allowed=allowed),q['alt'])
        st['alt']=rebuild(ctx,st['d1'],st['d2'],st['weights'],allowed)
    assert not np.any((st['alt']>=0)&((st['alt']==st['d1'])|(st['alt']==st['d2'])))
    folder=ROOT/'results'/trial
    if '_NULL' not in trial:dec.to_csv(folder/f'{market}_DECISIONS.csv',index=False)
    rows=[];checks=[]
    for contract in ('ALARM','FAST_LOCK3'):
        for fee in (.001,.003):
            key=f'{market}_{contract}_{round(fee*10000)}'
            r=simulate(st,events,contract=contract,fee=fee,friction=.001)
            audit=validate_book(st,r)
            if trial=='AUTH':
                parent=np.load(P20/f'results/portfolios/AUTH/{key}.npz')
                for k in r:np.testing.assert_array_equal(r[k],parent[k])
            rows.extend(dict(trial=trial,market=market,contract=contract,fee=fee,key=key,**row) for row in extra_metrics(st,r,metrics(st,r)))
            checks.append(dict(trial=trial,market=market,contract=contract,fee=fee,audit=audit))
            if '_NULL' not in trial:
                pd.DataFrame({'date':st['dates'][1:],'log_return':np.log(r['nav'][:-1]/r['ledger'][:-1,0])}).to_csv(folder/f'{key}_RETURNS.csv.gz',index=False)
                if contract=='FAST_LOCK3' and fee==.001:
                    np.savez_compressed(folder/f'{key}.npz',dates=st['dates'],nav=r['nav'],risk_trace=r['risk_trace'],ledger=r['ledger'])
    pd.DataFrame(rows).to_csv(folder/f'{market}_SCORECARD.csv',index=False)
    (folder/f'{market}_CHECKS.json').write_text(json.dumps(checks,default=str,indent=2))
    return dict(trial=trial,market=market,paths=4,rows=len(rows),seconds=time.time()-start)


def main():
    p=argparse.ArgumentParser();p.add_argument('--stage',choices=['scores','replay'],required=True);p.add_argument('--trials',nargs='*');p.add_argument('--workers',type=int,default=3);a=p.parse_args()
    if a.stage=='scores':write_scores();return
    with ProcessPoolExecutor(max_workers=a.workers) as pool:
        tasks=[pool.submit(replay_one,t,m) for t in (a.trials or TRIALS) for m in ('EU','USA')]
        for f in as_completed(tasks):print(json.dumps(f.result()),flush=True)
if __name__=='__main__':main()
