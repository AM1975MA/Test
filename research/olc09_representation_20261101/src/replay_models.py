"""Self-financing matched replay with immutable Return/risk/fee contracts."""
from bridge import *
from train_models import CONFIGS
import replay_pack as rp
import pandas as pd,numpy as np,json,time,argparse,hashlib
OUT=ROOT/'results';PATHS=OUT/'paths';PATHS.mkdir(exist_ok=True)
ARCHIVE={'REF_RSI':'REF_RSI','FRACTION_CORE':'H_UNIQUE','FRACTION_PATH':'H_PATH',**{f'FRACTION_NULL{s}':f'H_NULL{s}' for s in [7101,7102,7103]}}

def source(market,variant):
    if variant=='REF_RSI':return parent_bootstrap.PARENT/'results'/f'{market}_R_RSI_DOMAIN_FORECASTS.csv.gz'
    if variant in ARCHIVE:return PARENT/'results'/f'{market}_{ARCHIVE[variant]}_FORECASTS.csv.gz'
    return OUT/f'{market}_{variant}_FORECASTS.csv.gz'

def ensembles():
    for name,refs in [('ENSEMBLE_REF42',['REF_RSI','REF42_S211','REF42_S307']),('ENSEMBLE_FIXED_CORE',['FIXED_CORE_S101','FIXED_CORE_S211','FIXED_CORE_S307']),('ENSEMBLE_FIXED_PATH',['FIXED_PATH_S101','FIXED_PATH_S211','FIXED_PATH_S307'])]:
        for market in ['EU','USA']:
            parts=[pd.read_csv(source(market,r),parse_dates=['signal_date','source_date'],float_precision='round_trip').sort_values(['signal_date','ticker']).reset_index(drop=True) for r in refs]
            p=parts[0].copy()
            for other in parts[1:]:
                assert p[['signal_date','ticker']].equals(other[['signal_date','ticker']])
                for k in ['RETURN_RAW','RETURN']:np.testing.assert_allclose(p[k],other[k],rtol=0,atol=0,equal_nan=True)
                for k in ['ET_RAW','XGB_RAW']:assert np.array_equal(p[k].isna(),other[k].isna())
            for k in ['ET','XGB']:
                p[k+'_RAW']=np.mean([q[k+'_RAW'].to_numpy() for q in parts],axis=0)
                p[k]=p.groupby('signal_date')[k+'_RAW'].rank(pct=True)
            p=canonical_forecasts(p);p.to_csv(source(market,name),index=False,compression='gzip')
    atomic_json(OUT/'ENSEMBLE_CONTRACT.json',{'seed_members':[101,211,307],'method':'arithmetic mean raw predictions per learner, then same-date ranks; no selected seed','new_model_fits':0})

def run(variants):
    rows=[];checks=[];decisions=[];start=time.time()
    for market in ['EU','USA']:
        q,old_events,oldcal=rp.load(market,'HALF');T=list(q['tickers']);names=[x for x in T if not str(x).startswith('EUR_CASH')]
        cal=pd.read_csv(rp.CAL/f'{market}_CALENDAR.csv',parse_dates=['signal_date','entry_date','exit_date'])
        cal=cal[cal.signal_date.between('2019-01-01','2026-06-30')].reset_index(drop=True)
        support=None
        for variant in variants:
            path=source(market,variant);p=pd.read_csv(path,parse_dates=['signal_date'],float_precision='round_trip')
            assert not p.duplicated(['signal_date','ticker']).any()
            def matrix(c):return p.pivot(index='signal_date',columns='ticker',values=c).reindex(index=cal.signal_date,columns=names).to_numpy(float)
            score=pd.DataFrame(rp.combine_forecasts(matrix('RETURN'),matrix('ET'),matrix('XGB')),index=cal.signal_date,columns=names)
            if support is None:support=np.isfinite(score)
            else:assert np.array_equal(support,np.isfinite(score)),(market,variant,'support')
            st,events=rp.make_state(q,cal,score)
            score.to_csv(OUT/f'{market}_{variant}_COMBINED.csv')
            for j,r in enumerate(cal.itertuples(index=False)):
                a=pd.DatetimeIndex(st['dates']).searchsorted(r.entry_date)
                if a>=len(st['dates']):continue
                decisions.append({'market':market,'variant':variant,'signal_date':r.signal_date,'entry_date':r.entry_date,'first':T[st['d1'][0,a]],'second':T[st['d2'][0,a]],'eligible':int(np.isfinite(score.iloc[j]).sum())})
            for fee in [.001,.003]:
                for policy in ['IMMEDIATE','DELAY3','PHASE5']:
                    key=f'{market}_{variant}_{policy}_C{round(fee*10000)}';dest=PATHS/f'{key}.npz';marker=PATHS/f'{key}.json'
                    inputs={'forecast_sha256':sha256(path),'source_sha256':sha256(Path(__file__)),'market':market,'policy':policy,'fee':fee}
                    if marker.exists() and dest.exists() and json.loads(marker.read_text())['inputs']==inputs:
                        assert sha256(dest)==json.loads(marker.read_text())['sha256'];zz=np.load(dest,allow_pickle=False);r={k:zz[k] for k in zz.files if k!='dates'}
                    else:
                        r=rp.simulate(st,events,fee=fee,**rp.policy_args(policy));np.savez_compressed(dest,dates=st['dates'],**r);atomic_json(marker,{'inputs':inputs,'sha256':sha256(dest)})
                    olderr=None
                    if variant in ARCHIVE:
                        oldpath=PARENT/'results/paths'/f'{market}_{ARCHIVE[variant]}_{policy}_C{round(fee*10000)}.npz'
                        if oldpath.exists():
                            old=np.load(oldpath,allow_pickle=False)
                            olderr=max(float(np.max(abs(old[k]-r[k]))) for k in ['nav','primary_units','defensive_units','targets','ledger','free_cash'])
                            assert olderr==0,(key,olderr)
                    val=((r['primary_units'][:-1]+r['defensive_units'][:-1])*st['O'][1:]).sum(1)+r['free_cash'][:-1]
                    err=float(np.max(abs(val-r['nav'][:-1])));assert err<1e-10
                    logs=np.log(val/np.r_[1.,val[:-1]]);actual=pd.DatetimeIndex(st['dates'])[1:];errors=[]
                    for mr in rp.metrics(st,r):
                        mask=(actual>=pd.Timestamp(mr['first_valuation']))&(actual<=pd.Timestamp(mr['last_valuation']))
                        sub=logs[mask];e=np.exp(sub.cumsum());pk=np.maximum.accumulate(np.r_[1.,e])[1:]
                        independent={'cagr':float(np.expm1(sub.sum()*252/len(sub))),'maxdd':float((e/pk-1).min()),'period_return':float(np.expm1(sub.sum()))}
                        errors.extend(abs(independent[k]-mr[k]) for k in independent)
                        rows.append(dict(market=market,variant=variant,fee=fee,policy=policy,config=key,**mr))
                    assert max(errors)<1e-10
                    checks.append({'config':key,'nav_intervals':len(val),'position_error':err,'metric_error':max(errors),'baseline_error':olderr})
            pd.DataFrame(rows).to_csv(OUT/'SCORECARD.csv',index=False);pd.DataFrame(checks).to_csv(OUT/'REPLAY_CHECKS.csv',index=False);pd.DataFrame(decisions).to_csv(OUT/'DECISIONS.csv',index=False)
            print('REPLAY',market,variant,'paths',len(checks),'elapsed',round(time.time()-start,1),flush=True)
    atomic_json(OUT/'REPLAY_SUMMARY.json',{'paths':len(checks),'checked_metric_values':len(rows)*3,'checked_intervals':sum(x['nav_intervals'] for x in checks),'exact_archived_paths':sum(x['baseline_error']==0 for x in checks),'max_nav_error':max(x['position_error'] for x in checks),'max_metric_error':max(x['metric_error'] for x in checks),'scope':'Matched frozen prices/risk/V6 and original fees. No live or market-data certification.'})
if __name__=='__main__':
    ensembles();run(list(ARCHIVE)+list(CONFIGS)+['ENSEMBLE_REF42','ENSEMBLE_FIXED_CORE','ENSEMBLE_FIXED_PATH'])
