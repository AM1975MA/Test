"""Matched isolated substitutions; the old and RSI-corrected controls remain intact."""
from bootstrap import *
import numpy as np,pandas as pd,sys,argparse,time,json
sys.path[:0]=[str(PARENT/'parents/olc07_calendar_20261101/src'),str(PARENT/'parents/olc06_timing_20261101/src')]
from phase_state import combine_forecasts,make_state
from common import load,metrics,policy_args
from vector_engine import simulate
OUT=ROOT/'results';PATHS=OUT/'paths';PATHS.mkdir(exist_ok=True)

def forecast_path(market,variant):
    if variant=='LEGACY':return PARENT/'results'/f'{market}_BASE_FORECASTS.csv.gz'
    if variant=='REF_RSI':return PARENT/'results'/f'{market}_R_RSI_DOMAIN_FORECASTS.csv.gz'
    return OUT/f'{market}_{variant}_FORECASTS.csv.gz'

def run(variants):
    rows=[];checks=[];decisions=[];start=time.time()
    for market in ['EU','USA']:
        q,old_events,oldcal=load(market,'HALF');T=list(q['tickers']);names=[x for x in T if not str(x).startswith('EUR_CASH')]
        cal=pd.read_csv(CAL/f'{market}_CALENDAR.csv',parse_dates=['signal_date','entry_date','exit_date'])
        cal=cal[cal.signal_date.between('2019-01-01','2026-06-30')].reset_index(drop=True)
        support=None
        for variant in variants:
            p=pd.read_csv(forecast_path(market,variant),parse_dates=['signal_date'],float_precision='round_trip')
            assert not p.duplicated(['signal_date','ticker']).any()
            def matrix(c):return p.pivot(index='signal_date',columns='ticker',values=c).reindex(index=cal.signal_date,columns=names).to_numpy(float)
            score=pd.DataFrame(combine_forecasts(matrix('RETURN'),matrix('ET'),matrix('XGB')),index=cal.signal_date,columns=names)
            if support is None:support=np.isfinite(score)
            else:assert np.array_equal(support,np.isfinite(score)),(market,variant,'support')
            st,events=make_state(q,cal,score)
            if variant=='LEGACY':
                for k in ['d1','d2','weights','basew','margin']:assert np.array_equal(st[k],q[k]),(market,k)
                assert np.array_equal(events,old_events)
            score.to_csv(OUT/f'{market}_{variant}_COMBINED.csv')
            for j,r in enumerate(cal.itertuples(index=False)):
                a=pd.DatetimeIndex(st['dates']).searchsorted(r.entry_date)
                if a>=len(st['dates']):continue
                decisions.append({'market':market,'variant':variant,'signal_date':r.signal_date,'entry_date':r.entry_date,'first':T[st['d1'][0,a]],'second':T[st['d2'][0,a]],'eligible':int(np.isfinite(score.iloc[j]).sum())})
            for fee in [.001,.003]:
                for policy in ['IMMEDIATE','DELAY3','PHASE5']:
                    key=f'{market}_{variant}_{policy}_C{round(fee*10000)}'
                    path=PATHS/f'{key}.npz';keyinputs={'code':sha256(Path(__file__)),'forecast':sha256(forecast_path(market,variant)),'market':market,'policy':policy,'fee':fee}
                    # Complete manifests bind every saved path to immutable inputs.
                    marker=PATHS/f'{key}.json'
                    cached=marker.exists() and path.exists() and json.loads(marker.read_text()).get('inputs')==keyinputs
                    if cached:
                        meta=json.loads(marker.read_text());assert sha256(path)==meta['sha256'];z=np.load(path,allow_pickle=False);r={k:z[k] for k in z.files if k!='dates'}
                    else:
                        r=simulate(st,events,fee=fee,**policy_args(policy));np.savez_compressed(path,dates=st['dates'],**r)
                        atomic_json(marker,{'inputs':keyinputs,'sha256':sha256(path)})
                    olderr=None
                    if variant in ['LEGACY','REF_RSI']:
                        tag='BASE' if variant=='LEGACY' else 'R_RSI_DOMAIN'
                        old=np.load(PARENT/'results/paths'/f'{market}_{tag}_{policy}_C{round(fee*10000)}.npz',allow_pickle=False)
                        olderr=max(float(np.max(abs(old[k]-r[k]))) for k in ['nav','primary_units','defensive_units','targets','ledger','free_cash'])
                        assert olderr==0,(key,olderr)
                    v=((r['primary_units'][:-1]+r['defensive_units'][:-1])*st['O'][1:]).sum(1)+r['free_cash'][:-1]
                    err=float(np.max(abs(v-r['nav'][:-1])));assert err<1e-10,(key,err)
                    logs=np.log(v/np.r_[1.,v[:-1]]);actual=pd.DatetimeIndex(st['dates'])[1:];errors=[]
                    for mr in metrics(st,r):
                        mask=(actual>=pd.Timestamp(mr['first_valuation']))&(actual<=pd.Timestamp(mr['last_valuation']))
                        sub=logs[mask];equity=np.exp(sub.cumsum());peak=np.maximum.accumulate(np.r_[1.,equity])[1:]
                        independent={'cagr':float(np.expm1(sub.sum()*252/len(sub))),'maxdd':float((equity/peak-1).min()),'period_return':float(np.expm1(sub.sum()))}
                        errors.extend(abs(independent[k]-mr[k]) for k in independent)
                        rows.append(dict(market=market,variant=variant,fee=fee,policy=policy,config=key,**mr))
                    assert max(errors)<1e-10
                    checks.append({'config':key,'nav_intervals':len(v),'position_error':err,'metric_error':max(errors),'baseline_error':olderr})
            pd.DataFrame(rows).to_csv(OUT/'SCORECARD.csv',index=False);pd.DataFrame(checks).to_csv(OUT/'REPLAY_CHECKS.csv',index=False)
            pd.DataFrame(decisions).to_csv(OUT/'DECISIONS.csv',index=False)
            print('REPLAY',market,variant,'paths',len(checks),'elapsed',round(time.time()-start,1),flush=True)
    atomic_json(OUT/'REPLAY_SUMMARY.json',{'paths':len(checks),'checked_metric_values':len(rows)*3,'checked_intervals':sum(x['nav_intervals'] for x in checks),'exact_baseline_paths':sum(x['baseline_error']==0 for x in checks),'max_nav_error':max(x['position_error'] for x in checks),'max_metric_error':max(x['metric_error'] for x in checks),'scope':'Frozen original risk and V6, legacy fees/fills, identical support; no live certification.'})
if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('--variants',default='LEGACY,REF_RSI');a=ap.parse_args();run(a.variants.split(','))
