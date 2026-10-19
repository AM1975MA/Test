#!/usr/bin/env python3
"""Frozen Europe-only EUR60 annual-OOS R_H score -> four isolated risk treatments.

No F3/H1 US prediction leakage. True self-financed ETF shares and zero-yield
EUR cash. Historical 2017-2026 EUR candidate survivor universe not PIT.
"""
from __future__ import annotations
import argparse, hashlib, json, math
from pathlib import Path
import numpy as np
import pandas as pd

ROOT=Path(__file__).resolve().parents[2]
ROSTER=ROOT/"europe_only75/UNIVERSE_EUR_LISTED_60.csv"
ORIGINAL120=ROOT/"data/eu120/raw_ticker_csv"
MANIFEST=ROOT/"europe_only75/MANIFEST.json"
REF=("SPY","HYG","IEF","BIL","SHV")
ARMS=("B0_RH_TOP2","E1_CATEGORY","E2_VOL20","E3_TREND126","E4_BUFFER")
SEED=20261019

def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()

def read_prices(tickers,src):
    series={}
    for t in tickers:
        f=Path(src)/(t+".csv")
        if not f.is_file():raise AssertionError("Missing exact source "+str(f))
        d=pd.read_csv(f,parse_dates=["date"])
        if d.date.duplicated().any():raise AssertionError("Duplicate date "+t)
        d=d.set_index("date").sort_index()
        for col in ("Open","Close"):
            z=d[col].astype(float)
            z=z.where(np.isfinite(z)&(z>0))
            series.setdefault(col,{})[t]=z
    return {key:pd.concat(values,axis=1).sort_index()
            for key,values in series.items()}

def construct_calendar(opens,refits):
    cp,hp=refits
    cp["signal_date"]=pd.to_datetime(cp.signal_date)
    hp["signal_date"]=pd.to_datetime(hp.signal_date)
    signal=sorted(set(cp.signal_date)&set(hp.signal_date))
    signal=[x for x in signal if pd.Timestamp("2017-01-31")<=x<=pd.Timestamp("2026-06-30")]
    common=opens.notna().all(axis=1)
    dates=opens.index[common]
    assert dates.is_monotonic_increasing and len(dates)>1800
    rows=[]
    for sig in signal:
        ix=dates.searchsorted(sig,side="right")
        if ix>=len(dates):raise AssertionError("Missing post-signal joint Open")
        rows.append(dict(signal_date=sig,entry_date=dates[ix]))
    cal=pd.DataFrame(rows)
    cal["exit_date"]=cal.entry_date.shift(-1)
    cal=cal.dropna(subset=["exit_date"]).reset_index(drop=True)
    if len(cal)<100 or len(cal)>113:raise AssertionError("Unexpected common calendar "+str(len(cal)))
    assert (cal.signal_date<cal.entry_date).all()
    assert (cal.entry_date<cal.exit_date).all()
    return cal,dates

def frozen_rh_scores(cp,hp,cal,tickers):
    dates=pd.DatetimeIndex(cal.signal_date)
    expected=pd.MultiIndex.from_product([dates,tickers],names=["signal_date","ticker"])
    a=cp.set_index(["signal_date","ticker"]).reindex(expected)
    b=hp.set_index(["signal_date","ticker"]).reindex(expected)
    if (a.index.duplicated().any() or b.index.duplicated().any()):
        raise AssertionError("Duplicate archived model scores")
    ret=a.R_RAW.groupby(level=0,sort=True).rank(method="average",pct=True).to_numpy(float)
    ret=ret.reshape(len(dates),len(tickers))
    et=b.ET_RANK.to_numpy(float).reshape(len(dates),len(tickers))
    xb=b.XGB_RANK.to_numpy(float).reshape(len(dates),len(tickers))
    h=.6*et+.4*xb
    prev=np.concatenate([h[:1],h[:-1]],axis=0)
    prev2=np.concatenate([h[:1],h[:1],h[:-2]],axis=0)
    smooth=.4*h+.3*prev+.3*prev2
    tail=np.power(np.clip(smooth,0,1),1.1)
    score=.475*ret+.525*tail
    assert score.shape==(len(cal),60)
    if np.isinf(score).any():raise AssertionError("Inf frozen predictions")
    if min(np.isfinite(score).sum(axis=1))<2:raise AssertionError("No two scored ETFs")
    return score

def selections(scores,tickers):
    return [[tickers[j] for j in np.argsort(
        -np.where(np.isfinite(row),row,-1e6),kind="stable")[:2]]
        for row in scores]

def verify_archived_fixed(cal,orig,prices,fixed_archive):
    archived=pd.read_csv(fixed_archive).set_index("variant")
    prev={};equity=1.
    for i,row in cal.iterrows():
        names=orig[i]
        now={t:.5 for t in names}
        turnover=.5*sum(abs(now.get(t,0)-prev.get(t,0))
                        for t in set(now)|set(prev))
        start=prices.loc[row.entry_date,names].to_numpy(float)
        end=prices.loc[row.exit_date,names].to_numpy(float)
        if not np.isfinite(start).all() or not np.isfinite(end).all():
            raise AssertionError("Actual common quote missing")
        equity*=float(np.mean(end/start))*(1-.001*turnover)
        prev=now
    expected=float(archived.loc["R_H","terminal_equity"])
    error=abs(equity-expected)
    if error>1e-9:raise AssertionError("EUR R_H historical model parity failed "+str(error))
    return dict(archived_approx_equity=expected,
                reconstructed_approx_equity=equity, absolute_error=error,
                archived_cagr=float(archived.loc["R_H","cagr"]))

def completed_history(close,tickers,signal,n):
    """All historical returns from previously completed Euro ticker closes."""
    d=close.loc[:pd.Timestamp(signal),list(tickers)].dropna().tail(n+1)
    if len(d)!=n+1:raise AssertionError("Insufficient asof close history "+str(signal))
    if d.index[-1]>pd.Timestamp(signal):raise AssertionError("Close lookahead")
    if (pd.Timestamp(signal)-d.index[-1]).days>8:raise AssertionError("Stale signal Close")
    r=np.diff(np.log(d.to_numpy(float)),axis=0)
    if not np.isfinite(r).all():raise AssertionError("Price/return invalid")
    return r,np.log(d.iloc[-1].to_numpy(float)/d.iloc[0].to_numpy(float))

def model_policies(origin,idx,score,tickers,cats,closes,signal,previous):
    assert len(origin)==2 and len(set(origin))==2
    baseline={t:.5 for t in origin}
    label_match=cats[origin[0]]==cats[origin[1]]
    ec=.8 if label_match else 1.
    category={t:ec*.5 for t in origin}
    r63,_=completed_history(closes,origin,signal,63)
    covariance=np.cov(r63,rowvar=False)
    covariance=.5*covariance+.5*np.diag(np.diag(covariance))
    annual=float(np.sqrt(max(1e-16,.5*np.ones(2) @ covariance @ (.5*np.ones(2)))*252))
    vol_exp=float(np.clip(.20/annual,.40,1.))
    vol={t:.5*vol_exp for t in origin}
    r126,mom=completed_history(closes,origin,signal,126)
    trend=float(np.mean(mom))
    trend_exp=.5 if trend<0 else 1.
    trend_w={t:.5*trend_exp for t in origin}
    ranked=[tickers[i] for i in np.argsort(
        -np.where(np.isfinite(score),score,-1e6),kind="stable")]
    scoremap=dict(zip(tickers,score))
    current_second=float(scoremap[ranked[1]])
    sigma=float(np.nanstd(score,ddof=1))
    old=[t for t in previous if t in ranked[:4] and
         float(scoremap[t])>=current_second-.15*sigma]
    buffered=list(old)
    for t in ranked:
        if len(buffered)>=2:break
        if t not in buffered:buffered.append(t)
    assert len(buffered)==2 and len(set(buffered))==2
    buffer_weights={t:.5 for t in buffered}
    return {
      "B0_RH_TOP2":baseline,
      "E1_CATEGORY":category,
      "E2_VOL20":vol,
      "E3_TREND126":trend_w,
      "E4_BUFFER":buffer_weights
    }, buffered,dict(
      same_category=int(label_match),vol63_annual=float(annual),
      vol_invested=vol_exp,trend_126=float(trend),
      trend_invested=trend_exp,buffer_changed=int(set(buffered)!=set(origin)),
      category_invested=ec)


def rebalance(shares,cash,target,openquotes):
    """Solve wealth net of bilateral 10bp ETF trading, no cash transaction cost."""
    union=set(shares)|set(target)
    old={t:float(shares.get(t,0)*openquotes[t]) for t in union}
    before=cash+sum(old.values())
    assert before>0
    mass=sum(target.values())
    assert 0<=mass<=1+1e-12 and all(v>=0 for v in target.values())
    after=before
    for _ in range(90):
        gross=sum(abs(after*target.get(t,0)-old[t]) for t in union)
        nxt=before-.001*gross
        if abs(nxt-after)<1e-14:
            after=nxt;break
        after=nxt
    new={t:after*w/openquotes[t] for t,w in target.items() if w>1e-14}
    sell=sum(max(old[t]-after*target.get(t,0),0.) for t in union)
    buy=sum(max(after*target.get(t,0)-old[t],0.) for t in union)
    remaining=cash+.999*sell-1.001*buy
    expected=after*(1-mass)
    if abs(remaining-expected)>2e-9*max(1.,after):
        raise AssertionError("Cash not self financed")
    return new,float(max(0,remaining)),float(sell+buy),float(before-after)


def execute(weightseq,calendar,price,allcommon):
    days=allcommon[(allcommon>=calendar.entry_date.min())&
                   (allcommon<=calendar.exit_date.max())]
    assert len(days)>1600
    positions={};cash=1.;daily={};fee=0.;traded=0.;monthly=[]
    for k,row in calendar.iterrows():
        current=row.entry_date;ending=row.exit_date
        w=weightseq[k]
        quote={t:float(price.loc[current,t]) for t in set(positions)|set(w)}
        pre=cash+sum(positions[t]*quote[t] for t in positions)
        positions,cash,turn,cost=rebalance(positions,cash,w,quote)
        fee+=cost;traded+=turn
        dates=days[(days>=current)&(days<=ending)]
        for date in dates:
            currentnav=cash+sum(q*float(price.loc[date,t])
                                for t,q in positions.items())
            if date==ending:
                out=currentnav
            else:
                daily[pd.Timestamp(date)]=currentnav
        monthly.append(dict(signal=str(row.signal_date.date()),
                            entry=str(current.date()),exit=str(ending.date()),
                            before=float(pre),after_trade=float(
                                cash+sum(positions[t]*quote[t] for t in positions)),
                            end_nav=float(out),log_growth=float(np.log(out/pre)),
                            invested=float(sum(w.values())),monthly_fee=float(cost)))
    daily[pd.Timestamp(calendar.exit_date.iloc[-1])]=float(out)
    nav=pd.Series(daily).sort_index()
    if len(nav)!=len(days) or not np.array_equal(nav.index.to_numpy(),days.to_numpy()):
        raise AssertionError("Missing daily common Open mark")
    arr=nav.to_numpy(float)
    assert np.isfinite(arr).all() and np.all(arr>0)
    dr=np.diff(np.log(arr))
    es5=float(np.mean(np.sort(np.expm1(dr))[:int(np.ceil(.05*len(dr)))]))
    n=(days[-1]-days[0]).days/365.25
    underwater=arr<np.maximum.accumulate(arr)-1e-12
    longest=0;length=0
    for x in underwater:
        length=length+1 if x else 0
        longest=max(longest,length)
    stats=dict(
        cagr=float(float(out)**(1/n)-1),
        wealth_final=float(out),
        maxdd_daily_open=float(np.min(arr/np.maximum.accumulate(arr)-1)),
        sharpe_daily_log=float(np.mean(dr)/np.std(dr,ddof=1)*np.sqrt(252)),
        es5_daily=es5,
        annualized_vol=float(np.std(dr,ddof=1)*np.sqrt(252)),
        fee_notional=float(fee),gross_traded_initial_dollars=float(traded),
        mean_invested=float(np.mean([sum(w.values()) for w in weightseq])),
        months_cash=int(sum(sum(w.values())<.9999 for w in weightseq)),
        max_underwater_common_sessions=int(longest),
        daily_common_open_count=len(nav))
    return stats,nav,pd.DataFrame(monthly)


def ci_bootstrap(values,seed=SEED,n=3000):
    a=np.asarray(values,float)
    assert len(a)>100 and np.isfinite(a).all()
    rng=np.random.default_rng(seed);dist=[]
    for _ in range(n):
        chosen=[]
        while len(chosen)<len(a):
            j=int(rng.integers(len(a)))
            chosen.extend([(j+k)%len(a) for k in range(3)])
        dist.append(float(a[np.array(chosen[:len(a)],int)].mean()))
    return dict(mean=float(a.mean()),ci_98_75=[
        float(v) for v in np.quantile(dist,[.00625,.99375])],
        ci_95=[float(v) for v in np.quantile(dist,[.025,.975])])


def run(models,refs,output):
    out=Path(output);out.mkdir(parents=True,exist_ok=False)
    roster=pd.read_csv(ROSTER)
    assert len(roster)==60 and roster.ticker.nunique()==60
    assert roster.macro_category.str.startswith("EU_").all()
    assert roster.ticker.str.endswith((".DE",".MI",".AS",".PA",".MC")).all()
    assert json.loads(MANIFEST.read_text())["retained_count"]==75
    tickers=list(roster.ticker);cats=dict(zip(roster.ticker,roster.macro_category))
    audit=pd.read_csv(Path(models)/"TRAINING_AUDIT.csv")
    assert set(audit.year)==set(range(2017,2027))
    assert len(audit)==10 and audit.lookahead_guard_PASS.astype(bool).all()
    for z in audit.itertuples(index=False):
        assert pd.Timestamp(z.latest_training_label_exit)<pd.Timestamp(int(z.year),1,1)
        assert pd.Timestamp(z.ma3_latest_exit)<pd.Timestamp(int(z.year),1,1)
    cp=pd.read_parquet(Path(models)/"COMPACT_REFITTED.parquet")
    hp=pd.read_parquet(Path(models)/"HYBRID_REFITTED.parquet")
    candidate=read_prices(tickers,ORIGINAL120)
    reference=read_prices(REF,Path(refs)/"etf_trader_raw")
    fullO=pd.concat([candidate["Open"],reference["Open"]],axis=1).sort_index()
    cal,common=construct_calendar(fullO,(cp,hp))
    scores=frozen_rh_scores(cp,hp,cal,tickers)
    base=selections(scores,tickers)
    parity=verify_archived_fixed(cal,base,candidate["Open"],Path(models)/"FIXED_5050.csv")
    paths={name:[] for name in ARMS}
    statuses=[];allweights=[];old=[]
    for k,row in cal.iterrows():
        variants,old,diag=model_policies(base[k],k,scores[k],tickers,cats,
             candidate["Close"],row.signal_date,old)
        for name,w in variants.items():
            assert all(t in tickers for t in w)
            if name!="E4_BUFFER":assert set(w)==set(base[k])
            assert 0 < sum(w.values())<=1+1e-11
            paths[name].append(w)
            allweights.extend(dict(block=k,signal=str(row.signal_date.date()),
                       arm=name,ticker=t,weight=float(val)) for t,val in w.items())
        statuses.append(dict(block=k,signal=str(row.signal_date.date()),
             orig_first=base[k][0],orig_second=base[k][1],**diag))
    stats={};ledgers={};equities={}
    for name in ARMS:
        stat,nav,monthly=execute(paths[name],cal,candidate["Open"],common)
        stats[name]=stat;ledgers[name]=monthly;equities[name]=nav
    assert all(equities[x].index.equals(equities[ARMS[0]].index) for x in ARMS)
    assert len(ledgers[ARMS[0]])==len(cal)
    paired={}
    years=cal.signal_date.dt.year.to_numpy(int)
    origlog=ledgers[ARMS[0]].log_growth.to_numpy(float)
    for i,name in enumerate(ARMS[1:]):
        gains=ledgers[name].log_growth.to_numpy(float)-origlog
        ci=ci_bootstrap(gains,SEED+i+1)
        era={tag:float(gains[mask].mean()) for tag,mask in (
            ("2017_2020",years<=2020),
            ("2021_2023",(years>=2021)&(years<=2023)),
            ("2024_2026",years>=2024))}
        dd=(stats[name]["maxdd_daily_open"]-stats[ARMS[0]]["maxdd_daily_open"])*100
        es=stats[name]["es5_daily"]-stats[ARMS[0]]["es5_daily"]
        paired[name]=dict(net_log_growth_paired=ci,eras=era,
            maxdd_improvement_pp=float(dd),es5_improvement_pp=float(es*100),
            strict_GO=bool(ci["ci_98_75"][0]>0 and dd>=1.5
                           and es>=0 and all(v>0 for v in era.values())))
    date=equities[ARMS[0]].index
    daily=pd.DataFrame({"day":date})
    for name in ARMS:daily[name]=equities[name].to_numpy(float)
    daily.to_csv(out/"DAILY_COMMON_OPEN_COSTED_NAV.csv",index=False)
    pd.DataFrame(statuses).to_csv(out/"ASOF_MONTHLY_STATES.csv",index=False)
    pd.DataFrame(allweights).to_csv(out/"MONTHLY_EUROPE_ONLY_WEIGHTS.csv",index=False)
    lm=pd.concat([x.assign(arm=name) for name,x in ledgers.items()],ignore_index=True)
    lm.to_csv(out/"EXACT_COSTED_MONTHLY_PNL.csv",index=False)
    cal.to_csv(out/"EXACT_EUROPE_COMMON_CALENDAR.csv",index=False)
    result=dict(status="EUROPE60_FOUR_STANDALONE_RISK_TRIALS_COMPLETE",
        europe_universe_tickers=60,geography_all_75=75,excluded_non_eur=15,
        source_eu120_non_europe_excluded=45,
        model_source_action=39071370480,
        trained_eu_folds=10,trained_on_original149=False,
        model_score_type="EUR60 annual matured-fold R_H top2",
        source_eur60_roster_sha256=sha(ROSTER),
        source_compact_pred_sha256=sha(Path(models)/"COMPACT_REFITTED.parquet"),
        source_hybrid_pred_sha256=sha(Path(models)/"HYBRID_REFITTED.parquet"),
        source_training_audit_sha256=sha(Path(models)/"TRAINING_AUDIT.csv"),
        source_calendar_price_refs=REF,
        all_months=len(cal),
        common_daily_open_count=len(date),
        original_refit_approx_5050_parity=parity,
        new_cost_engine="self-financing 10bp ETF buy/sale, 0bp cash",
        policy_stats=stats,paired_tests=paired,
        precommitted_go=[m for m,v in paired.items() if v["strict_GO"]],
        historical_development_not_independent=True,
        actual_EUR_trade_currency_and_ISIN_not_verified=True,
        no_production_change=True,
        warnings=["EUR60 historical survivor ticker lines from 2026 source; not PIT",
           "Adjusted Yahoo OHLC histories may be revised; no historical vendor vintages",
           "Same-fund multiple ticker lines or ISIN duplicates not audited",
           "No live bid/ask slippage, broker FX, taxes or cash interest",
           "Old published 9.978% EUR60 R_H fixed5050 and new share-level 5050 have different fee accounting; do not conflate"])
    (out/"RESULT.json").write_text(json.dumps(result,indent=2)+"\n")
    print("EUROPE60_RISK_ABLATION_RESULT "+json.dumps(result),flush=True)
    return result


if __name__=="__main__":
    p=argparse.ArgumentParser()
    p.add_argument("--models",required=True)
    p.add_argument("--raw149",required=True)
    p.add_argument("--out",required=True)
    a=p.parse_args()
    run(a.models,a.raw149,a.out)
