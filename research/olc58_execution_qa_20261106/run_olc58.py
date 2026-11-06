#!/usr/bin/env python3
"""OLC58: execution-readiness, event-aligned attribution, asymmetric-friction stress.

Inputs are the *frozen* original OLC19 checkpoint ZIP and OLC56 test ZIP.
No retraining, return-based rule search, data fetching or production modifications.

Usage:
    python run_olc58.py --olc19 OLC19_Rischio_Rientro_Checkpoint_20261102.zip \
      --olc56 OLC56_TESTS_20261106_VERIFICATI.zip --out results

Dependencies: Python >= 3.10, numpy, pandas.
"""
from __future__ import annotations
import argparse
import hashlib
import io
import json
import sys
import tempfile
import zipfile
from pathlib import Path
from functools import lru_cache
import numpy as np
import pandas as pd

OLC19_HASH = '3b5799dae060c104408f581c70280cef8ce4d84c3978434d4e6ba81108f16540'
OLC56_HASH = 'f22b92a5c4b5024d6f8afef6504b794e1f46ff53ffa87adfaa8f3a2e0e3e2573'
E19 = 'olc19_combined_risk_20261102'
E56 = 'OLC56_ROBUST_20261106/results/'
BASE_FEE = .001
BASE_FRICTION = .001


def digest(path):
    h=hashlib.sha256()
    with Path(path).open('rb') as f:
        for b in iter(lambda:f.read(2**20),b''):h.update(b)
    return h.hexdigest()


def toframe(records):return pd.DataFrame.from_records(records)


def main(opts):
    out=Path(opts.out).resolve();out.mkdir(parents=True,exist_ok=True)
    checks = {'olc19_sha256':digest(opts.olc19),'olc56_sha256':digest(opts.olc56)}
    assert checks['olc19_sha256']==OLC19_HASH,'OLC19 input ZIP changed.'
    assert checks['olc56_sha256']==OLC56_HASH,'OLC56 input ZIP changed.'
    with tempfile.TemporaryDirectory(prefix='olc58-source-') as td, zipfile.ZipFile(opts.olc19) as z19, zipfile.ZipFile(opts.olc56) as z56:
        # Original source is explicitly frozen; copy it in temporary workspace only.
        z19.extractall(td)
        root=Path(td)/E19
        sys.path.insert(0,str(root/'src'))
        sys.path.insert(0,str(root/'restore/olc18_execution_20261102/parent_archive/parent/olc16_contextual_rank_20261102/src'))
        from combined_engine import _impl  # noqa: E402
        from portfolio_metrics_parent import metrics  # noqa: E402
        rows_phase=[]; rows_cost=[]; rows_boot=[]; rows_loo=[]; rows_events=[]
        rows_liq=[]; rows_orders=[]; rows_stops=[]; rows_month=[]
        decision={}
        for market in ['EU','USA']:
            p=root/f'restore/olc18_execution_20261102/inputs/{market}_TOP2_CONTEXT_REVALUE.npz'
            q=dict(np.load(p,allow_pickle=False)); e=q.pop('events')
            dates=pd.DatetimeIndex(q['dates'])
            assert len(e)==len(dates) and e[0] and e[-1]
            event_ix=np.flatnonzero(e)
            event_age=np.arange(len(dates)) - np.maximum.accumulate(np.where(e,np.arange(len(dates)),-1))
            ticker_index={name:i for i,name in enumerate(q['tickers'])}
            @lru_cache(maxsize=None)
            def execute(policy, fee, stop_friction):
                return _impl(q,e,policy='DELAY' if policy=='DELAY3' else 'IMMEDIATE',
                             fraction=3 if policy=='DELAY3' else 1,
                             fee=fee,exposure_timing='PREVIOUS',stop_timing='NOW',
                             stop_friction=stop_friction,ordinary_alarm=False,
                             fast_stop=True,lock_days=3)
            outputs={}
            for pol in ('IMMEDIATE','DELAY3'):
                outputs[pol]=execute(pol,BASE_FEE,BASE_FRICTION)
                local=outputs[pol]
                arr=toframe(metrics(q,local)); arr.set_index('period',inplace=True)
                decision[(market,pol)]=arr
                ratios=local['nav'][:-1]/local['ledger'][:-1,0]
                expected=pd.read_csv(io.BytesIO(z56.read(E56+f'{market}_TIMING_DAILY.csv')))
                expected=expected[expected['policy']==pol].reset_index(drop=True)
                assert np.array_equal(pd.DatetimeIndex(expected.day).values,dates[1:].values)
                assert len(expected)==len(ratios)
                maxerr=np.max(np.abs(np.log(ratios)-expected.logR.to_numpy()))
                assert maxerr<=2e-14,(market,pol,maxerr)
                checks[market+'_'+pol+'_daily_maxerr']=float(maxerr)
                if pol=='IMMEDIATE':
                    ref=dict(np.load(root/f'results/paths/{market}_TOP2_CONTEXT_REVALUE_FAST_LOCK3_F10_S10.npz'))
                    for key in ['nav','ledger','primary_units','defensive_units','free_cash','targets','risk_trace']:
                        assert np.array_equal(local[key],ref[key]),('OLC19 bitwise parity',market,key)
                    checks[market+'_olc19_7array_bitwise']=True
            imm=outputs['IMMEDIATE']; lag=outputs['DELAY3'];
            delta=np.log(lag['nav'][:-1]/lag['ledger'][:-1,0])-np.log(imm['nav'][:-1]/imm['ledger'][:-1,0])
            actual_days=dates[1:]
            df=pd.DataFrame({'date':actual_days,'delta':delta,'event_age':event_age[:-1]})
            df['cal_month']=df.date.dt.to_period('M')
            df['calendar_session_index']=df.groupby('cal_month').cumcount()
            df['entry_aligned_phase']=np.where(df.event_age<2,'FIRST2_EVENT','AFTER_EVENT2')
            df['period']=np.select([df.date.dt.year.between(2021,2024),df.date.dt.year>=2025],['MAIN','LATE'],'EARLY')
            # Legacy OLC57 calendar two-day split is NOT aligned to signal-entry dates.
            for window,sub in df.groupby('period',sort=False):
                for label,pred in [('FIRST2_EVENT',sub.event_age<2),('AFTER_EVENT2',sub.event_age>=2),
                                   ('FIRST2_CALENDAR',sub.calendar_session_index<2),('AFTER_CALENDAR2',sub.calendar_session_index>=2)]:
                    rows_phase.append(dict(market=market,window=window,phase=label,
                       sessions=int(pred.sum()),paired_logbp=float(sub.loc[pred,'delta'].sum()*1e4)))
            # Each month must reconcile with the original *frozen* OLC56 report.
            archive=pd.read_csv(io.BytesIO(z56.read(E56+f'{market}_TIMING_MONTHLY_DELTA.csv')))
            computed=(df.groupby('cal_month').delta.sum()*1e4);computed.index=computed.index.astype(str)
            compared=archive.merge(computed.rename('recomputed_logbp'),left_on='month',right_index=True,validate='one_to_one')
            assert len(compared)==90
            monerr=float((compared.delay_minus_immediate_log_bp-compared.recomputed_logbp).abs().max())
            assert monerr<1e-7
            checks[market+'_monthly_max_error_logbp']=monerr
            compared['market']=market;rows_month.extend(compared.to_dict('records'))
            # Leave-one-year-out diagnostic on original 48 MAIN months, without refitting.
            x=df[df.period=='MAIN'];assert x.cal_month.nunique()==48
            for y in [2021,2022,2023,2024]:
                tmp=x[x.date.dt.year!=y]
                nmonth=tmp.cal_month.nunique();assert nmonth==36
                rows_loo.append(dict(market=market,year_excluded=y,months=nmonth,
                   annualized_paired_log_pp=float(tmp.delta.sum()*100*12/nmonth)))
            # Month entry schedule: export venue-quote request for 1st/2nd/3rd session.
            for n,k in enumerate(event_ix):
                prev=event_ix[n-1] if n>0 else k
                entries={str(q['tickers'][int(j)]) for j in [q['d1'][0,k],q['d2'][0,k],q['d1'][0,prev],q['d2'][0,prev]] if int(j)>=0}
                changed=bool(n and (q['d1'][0,k]!=q['d1'][0,prev] or q['d2'][0,k]!=q['d2'][0,prev] or abs(q['weights'][0,k]-q['weights'][0,prev])>1e-12))
                for offset in [0,1,2]:
                    if k+offset>=len(dates):continue
                    for name in sorted(entries):
                        t=ticker_index[name]
                        rows_liq.append(dict(market=market,event_n=n,entry_date=str(dates[k].date()),
                            target_session=offset+1,quote_date=str(dates[k+offset].date()),ticker=name,
                            status='NEW_OR_PREVIOUS',pair_changed=changed,
                            original_O=float(q['O'][k+offset,t]),
                            has_original_observed_mask='observed' in q,
                            original_observed=bool(q['observed'][k+offset,t]) if 'observed' in q else '',
                            required='timestamped auction/open trade, bid, ask, size, venue, ISIN'))
                rows_events.append(dict(market=market,event_n=n,date=str(dates[k].date()),changed_pair=changed,
                   new1=str(q['tickers'][int(q['d1'][0,k])]),new2=str(q['tickers'][int(q['d2'][0,k])]),
                   last_valuation=str(dates[min(k+2,len(dates)-1)].date()),
                   signal_requires_venue_quote=True))
            for policy in ('IMMEDIATE','DELAY3'):
                stop=[];orders=[]
                # Event logging is isolated from math and checked against cached no-log replay.
                withlogs=_impl(q,e,policy='DELAY' if policy=='DELAY3' else 'IMMEDIATE',fraction=3 if policy=='DELAY3' else 1,
                               fee=BASE_FEE,exposure_timing='PREVIOUS',stop_timing='NOW',stop_friction=BASE_FRICTION,
                               ordinary_alarm=False,fast_stop=True,lock_days=3,
                               event_log=stop,order_log=orders)
                assert np.array_equal(withlogs['nav'],outputs[policy]['nav'])
                for s in orders:
                    if s['kind'] != 'ORDER':  # REENTRY is a separate annotation of an ORDER, not extra trade.
                        continue
                    t=ticker_index[s['ticker']];k=s['index'];
                    rows_orders.append(dict(market=market,policy=policy,kind=s['kind'],day=str(dates[k].date()),
                       ticker=s['ticker'],side='BUY' if s['delta']>0 else 'SELL',
                       units=float(s['delta']),theoretical_open=float(s['price']),
                       model_one_sided_notional=abs(float(s['delta']*s['price'])),
                       observed=bool(q['observed'][k,t]) if 'observed' in q else '',
                       venue='',actual_auction_price='',actual_best_bid='',actual_best_ask='',actual_fill=''))
                for s in stop:
                    k=s['signal_index']; t=ticker_index[s['ticker']]
                    low=float(q['L'][k,t]);opening=float(q['O'][k,t]);barrier=float(s['barrier'])
                    rows_stops.append(dict(market=market,policy=policy,date=str(dates[k].date()),
                        ticker=s['ticker'],opening_breach=bool(s['opening_breach']),
                        theoretical_stop=barrier,theoretical_open=opening,theoretical_low=low,
                        low_under_stop_pct=(low/barrier-1)*100,
                        theoretical_fill=float(s['fill_price']),
                        stop_quantity=float(s['quantity']),source_is_bar_proxy=True))
            # Matched-cost and explicitly asymmetric fee cost sensitivity. These are
            # stress-proxies on the engine's half-turnover fee convention, NOT quotes.
            for fee in [.001,.002,.003,.005,.0075,.01]:
                for policy in ('IMMEDIATE','DELAY3'):
                    result=execute(policy,fee,BASE_FRICTION)
                    met={r['period']:r for r in metrics(q,result)}
                    for win,per in [('MAIN','ACTIVE2021_2024'),('FULL','FULL')]:
                        rows_cost.append(dict(market=market,scenario='SAME_FEE',policy=policy,fee_coefficient=fee,
                          stop_friction=BASE_FRICTION,window=win,cagr=float(met[per]['cagr']),
                          maxdd=float(met[per]['maxdd']),turnover_annual_half=float(met[per]['turnover_annual'])))
                # asymmetric: baseline remains at its frozen 0.001
                result=execute('DELAY3',fee,BASE_FRICTION)
                met={r['period']:r for r in metrics(q,result)}
                for win,per in [('MAIN','ACTIVE2021_2024'),('FULL','FULL')]:
                    rows_cost.append(dict(market=market,scenario='DELAY_ONLY_FEE',policy='DELAY3',fee_coefficient=fee,
                        stop_friction=BASE_FRICTION,window=win,cagr=float(met[per]['cagr']),
                        maxdd=float(met[per]['maxdd']),turnover_annual_half=float(met[per]['turnover_annual'])))
            # Find incremental fee coefficient that makes DELAY3 match unchanged baseline.
            for win,per in [('MAIN','ACTIVE2021_2024'),('FULL','FULL')]:
                target=float(decision[(market,'IMMEDIATE')].loc[per,'cagr'])
                lo=BASE_FEE;hi=.02
                def score(f):return next(d['cagr'] for d in metrics(q,execute('DELAY3',float(f),BASE_FRICTION)) if d['period']==per)
                assert score(lo)>target and score(hi)<target
                for _ in range(35):
                    mid=(lo+hi)/2
                    if score(mid)>target:lo=mid
                    else:hi=mid
                rows_boot.append(dict(market=market,window=win,baseline_fee=BASE_FEE,
                    breakeven_delay_fee=(lo+hi)/2,
                    maximum_extra_fee_coefficient_bp=((lo+hi)/2-BASE_FEE)*1e4,
                    cost_metric='OLC19 fee * half turnover + stop fee; not bid/ask or trade fill'))
            # Stop-only incremental friction stress (both policies identical friction):
            for friction in [.001,.005,.01]:
                for policy in ('IMMEDIATE','DELAY3'):
                    met={r['period']:r for r in metrics(q,execute(policy,BASE_FEE,friction))}
                    for win,per in [('MAIN','ACTIVE2021_2024'),('FULL','FULL')]:
                        rows_cost.append(dict(market=market,scenario='SAME_STOP_FRICTION',policy=policy,
                            fee_coefficient=BASE_FEE,stop_friction=friction,window=win,
                            cagr=float(met[per]['cagr']),maxdd=float(met[per]['maxdd']),
                            turnover_annual_half=float(met[per]['turnover_annual'])))
            print(f'{market}: native parity, event split, order/stop logs, execution sensitivities verified.',flush=True)

    # Forensic vendor request prioritization: choose observed extremes for
    # quotation quality checks only. This is NOT a trading signal or model fit.
    months=toframe(rows_month)
    quotes=toframe(rows_liq)
    priority=[]
    for m in ['EU','USA']:
        sub=months[months.market==m]
        main=sub[sub.month.str.slice(0,4).astype(int).between(2021,2024)]
        late=sub[sub.month.str.slice(0,4).astype(int)==2025]
        selected=[]
        for tag,part in [('MAIN_TOP_POSITIVE',main.nlargest(3,'delay_minus_immediate_log_bp')),
                         ('MAIN_TOP_NEGATIVE',main.nsmallest(3,'delay_minus_immediate_log_bp')),
                         ('YEAR2025_NEGATIVE',late.nsmallest(2,'delay_minus_immediate_log_bp'))]:
            for x in part.itertuples():
                selected.append((x.month,tag,float(x.delay_minus_immediate_log_bp)))
        for month,tag,edge in selected:
            matching=quotes[(quotes.market==m)&(quotes.entry_date.str.startswith(month))]
            for r in matching.to_dict('records'):
                priority.append(dict(market=m,month=month,reason=tag,monthly_paired_logbp=edge,
                    day=r['quote_date'],ticker=r['ticker'],event_entry=r['entry_date'],
                    session=r['target_session'],model_open=r['original_O'],
                    venue_from_validated_isin='',real_bid='',real_ask='',auction_price='',
                    quote_time_utc='',source_file='',provenance_verified=''))
    toframe(priority).to_csv(out/'OLC58_PRIORITY_QUOTES.csv',index=False,float_format='%.12g')

    for name,rows in [('PHASES',rows_phase),('FEES',rows_cost),('FEE_BREAKEVEN',rows_boot),
                      ('LEAVE_ONE_YEAR',rows_loo),('EVENTS',rows_events),('QUOTE_REQUEST_EVENTS',rows_liq),
                      ('ORDER_MANIFEST',rows_orders),('STOP_AUDIT',rows_stops),('MONTHLY_RECONCILIATION',rows_month)]:
        toframe(rows).to_csv(out/f'OLC58_{name}.csv',index=False,float_format='%.12g')
    # Source limitations in a machine readable, stable audit record.
    checks['olc19_contains_bid_ask_size_or_volume']=False
    checks['olc19_usa_original_observed_mask']=False
    checks['temporal_validity']='CHECKPOINT 2019-02 through first opening 2026-07; no independent OOS'
    checks['input_original_quote_trade_fills']='NOT AVAILABLE'
    checks['output_files']=sorted(p.name for p in out.glob('OLC58_*.csv'))
    checks['no_strategy_promoted']=True
    (out/'OLC58_QA.json').write_text(json.dumps(checks,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')
    print(json.dumps({'status':'verified','QA':checks,'breakeven':rows_boot,'phase_main':[x for x in rows_phase if x['window']=='MAIN']},indent=2))

if __name__=='__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('--olc19',required=True)
    parser.add_argument('--olc56',required=True)
    parser.add_argument('--out',default='results')
    main(parser.parse_args())