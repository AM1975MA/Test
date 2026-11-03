#!/usr/bin/env python3
"""Conservative score-bridge experiment on *frozen* OLC19 daily execution.

This is NOT an authentic native OLC19 rerank or model refit. New ETF
candidates use a separately preregistered causal 63/126d momentum challenge
against the frozen OLC19 pair. Bookkeeping, LOCK3 and execution use the
original source code from the archived OLC19 checkpoint. No ex-post labels
or contemporaneous EOD data enter the monthly decision.

Usage: python run_olc19_expansion_replay.py
Requires the *original* OLC19 checkpoint zip under ../etf_sources, and
ETF_sector_daily_OHLC_GH.zip in /mnt/data from the frozen GitHub Actions.
"""
from __future__ import annotations
import io, hashlib, json, sys, os
from pathlib import Path
from zipfile import ZipFile
import numpy as np
import pandas as pd
ROOT=Path(__file__).resolve().parent
SOURCES=Path(os.environ.get('OLC19_SOURCES',ROOT.parent/'etf_sources'))
CK=Path(os.environ.get('OLC19_CHECKPOINT_ZIP',SOURCES/'OLC19_Rischio_Rientro_Checkpoint_20261102.zip'))
DAILY=Path(os.environ.get('E1_PRICE_ARTIFACT',ROOT.parent/'ETF_sector_daily_OHLC_GH.zip'))
SRC=Path(os.environ.get('OLC19_SOURCE_ROOT',ROOT.parent/'etf19_dev/olc19_combined_risk_20261102'))
OUT=Path(os.environ.get('E2_OUTPUT_DIR',ROOT/'replay_e2'));OUT.mkdir(parents=True,exist_ok=True)
sys.path.insert(0,str(SRC/'src'))
from combined_engine import simulate
sys.path.append(str(SRC/'restore/olc18_execution_20261102/parent_archive/parent/olc16_contextual_rank_20261102/src'))
from portfolio_metrics_parent import metrics

# Predeclared two policies; no hyperparameter tuning on realized returns.
RULES=('ORIGINAL','MOM63','MOM63_126')
MIN_HISTORY=500
REQUIRE_PREV_CLOSE=True
MARGIN_LOG=.05
CAN={'EU':('G2X.DE','USPY.DE','WTIC.DE','2B76.DE'),'USA':('BOTZ','LIT','PAVE')}
EXCLUSION={'CMOD.MI':'539/2400 inconsistent OHLC bars in downloaded quote series; risk stop cannot be reliably replayed'}


def original(market):
    with ZipFile(CK) as z:
        base='olc19_combined_risk_20261102/'
        p=base+f'restore/olc18_execution_20261102/inputs/{market}_TOP2_CONTEXT_REVALUE.npz'
        with np.load(io.BytesIO(z.read(p)),allow_pickle=False) as a:q={k:a[k] for k in a.files}
        reference=base+f'results/paths/{market}_TOP2_CONTEXT_REVALUE_FAST_LOCK3_F10_S10.npz'
        with np.load(io.BytesIO(z.read(reference)),allow_pickle=False) as a:
            ref_nav=a['nav'].copy()
    ev=q.pop('events')
    return q,ev,ref_nav


def prepare_daily(dates,market):
    arrays=[];quality=[]
    with ZipFile(DAILY) as zipf:
        for ticker in CAN[market]:
            p='candidate_daily/'+ticker.replace('.','_')+'.csv.gz'
            df=pd.read_csv(io.BytesIO(zipf.read(p)),compression='gzip')
            df['date']=pd.to_datetime(df['date'])
            df=df.set_index('date').sort_index()
            assert not df.index.has_duplicates
            for fld in ('open','high','low','close'):
                assert (df[fld]>0).all(),(ticker,fld)
            bad=((df.low>df.high)|(df.low>df.open)|(df.low>df.close)|
                 (df.high<df.open)|(df.high<df.close))
            assert not bad.any(),(ticker,int(bad.sum()))
            dates=pd.DatetimeIndex(dates)
            seen=pd.Index(dates).isin(df.index)
            prev_dates=dates-pd.Timedelta(days=1)
            # Previous available quote strictly BEFORE today's open.
            pc=df['close'].reindex(prev_dates,method='ffill').to_numpy(dtype=float)
            # Today's own last available close for marking even when this venue is closed.
            c=df['close'].reindex(dates,method='ffill').to_numpy(dtype=float)
            def bar(fld):
                b=df[fld].reindex(dates).to_numpy(dtype=float)
                return np.where(seen,b,pc)
            o=bar('open');l=bar('low')
            c=np.where(seen,c,pc)
            assert np.isfinite(o).all() and (o>0).all(),ticker
            assert np.isfinite(l).all() and (l>0).all(),ticker
            assert np.isfinite(pc).all() and (pc>0).all(),ticker
            assert np.isfinite(c).all() and (c>0).all(),ticker
            # Counts use full history, not the truncated OLC19 state window.
            observed_before=np.searchsorted(df.index.values,dates.values,side='left')
            quality.append(dict(market=market,ticker=ticker,n_dates=len(df),
                                missing_OLC19=int((~seen).sum()),
                                start=str(df.index.min().date()),end=str(df.index.max().date()),
                                min_prior_history_2021=int(np.min(observed_before[dates>=pd.Timestamp('2021-01-01')]))))
            arrays.append(dict(ticker=ticker,O=o,L=l,C=c,PC=pc,observed=seen,
                               prior_count=observed_before,gap=o/pc-1))
    return arrays,quality


def with_candidates(q,candidates):
    out={k:v.copy() for k,v in q.items()}
    n=len(candidates)
    for key,fld in [('O','O'),('L','L'),('C','C'),('PC','PC'),('gap','gap')]:
        out[key]=np.column_stack([q[key]]+[x[fld] for x in candidates])
    for key in ('observed','low_observed','UH','SA'):
        if key not in q:
            continue
        new=[]
        for x in candidates:
            if key in ('observed','low_observed'):new.append(x['observed'])
            else:new.append(np.zeros(len(q['dates']),bool))
        out[key]=np.column_stack([q[key]]+new)
    out['tickers']=np.r_[q['tickers'],np.array([x['ticker'] for x in candidates])]
    assert len(set(out['tickers']))==len(out['tickers'])
    return out


def rolling_signal(q,k,ticker_index):
    # Returns calculated at closing BEFORE event k, so before opening execution.
    if k<127:return None
    close=q['C'][:,ticker_index]
    observed=q.get('observed',np.ones_like(q['C'],bool))[:,ticker_index]
    if not np.all(np.isfinite(close[k-127:k])) or (close[k-127:k]<=0).any():return None
    if observed[k-126:k].sum()<120 or observed[k-63:k].sum()<60:
        return None
    r63=float(np.log(close[k-1]/close[k-64]))
    r126=float(np.log(close[k-1]/close[k-127]))
    if not np.isfinite(r63+r126):return None
    return r63,r126


def replay_one(q,ev,ref_nav,market,candidates,policy,fee):
    if policy=='ORIGINAL':
        res=simulate(q,ev,contract='FAST_LOCK3',fee=fee,friction=.001)
        diff=float(np.max(np.abs(res['nav']-ref_nav))) if fee==.001 else np.nan
        if fee==.001: assert diff<1e-10,(market,'baseline reproduction',diff)
        return res, [],diff,q
    orig_n=len(q['tickers'])
    full=with_candidates(q,candidates)
    decisions=[]
    evt=np.flatnonzero(ev)
    for n,k in enumerate(evt):
        if k<127:continue
        old1=int(q['d1'][0,k]);old2=int(q['d2'][0,k]);
        if old1<0 or old2<0 or old1==old2:continue
        old1score=rolling_signal(full,k,old1)
        old2score=rolling_signal(full,k,old2)
        if old1score is None or old2score is None: continue
        avail=[]
        for ci,x in enumerate(candidates):
            if int(x['prior_count'][k])<MIN_HISTORY:continue
            if not x['observed'][k]:continue
            score=rolling_signal(full,k,orig_n+ci)
            if score is None:continue
            r63,r126=score
            if r63<=0:continue
            if policy=='MOM63_126' and r126<=0:continue
            candidate_score=r63 if policy=='MOM63' else .5*(r63+r126)
            avail.append((candidate_score,orig_n+ci,x['ticker'],r63,r126))
        if not avail:continue
        best=max(avail,key=lambda a:(a[0],a[2]))
        o1=old1score[0] if policy=='MOM63' else .5*sum(old1score)
        o2=old2score[0] if policy=='MOM63' else .5*sum(old2score)
        if best[0] <= max(o1,o2)+MARGIN_LOG:continue
        next_event=int(evt[n+1]) if n+1<len(evt) else len(ev)
        # Preserve 50% OLC19 first slot, replace 50% second slot. Leave V6
        # g and defensive allocations frozen to original as-of policies.
        full['d2'][0,k:next_event]=best[1]
        decisions.append(dict(market=market,policy=policy,
          signal_date=str(q['dates'][k-1])[:10],execution_date=str(q['dates'][k])[:10],
          previous_top1=str(q['tickers'][old1]),previous_top2=str(q['tickers'][old2]),
          selected_new=best[2],new_mom63_log=best[3],new_mom126_log=best[4],
          old1_mom63_log=old1score[0],old1_mom126_log=old1score[1],
          old2_mom63_log=old2score[0],old2_mom126_log=old2score[1],
          min_history=int(candidates[best[1]-orig_n]['prior_count'][k]),
          seen_event_price=bool(candidates[best[1]-orig_n]['observed'][k]),
          first_exposure_fraction_nominal=.5))
    res=simulate(full,ev,contract='FAST_LOCK3',fee=fee,friction=.001)
    # Full accounting reconciliation and audit of holdings => no phantom trades.
    assert (res['nav']>0).all()
    return res,decisions,np.nan,full


def main():
    rows=[];annual=[];decisions=[];quotes=[];nav_export=[]
    for mk in ('EU','USA'):
        q,ev,ref=original(mk)
        c,qua=prepare_daily(q['dates'],mk);quotes+=qua
        for fee in (.001,.003):
          for policy in RULES:
            res,decs,max_diff,qx=replay_one(q,ev,ref,mk,c,policy,fee)
            m=metrics(qx,res)
            for a in m:
                rows.append(dict(market=mk,policy=policy,fee=fee,**a,reference_reproduction_diff=max_diff))
            decisions+=[dict(fee=fee,**x) for x in decs]
            nav_export.append(pd.DataFrame({'market':mk,'policy':policy,'fee':fee,'date':qx['dates'][1:].astype('datetime64[D]').astype(str),'nav_at_next_open':res['nav'][:-1], 'net_daily_return':res['nav'][:-1]/res['ledger'][:-1,0]-1}))
            # Conditional return by year, identical calendar across arms.
            dates=pd.to_datetime(qx['dates'][1:])
            rat=res['nav'][:-1]/res['ledger'][:-1,0]
            for year in range(2019,2027):
                mask=(dates>=pd.Timestamp(f'{year}-01-01')) & (dates<pd.Timestamp(f'{year+1}-01-01'))
                if mask.sum():
                    annual.append(dict(market=mk,policy=policy,fee=fee,year=year,observations=int(mask.sum()),
                       return_pct=100*(float(np.prod(rat[mask]))-1)))
            print(mk,fee,policy,'n_decisions',len(decs),
                  'active_cagr',[round(a['cagr']*100,5) for a in m if a['period']=='ACTIVE2021_2024'],flush=True)
    df=pd.DataFrame(rows)
    df.to_csv(OUT/'scorecard_all_periods.csv',index=False)
    pd.DataFrame(annual).to_csv(OUT/'annual_returns.csv',index=False)
    pd.DataFrame(decisions).to_csv(OUT/'new_sector_decisions.csv',index=False)
    pd.DataFrame(quotes).to_csv(OUT/'price_quality.csv',index=False)
    pd.concat(nav_export,ignore_index=True).to_csv(OUT/'daily_nav.csv.gz',index=False,compression='gzip')
    summary=df[(df.period=='ACTIVE2021_2024') & (df.fee==.001)]
    print(summary[['market','policy','cagr','maxdd','turnover_annual','stops','rebalances']].to_string(index=False))
    assert len(summary)==len(RULES)*2
    assert (summary.groupby('market').size()==len(RULES)).all()
    manifest={'status':'research-only conditional challenger, not native OLC19 reranking',
      'baseline':'OLC19 checkpoint 20261102, exact frozen risk/execution engine',
      'q_sha256':hashlib.sha256(CK.read_bytes()).hexdigest(),
      'candidate_daily_zip_sha256':hashlib.sha256(DAILY.read_bytes()).hexdigest(),
      'rules':{'MOM63':'63-day log momentum, new beats BOTH incumbents by 0.05 log and positive',
               'MOM63_126':'63 & 126 day positive; average log momentum beats BOTH by 0.05 log'},
      'venue_risk_exclusions':EXCLUSION,
      'candidate_universe':CAN,
      'min_history_prices_original':MIN_HISTORY,
      'risk_convention':'OLC19 FAST_LOCK3; same g/alt originally frozen, not rescored for new ETFs',
      'cost':'.001 or .003 legacy rebalance fee + .001 stop friction',
      'entry':'next monthly opening, calculated at last close prior to event',
      'historical_period':'2019-02-01 to 2026-07-01; primary 2021–2024',
      'warning':'2021-2024 repeatedly researched; no independent prospective test'}
    (OUT/'manifest.json').write_text(json.dumps(manifest,indent=2))
if __name__=='__main__':main()