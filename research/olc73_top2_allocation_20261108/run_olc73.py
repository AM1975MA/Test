#!/usr/bin/env python3
"""OLC73 preregistered Top2 allocation factorial; native OLC19 engine, no tuning."""
from __future__ import annotations
import hashlib, json, sys, zipfile, gzip, io
from pathlib import Path
import numpy as np
import pandas as pd
ROOT=Path(__file__).resolve().parent
N=ROOT/'OLC67/native/olc19_combined_risk_20261102'
P=N/'restore/olc18_execution_20261102'
R=ROOT/'results'; R.mkdir(exist_ok=True)
sys.path[:0]=[str(N/'src'),str(P/'parent_archive/parent/olc16_contextual_rank_20261102/src')]
from combined_engine import _impl
from portfolio_metrics_parent import metrics
MARKETS=('EU','USA')
POLICIES=('HALF','TOP1_65','TOP1_75','TOP2_65','TOP2_75','INVOL63_CAP25','MOM63_LEADER65','MINVAR63_CAP25')
TIMINGS=('IMMEDIATE','DELAY3')
FEES=(.001,.003)
SOURCE19=Path('/mnt/data/etf_source/OLC19_Rischio_Rientro_Checkpoint_20261102.zip')
SOURCE56=Path('/mnt/data/files/OLC56_TESTS_20261106_VERIFICATI.zip')
ORIGINAL=Path('/mnt/data/OLC67_Strategia_ETF_Verificata.zip')

def digest(path):
    h=hashlib.sha256()
    with path.open('rb') as file:
        for p in iter(lambda:file.read(4*1024*1024),b''):h.update(p)
    return h.hexdigest()

def load(m):
    q=dict(np.load(P/f'inputs/{m}_TOP2_CONTEXT_REVALUE.npz',allow_pickle=False))
    ev=q.pop('events'); ids=np.flatnonzero(ev)
    decisions=pd.read_csv(ROOT/f'OLC67/native/OLC56_{m}_DECISIONS.csv')
    assert len(ids)==len(decisions)==90
    assert np.array_equal(decisions.event_index.to_numpy(),ids)
    assert np.array_equal(decisions.entry_date.to_numpy(),pd.to_datetime(q['dates'][ids]).strftime('%Y-%m-%d').to_numpy())
    assert np.array_equal(decisions.ticker1.to_numpy(),q['tickers'][q['d1'][0,ids]])
    assert np.array_equal(decisions.ticker2.to_numpy(),q['tickers'][q['d2'][0,ids]])
    assert np.all(q['weights']==.5)
    return q,ev,ids,decisions

def momentum_vol(q,k,i,j):
    # Strict as-of: 64 prior COMPLETED close observations, never event day's close.
    if k<64:return None
    window=q['C'][k-64:k,[i,j]]
    observed=np.asarray(q.get('observed',np.isfinite(q['C']) & (q['C']>0)),bool)[k-64:k,[i,j]]
    # Advanced indexing returns shape (2,64) for numpy; normalize shape.
    if window.shape==(2,64):window=window.T;observed=observed.T
    if window.shape!=(64,2):raise AssertionError(('bad shape',window.shape))
    if not (np.isfinite(window).all() and np.all(window>0) and observed.all()):return None
    lr=np.diff(np.log(window),axis=0)
    vol=lr.std(axis=0,ddof=0)
    mom=np.log(window[-1]/window[0])
    if not (np.isfinite(vol).all() and np.isfinite(mom).all()):return None
    return vol,mom

def make_event_weights(policy,q,ids,d):
    out=[]; fallback=0;data=[]
    for pos,k in enumerate(ids):
        a,b=int(q['d1'][0,k]),int(q['d2'][0,k])
        prev=momentum_vol(q,int(k),a,b)
        if policy=='HALF':w=.5
        elif policy=='TOP1_65':w=.65
        elif policy=='TOP1_75':w=.75
        elif policy=='TOP2_65':w=.35
        elif policy=='TOP2_75':w=.25
        elif policy=='MINVAR63_CAP25':
            w=float(d['weight__B1_MINVAR63_CAP25'].iloc[pos]);fallback+=(not bool(d.valid63.iloc[pos]));
        elif prev is None:
            w=.5;fallback+=1
        elif policy=='INVOL63_CAP25':
            vol,mom=prev
            w=float(np.clip(vol[1]/sum(vol),.25,.75)) if sum(vol)>1e-14 else .5
        elif policy=='MOM63_LEADER65':
            vol,mom=prev
            w=.65 if mom[0]>mom[1]+1e-14 else (.35 if mom[1]>mom[0]+1e-14 else .5)
        else:raise ValueError(policy)
        assert .25-1e-13<=w<=.75+1e-13 and np.isfinite(w)
        out.append(w)
        data.append({'market':d.market.iloc[pos],'event_index':int(k),'date':str(d.entry_date.iloc[pos]),'policy':policy,'top1':str(d.ticker1.iloc[pos]),'top2':str(d.ticker2.iloc[pos]),'w_top1':w,'w_top2':1-w,'fallback':bool(w==.5 and (policy in ('INVOL63_CAP25','MOM63_LEADER65') and prev is None))})
    return np.asarray(out),fallback,data

def apply_event_weights(q,ids,weights):
    qq={k:v for k,v in q.items()};qq['weights']=q['weights'].copy()
    for pos,k in enumerate(ids):
        j=int(ids[pos+1]) if pos+1<len(ids) else qq['weights'].shape[1]
        qq['weights'][0,k:j]=weights[pos]
    assert qq['weights'].shape==q['weights'].shape
    return qq

def logr(r):
    v=r['nav'][:-1]/r['ledger'][:-1,0]
    assert np.all(np.isfinite(v)) and np.all(v>0)
    return np.log(v)

def independent_metrics(x):
    return float(np.expm1(x.mean()*252)),float((np.exp(np.cumsum(x))/np.maximum.accumulate(np.r_[1.,np.exp(np.cumsum(x))])[1:]-1).min())

def run():
    sha={'OLC19':digest(SOURCE19),'OLC56':digest(SOURCE56),'OLC67':digest(ORIGINAL)}
    assert sha['OLC19']=='3b5799dae060c104408f581c70280cef8ce4d84c3978434d4e6ba81108f16540'
    assert sha['OLC56']=='f22b92a5c4b5024d6f8afef6504b794e1f46ff53ffa87adfaa8f3a2e0e3e2573'
    qa={'hashes':sha,'native_parity':{},'prior_OLC67_logparity':{},'runs':[],'fallbacks':{},'event_count':{},'source_observed_mask':{}}
    with zipfile.ZipFile(ORIGINAL) as archive:
        prior=pd.read_csv(io.BytesIO(gzip.decompress(archive.read('OLC67/results/OLC67_DAILY_LOGRET.csv.gz'))))
    pr=prior.set_index(['key','date']).logr
    scores=[]; annual=[]; monthly=[]; weights=[]; dall=[]
    for market in MARKETS:
        q,events,ids,decisions=load(market)
        ds=pd.to_datetime(q['dates'][1:]);qa['event_count'][market]=len(ids)
        qa['source_observed_mask'][market]=('original_flags' if 'observed' in q else 'finite_close_proxy_as_OLC56')
        for policy in POLICIES:
            ww,fallback,data=make_event_weights(policy,q,ids,decisions)
            weights.extend(data);qa['fallbacks'][f'{market}:{policy}']=fallback
            qq=apply_event_weights(q,ids,ww)
            for timing in TIMINGS:
                for fee in FEES:
                    k=f'{market}_{policy}_{timing}_{int(fee*10000)}'
                    r=_impl(qq,events,policy='IMMEDIATE' if timing=='IMMEDIATE' else 'DELAY',fraction=1 if timing=='IMMEDIATE' else 3,
                       fee=fee,exposure_timing='PREVIOUS',stop_timing='NOW',stop_friction=.001,
                       ordinary_alarm=False,fast_stop=True,lock_days=3)
                    x=logr(r);assert len(x)==len(ds)
                    native=np.diff(np.log(np.r_[1.,r['nav']]))[:-1]
                    assert np.max(np.abs(x-native))<1e-10
                    native_metrics=metrics(qq,r)
                    for rec in native_metrics:
                        if rec['period'] in ('FULL','ACTIVE2021_2024','2024','2025','2026','CRASH2020','2021','2022','2023'):
                            mask=(ds>=rec['first_valuation'])&(ds<=rec['last_valuation'])
                            v=x[mask]
                            c,dd=independent_metrics(v)
                            assert len(v)==rec['n'] and abs(c-rec['cagr'])<1e-11 and abs(dd-rec['maxdd'])<1e-11,(k,rec['period'])
                            scores.append({'market':market,'policy':policy,'timing':timing,'fee':fee,'key':k,**rec})
                    for year in sorted(np.unique(ds.year)):
                        mask=ds.year==year
                        annual.append({'market':market,'policy':policy,'timing':timing,'fee':fee,'year':int(year),'n':int(mask.sum()),'return':float(np.expm1(x[mask].sum()))})
                    monthly.append(pd.DataFrame({'date':ds,'market':market,'policy':policy,'timing':timing,'fee':fee,'key':k,'logr':x}))
                    # Baseline exact parity for seven native bookkeeping arrays.
                    if policy=='HALF' and timing=='IMMEDIATE' and fee==.001:
                        saved=N/f'results/paths/{market}_TOP2_CONTEXT_REVALUE_FAST_LOCK3_F10_S10.npz'
                        with np.load(saved) as obj:
                            for name in ['nav','ledger','primary_units','defensive_units','free_cash','targets','risk_trace']:
                                assert np.array_equal(r[name],obj[name]),(market,'native OLC19 parity',name)
                        qa['native_parity'][market]='EXACT_SEVEN_ARRAYS'
                    # Prior OLC67 32 paths: exact baseline & minvar paths at both timing/fee levels.
                    if policy in ('HALF','MINVAR63_CAP25'):
                        previous_policy='HALF' if policy=='HALF' else 'MINVAR63'
                        oldkey=f'{market}_{previous_policy}_{timing}_FAST_LOCK3_{int(fee*10000)}'
                        prev=prior[prior.key==oldkey]
                        assert len(prev)==len(x),(oldkey,len(prev),len(x))
                        err=float(np.max(np.abs(x-prev.logr.to_numpy())))
                        assert err<1e-13,(oldkey,err)
                        qa['prior_OLC67_logparity'][oldkey]=err
                    qa['runs'].append(k)
                    print('RUN',k,'main',round(100*[v['cagr'] for v in native_metrics if v['period']=='ACTIVE2021_2024'][0],3),
                          'full',round(100*[v['cagr'] for v in native_metrics if v['period']=='FULL'][0],3),flush=True)
    assert len(qa['runs'])==64 and len(qa['native_parity'])==2 and len(qa['prior_OLC67_logparity'])==16
    pd.DataFrame(scores).to_csv(R/'OLC73_SCORECARD.csv',index=False)
    pd.DataFrame(annual).to_csv(R/'OLC73_ANNUAL.csv',index=False)
    pd.DataFrame(weights).to_csv(R/'OLC73_EVENT_WEIGHTS.csv',index=False)
    pd.concat(monthly,ignore_index=True).to_csv(R/'OLC73_DAILY_LOGRET.csv.gz',index=False)
    qa['runs_count']=len(qa['runs']);qa['QA_status']='PASS'
    (R/'OLC73_QA.json').write_text(json.dumps(qa,indent=2,ensure_ascii=False))
    print('COMPLETED',len(scores),'scorecard rows',len(annual),'annual rows',flush=True)
if __name__=='__main__':run()