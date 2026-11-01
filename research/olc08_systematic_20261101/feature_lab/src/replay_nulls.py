"""Twelve auxiliary IMMEDIATE null-information paths; main scorecard untouched."""
from bootstrap import *
from evidence_math import daily_log,score_month
from replay_pack import load,make_state,combine_forecasts,metrics,policy_args,simulate
import pandas as pd,numpy as np,json
OUT=ROOT/'results';PATHS=OUT/'null_paths';PATHS.mkdir(exist_ok=True)

def run():
    rows=[];checks=[];predrows=[]
    for market in ['EU','USA']:
        q,_,_=load(market,'HALF');names=[t for t in q['tickers'] if not str(t).startswith('EUR_CASH')]
        cal=pd.read_csv(CAL/f'{market}_CALENDAR.csv',parse_dates=['signal_date','entry_date','exit_date'])
        cal=cal[cal.signal_date.between('2019-01-01','2026-06-30')].reset_index(drop=True)
        reference=pd.read_csv(OUT/f'{market}_H_PATH_COMBINED.csv',index_col=0,parse_dates=True,float_precision='round_trip')
        labels=pd.read_pickle(CAL/f'{market}_COMPACT.pkl')[['signal_date','ticker','exit_date_21','fwd_ret_21']]
        for seed in [7101,7102,7103]:
            variant=f'H_NULL{seed}'
            p=pd.read_csv(OUT/f'{market}_{variant}_FORECASTS.csv.gz',parse_dates=['signal_date'],float_precision='round_trip')
            def mat(c):return p.pivot(index='signal_date',columns='ticker',values=c).reindex(index=cal.signal_date,columns=names).to_numpy(float)
            score=pd.DataFrame(combine_forecasts(mat('RETURN'),mat('ET'),mat('XGB')),index=cal.signal_date,columns=names)
            assert np.array_equal(np.isfinite(score),np.isfinite(reference))
            st,events=make_state(q,cal,score)
            score.index.name='signal_date';score.columns.name='ticker'
            pr=score.stack(future_stack=True).rename('score').reset_index().merge(labels,on=['signal_date','ticker'],validate='one_to_one')
            pr=pr[(pr.signal_date>='2021-01-01')&(pr.exit_date_21<'2025-01-01')]
            for d,g in pr.groupby('signal_date'):predrows.append({'market':market,'variant':variant,'signal_date':d,**score_month(g,'score','fwd_ret_21')})
            for fee in [.001,.003]:
                r=simulate(st,events,fee=fee,**policy_args('IMMEDIATE'))
                key=f'{market}_{variant}_IMMEDIATE_C{round(fee*10000)}'
                np.savez_compressed(PATHS/f'{key}.npz',dates=st['dates'],**r)
                val=((r['primary_units'][:-1]+r['defensive_units'][:-1])*st['O'][1:]).sum(1)+r['free_cash'][:-1]
                error=float(np.max(abs(val-r['nav'][:-1])));assert error<1e-10
                lr=np.log(val/np.r_[1.,val[:-1]]);dates=pd.DatetimeIndex(st['dates'])[1:];errors=[]
                for m in metrics(st,r):
                    mask=(dates>=m['first_valuation'])&(dates<=m['last_valuation']);z=lr[mask];nav=np.exp(z.cumsum());dd=nav/np.maximum.accumulate(np.r_[1.,nav])[1:]-1
                    errors += [abs(float(np.expm1(z.mean()*252))-m['cagr']),abs(float(dd.min())-m['maxdd']),abs(float(np.expm1(z.sum()))-m['period_return'])]
                    rows.append(dict(market=market,variant=variant,fee=fee,policy='IMMEDIATE',config=key,**m))
                assert max(errors)<1e-10
                checks.append(dict(config=key,intervals=len(val),nav_error=error,metric_error=max(errors)))
                print('NULL_REPLAY',key,flush=True)
    a=pd.DataFrame(rows);a.to_csv(OUT/'NULL_SCORECARD.csv',index=False)
    p=pd.DataFrame(predrows);p.to_csv(OUT/'NULL_PREDICTIVE_MONTHS.csv',index=False)
    p.groupby(['market','variant']).agg(months=('signal_date','nunique'),rank_ic=('rank_ic','mean'),top2_excess=('top2_excess','mean')).reset_index().to_csv(OUT/'NULL_PREDICTIVE_SUMMARY.csv',index=False)
    atomic_json(OUT/'NULL_REPLAY_VERIFICATION.json',{'paths':len(checks),'intervals':sum(x['intervals'] for x in checks),'metric_values':len(rows)*3,'max_nav_error':max(x['nav_error'] for x in checks),'max_metric_error':max(x['metric_error'] for x in checks),'scope':'Three null permutations selected before auxiliary outcomes, after favorable main H_PATH observation; not independent confirmation or calibrated p-value.'})
    print(a.query("period=='ACTIVE2021_2024' and fee==.001").pivot(index='variant',columns='market',values=['cagr','maxdd']).to_string(),flush=True)
if __name__=='__main__':run()
