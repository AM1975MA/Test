"""Risk-layer attribution, all paired outcomes and chronological reentry diagnostics."""
import json
from pathlib import Path
import numpy as np
import pandas as pd
from run_experiment import ROOT,PARENT
R=ROOT/'results';C='TOP2_CONTEXT_REVALUE';S='TOP2_STATIC_REVALUE'

def csv(path):
    try:return pd.read_csv(path)
    except pd.errors.EmptyDataError:return pd.DataFrame()

def main():
    f=pd.concat([pd.read_csv(p) for p in R.glob('SCORECARD_*.csv')],ignore_index=True)
    assert not f.duplicated(['key','period']).any()
    f.to_csv(R/'SCORECARD.csv',index=False);pairs=[];exposure=[];evrows=[];reentry=[];unc=[]
    for (m,mode,fee,stress,period),g in f.groupby(['market','contract','fee','stress','period']):
        d=g.set_index('variant')
        for b in (S,'CUM_FIT','ORIGINAL'):
            pairs.append(dict(market=m,contract=mode,fee=fee,stress=stress,period=period,baseline=b,
                candidate_cagr=d.at[C,'cagr'],baseline_cagr=d.at[b,'cagr'],delta_cagr=d.at[C,'cagr']-d.at[b,'cagr'],
                candidate_maxdd=d.at[C,'maxdd'],baseline_maxdd=d.at[b,'maxdd'],delta_maxdd=d.at[C,'maxdd']-d.at[b,'maxdd']))
    pd.DataFrame(pairs).to_csv(R/'PAIRED_COMPARISONS.csv',index=False)
    rng=np.random.default_rng(20261102);ix=((rng.integers(0,48,(4000,8))[:,:,None]+np.arange(6))%48).reshape(4000,48)
    def path_row(m,v,mode):return f[(f.market==m)&(f.variant==v)&(f.contract==mode)&(f.fee==.001)&~f.stress].iloc[0]
    def monthly(key):
        q=np.load(R/f'paths/{key}.npz');ds=pd.to_datetime(q['dates'][1:]);lr=np.log(q['nav'][:-1]/q['ledger'][:-1,0])
        return pd.Series(lr,index=ds).groupby(ds.to_period('M')).sum().reindex(pd.period_range('2021-01','2024-12',freq='M')).to_numpy()
    for m in ('EU','USA'):
        for mode,base_v,base_mode in [('FAST_LOCK3',C,'FAST_NOLOCK'),('FAST_LOCK3',C,'ALARM'),('FAST_LOCK3',S,'FAST_LOCK3'),('FAST_LOCK3','CUM_FIT','FAST_LOCK3')]:
            a=path_row(m,C,mode);b=path_row(m,base_v,base_mode)
            d=monthly(a['key'])-monthly(b['key']);boot=d[ix].mean(1)*12;lo,hi=np.quantile(boot,[.025,.975])
            unc.append(dict(market=m,candidate=mode,baseline=base_v+' / '+base_mode,annual_log_difference=float(d.mean()*12),lower=float(lo),upper=float(hi),positive_months=int((d>1e-12).sum()),negative_months=int((d<-1e-12).sum())))
        state=dict(np.load(PARENT/f'inputs/{m}_{C}.npz'));ticks=list(state['tickers'])
        for mode in ('BASE','ALARM','FAST_NOLOCK','FAST_LOCK3'):
            a=path_row(m,C,mode);p=np.load(R/f"paths/{a['key']}.npz");dates=pd.to_datetime(p['dates'][1:])
            for period,left,right in [('FULL','2019-01-01','2026-07-01'),('ACTIVE2021_2024','2021-01-01','2024-12-31'),('CRASH2020','2020-02-01','2020-03-31')]:
                mask=(dates>=left)&(dates<=right)
                exposure.append(dict(market=m,contract=mode,period=period,mean_risky_before_stop=float(p['ledger'][:-1,12][mask].mean()),
                  mean_risky_after_stop=float(p['ledger'][:-1,13][mask].mean()),locked_weight_sum=float(p['risk_trace'][:-1,2][mask].sum())))
            stops=csv(R/f"events/{a['key']}_stops.csv.gz");orders=csv(R/f"events/{a['key']}_orders.csv.gz")
            if stops.empty:continue
            for event in stops.to_dict('records'):
                k=int(event['signal_index']);t=ticks.index(event['ticker']);entry=orders[(orders.kind=='REENTRY')&(orders.ticker==event['ticker'])&(orders['index']>k)]
                nextk=int(entry['index'].min()) if len(entry) else None
                end=min(int(event['earliest_reentry']),len(state['O'])-1);start=min(k+1,len(state['O'])-1)
                move=float(state['O'][end,t]/state['O'][start,t]-1) if end>start else 0.
                event.update(market=m,contract=mode,next_actual_reentry_index=nextk,
                    sessions_until_actual_reentry=(nextk-k if nextk is not None else np.nan),
                    ticker_return_next_open_to_lock_expiry=move,close_recovered=bool(state['C'][k,t]>event['barrier']))
                evrows.append(event)
            main=stops[stops.date.between('2021-01-01','2024-12-31')]
            reentry.append(dict(market=m,contract=mode,full_stops=len(stops),main_stops=len(main),
                main_same_day_increase=int((main.newly_bought_quantity>1e-14).sum()),
                main_open_gap=int(main.opening_breach.sum()),full_open_gap=int(stops.opening_breach.sum())))
    pd.DataFrame(evrows).to_csv(R/'STOP_REENTRY_DIAGNOSTICS.csv',index=False)
    pd.DataFrame(reentry).to_csv(R/'STOP_SUMMARY.csv',index=False)
    pd.DataFrame(exposure).to_csv(R/'EXPOSURE_SUMMARY.csv',index=False)
    pd.DataFrame(unc).to_csv(R/'UNCERTAINTY.csv',index=False)
    print('UNCERTAINTY');print(pd.DataFrame(unc).round(6).to_string(index=False))
    print('STOPS');print(pd.DataFrame(reentry).to_string(index=False))
    print('EXPOSURE');print(pd.DataFrame(exposure).round(5).to_string(index=False))
    z=pd.DataFrame(evrows);z=z[z.contract.eq('FAST_LOCK3')]
    print('LOCKED PRICE MOVEMENT, NOT PORTFOLIO ATTRIBUTION')
    print(z.groupby('market').ticker_return_next_open_to_lock_expiry.agg(['count','mean','median','min','max']))

if __name__=='__main__':main()
