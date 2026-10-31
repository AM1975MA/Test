"""As-of monthly feature panel and separately matured future segments."""
from common import *
from lifecycle_math import segments,risk_cov
import warnings,time
FEATURES=['r_pct','h_pct','h_level','et','xgb','expert_disagreement','r_change1','r_change3','h_change1','h_change3','mom21','mom63','mom126','mom252','accel','vol63','dd63','ma50_gap','ma200_gap','rel_mom63','market_mom63','breadth','price_age_days']

def own_features(close):
    c=close.dropna();c=c[c>0];r=np.log(c).diff();out=pd.DataFrame(index=c.index)
    for h in [21,63,126,252]:out[f'mom{h}']=np.log(c/c.shift(h))
    out['accel']=out.mom21-out.mom63/3
    out['vol63']=r.rolling(63,min_periods=42).std()*np.sqrt(252)
    out['dd63']=c/c.rolling(63,min_periods=42).max()-1
    out['ma50_gap']=c/c.rolling(50,min_periods=50).mean()-1
    out['ma200_gap']=c/c.rolling(200,min_periods=200).mean()-1
    return out

def prepare_market(market):
    q,C,score,rr,hy,et,xx,cal,pred,raw=sources(market)
    T=list(score.columns);N=len(T);dates=pd.DatetimeIndex(q['dates']);out=ROOT/'inputs';out.mkdir(exist_ok=True)
    forecast_hashes={f'{market}_{p}':digest(F/f'results/calendar/{market}_{p}') for p in ['FORECASTS.csv.gz','CALENDAR.csv']}
    states=[];par=[]
    with warnings.catch_warnings():
        warnings.simplefilter('ignore')
        for half in [False,True]:
            wt='HALF' if half else 'ORIGINAL';st=state_with_score(q,C.copy(),score,et,xx,cal,market,half)
            E,_,_,_,L=simulate(st,np.ones(len(dates)),.001,market)
            ref=np.load(DIAG/f'results/references/{market}_CL01_{wt}.npz',allow_pickle=False)
            err=float(np.max(np.abs(E[0]-ref['nav'])));assert err<1e-12,(market,wt,err)
            np.savez_compressed(out/f'{market}_STATE_{wt}.npz',**st)
            np.savez_compressed(ROOT/f'results/{market}_REFERENCE_{wt}.npz',dates=dates.values,nav=E[0],ledger=L[0])
            par.append(dict(market=market,weight=wt,max_nav_error=err))
    for k,v in raw.items():v.to_pickle(out/f'{market}_{k}.pkl')
    score.to_csv(out/f'{market}_SCORE.csv');cal.to_csv(out/f'{market}_CALENDAR.csv',index=False)
    eidx=raw['Open'].index.get_indexer(cal.entry_date);assert (eidx>=0).all()
    labels=np.stack([segments(raw['Open'].to_numpy(),e) for e in eidx])
    matrix=raw['Close'].ffill(limit=3);rets=matrix.pct_change(fill_method=None)
    mkt=(1+rets.median(axis=1).fillna(0)).cumprod();mk63=np.log(mkt/mkt.shift(63))
    breadth=((matrix/matrix.shift(63)-1)>0).sum(1)/(matrix/matrix.shift(63)-1).notna().sum(1).replace(0,np.nan)
    rows=[];fp_checks=[];hpct=hy.rank(axis=1,pct=True);rd1=rr.diff();rd3=rr.diff(3);hd1=hpct.diff();hd3=hpct.diff(3)
    for j,t in enumerate(T):
        fs=own_features(raw['Close'][t]);cut=fs.index<=pd.Timestamp('2023-12-31')
        chk=own_features(raw['Close'][t].loc[:'2023-12-31'])
        np.testing.assert_allclose(fs.loc[cut],chk,atol=1e-12,equal_nan=True)
        for i,r in enumerate(cal.itertuples(index=False)):
            pos=fs.index.searchsorted(r.signal_date,side='right')-1
            source=fs.index[pos] if pos>=0 else pd.NaT
            age=(r.signal_date-source).days if pos>=0 else 999
            good=pos>=0 and age<=5 and np.isfinite(score.iloc[i,j])
            if not good:continue
            f=fs.iloc[pos].to_dict()
            row=dict(market=market,signal_date=r.signal_date,entry_date=r.entry_date,ticker=t,ticker_idx=j,source_date=source,r_pct=rr.iloc[i,j],h_pct=hpct.iloc[i,j],h_level=hy.iloc[i,j],et=et.iloc[i,j],xgb=xx.iloc[i,j],expert_disagreement=abs(rr.iloc[i,j]-hpct.iloc[i,j]),r_change1=rd1.iloc[i,j],r_change3=rd3.iloc[i,j],h_change1=hd1.iloc[i,j],h_change3=hd3.iloc[i,j],price_age_days=age,**f)
            row['market_mom63']=mk63.loc[r.signal_date];row['rel_mom63']=row['mom63']-row['market_mom63'];row['breadth']=breadth.loc[r.signal_date]
            for h,days in enumerate([21,42,63],1):
                row[f'y{h}']=labels[i,h-1,j]
                row[f'exit{h}']=raw['Open'].index[eidx[i]+days] if eidx[i]+days<len(raw['Open']) else pd.NaT
            rows.append(row)
    panel=pd.DataFrame(rows).sort_values(['signal_date','ticker']).reset_index(drop=True)
    panel[FEATURES]=panel[FEATURES].replace([np.inf,-np.inf],np.nan)
    panel.to_pickle(out/f'{market}_PANEL.pkl');panel.to_csv(out/f'{market}_PANEL.csv.gz',index=False,compression='gzip')
    cov=[]
    for sd in cal.signal_date:
        hist=np.log(raw['Close'].ffill(limit=3)).diff().loc[:sd].tail(126).to_numpy()
        cov.append(risk_cov(hist))
    np.savez_compressed(out/f'{market}_COVARIANCE.npz',dates=cal.signal_date.to_numpy(),covariance=np.stack(cov))
    meta={'market':market,'rows':len(panel),'months':panel.signal_date.nunique(),'features':FEATURES,'last_signal':str(panel.signal_date.max()),'training_targets':[int(panel[f'y{i}'].notna().sum()) for i in [1,2,3]],'source_dates_checked':len(panel),'own_price_prefix_checks':N,'forecast_hashes':forecast_hashes,'baseline_parity':par,'cold_start':'2019-2020 original CL01; all model outcomes reported from2021 separately'}
    (out/f'{market}_INPUT_AUDIT.json').write_text(json.dumps(meta,indent=2))
    print(json.dumps(meta,indent=2),flush=True)

if __name__=='__main__':
    for m in ['EU','USA']:prepare_market(m)
