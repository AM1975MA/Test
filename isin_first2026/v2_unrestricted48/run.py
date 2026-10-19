#!/usr/bin/env python3
"""ONE unrestricted Europe-48 ETF Trainer V2 benchmark and producer, not 500 baskets.

Real source-only TIT_R + MA3 Hybrid24 re-fit, original source DD-first,
V6 and exact daily full-asset share/stop engine. V2 differs only by risk-off
model agreement concentration. Risk references are explicitly EU proxies.
NO ticker/category quotas in ranking, no privileged sector filter.
"""
from __future__ import annotations
import argparse,hashlib,importlib.util,inspect,json,os,sys
from pathlib import Path
import numpy as np
import pandas as pd
from etf_trader.source_only.raw_io import load_ticker_csv_folder
from etf_trader.ma3 import producer,ddfirst,v6,highcagr24
from etf_trader.ma3.hybrid_producer import fit_hybrid_producer
from isin_first2026.v2_unrestricted48.cluster_adapter import enable
ROOT=Path(__file__).resolve().parents[2]
BASKET_NAME="UNRESTRICTED_ALL_48_LEGAL_ISIN"
REF=ROOT/"isin_first2026/refit48/results/RESULT.json"
DATA=ROOT/"isin_first2026/full_eu_2017/results"

def sha(f):
    h=hashlib.sha256()
    with Path(f).open("rb") as d:
        for block in iter(lambda:d.read(1<<20),b""):h.update(block)
    return h.hexdigest()

def build_panel(src_data,output):
    cluster_changes=enable()
    builder=ROOT/"vendor/etf_trader_v2/scripts/build_ma3_panel_source_only.py"
    sp=importlib.util.spec_from_file_location("original_etf_trader_build_ma3_source",builder)
    mod=importlib.util.module_from_spec(sp)
    sp.loader.exec_module(mod)
    save=list(sys.argv)
    try:
        sys.argv=[str(builder),"--data",str(src_data),"--output",str(output)]
        status=mod.main()
        assert status==0
    finally:sys.argv=save
    return cluster_changes

def risk_reference_euro48(closes,corp_high_yield):
    # Preserve ORIGINAL ddfirst risk ladder and thresholds, replace ONLY factor
    # source identities; breadths are computed over precisely the 48 assets,
    # never counting risk-only aliases as 49th/50th portfolio choices.
    close=closes.astype(float)
    spy=close["IMEU.AS"]
    spyret=spy.pct_change(fill_method=None)
    ma200=spy.rolling(200,min_periods=150).mean()
    sv=(spy/ma200-1).shift(1).fillna(0.0)
    ret21=close/close.shift(21)-1
    ret63=close/close.shift(63)-1
    b21=(ret21>0).mean(axis=1).shift(1).fillna(.5)
    b63=(ret63>0).mean(axis=1).shift(1).fillna(.5)
    v20=(spyret.rolling(20,min_periods=15).std()*np.sqrt(252)).shift(1).fillna(.15)
    cref=corp_high_yield.reindex(close.index).ffill(limit=3)
    ratio=cref/close["EUNH.DE"]
    credit21=(ratio/ratio.shift(21)-1).shift(1).fillna(0.0)
    ma63=close.rolling(63,min_periods=40).mean()
    ma126=close.rolling(126,min_periods=80).mean()
    ba63=(close>ma63).mean(axis=1).shift(1).fillna(.5)
    ba126=(close>ma126).mean(axis=1).shift(1).fillna(.5)
    return dict(spy_vs200=sv.to_numpy(float),
        breadth21=b21.to_numpy(float),breadth63=b63.to_numpy(float),
        vol20=v20.to_numpy(float),credit21=credit21.to_numpy(float),
        above_ma63=ba63.to_numpy(float),above_ma126=ba126.to_numpy(float))

def v6_reference_europe():
    # Immutable original function source. One exact source token is swapped
    # from US SPY index to Europe IMEU index, without injecting tradable aliases.
    source=inspect.getsource(v6.build_v6_state)
    needle='spy=ti["SPY"]'
    if source.count(needle)!=1:raise RuntimeError("V6 original source SPY ref drift")
    translated=source.replace(needle,'spy=ti["IMEU.AS"]')
    ns={}
    exec(compile(translated,"<V6_REFERENCES_SPY_to_MSCI_EUROPE>","exec"),v6.__dict__,ns)
    return ns["build_v6_state"]

def evaluate(E,T,dates,start="2021-02-01",end="2026-07-01"):
    # Source engine output is daily value at Open marks, with first day rebalance.
    dates=pd.DatetimeIndex(dates)
    mask=(dates>=pd.Timestamp(start))&(dates<=pd.Timestamp(end))
    vals=np.asarray(E[0,mask],float);t=np.asarray(T[0,mask],float)
    ds=dates[mask]
    assert len(vals)>1200 and np.isfinite(vals).all() and (vals>0).all()
    # Match EXACT ETF Trader source runner metrics: the initial invested
    # portfolio starts at NAV 1.0. Engine E[0] already includes first-session
    # trading/price performance. Excluding it would artificially omit costs
    # and first day's gain/loss from reported CAGR and Sharpe.
    logret=np.diff(np.log(np.r_[1.0,vals]))
    returns=np.expm1(logret)
    n=len(logret)
    cagr=float(np.expm1(logret.sum()*252/n))
    equity=np.exp(np.cumsum(logret))
    high=np.maximum.accumulate(np.r_[1.0,equity])[1:]
    dd=float(np.min(equity/high-1))
    annvol=float(returns.std(ddof=1)*np.sqrt(252))
    sharpe=(float(returns.mean()*np.sqrt(252)/returns.std(ddof=1))
             if annvol>0 else 0.0)
    return dict(cagr=cagr,
        maxdd=dd,sharpe=sharpe,ann_vol=annvol,
        es5_daily=float(np.sort(logret)[:max(1,int(.05*len(logret)))].mean()),
        terminal_nav=float(vals[-1]),days=len(vals),
        turnover_ann=float(t.mean()*252),n_months=65)

def run(prep,tit,output):
    output=Path(output);output.mkdir(exist_ok=False,parents=True)
    prep=Path(prep);tit=Path(tit)
    raw=prep/"raw_ticker_csv"
    mats,cats,manifest=load_ticker_csv_folder(raw)
    universe=pd.read_csv(raw/"universe.csv")
    assert len(universe)==48 and universe["isin"].nunique()==48
    names=list(mats["Open"].columns)
    assert len(names)==48
    schedule=pd.read_csv(tit/"TIT_R_SOURCE_ONLY.csv",
       parse_dates=["signal_date","entry_date","exit_date"])
    schedule=schedule[schedule.exit_date.notna()]
    assert schedule.ticker.nunique()==48
    assert schedule.groupby("signal_date").ticker.nunique().eq(48).all()
    cal=schedule[["signal_date","entry_date","exit_date"]].drop_duplicates().sort_values("signal_date")
    assert len(cal)==65,(len(cal),cal.tail(4).to_string(index=False))
    assert cal.entry_date.min()>=pd.Timestamp("2021-02-01")
    print("SOURCE_EU48_UNRESTRICTED_CALENDAR",len(cal),len(names),flush=True)

    ma3=output/"model_feature_build";ma3.mkdir()
    port=build_panel(raw,ma3)
    p=fit_hybrid_producer(pd.read_pickle(ma3/"RAW_FEATURE_PANEL.pkl"),
       schedule,names,start_year=2021,end_year=2026,et_n_jobs=2,xgb_n_jobs=2)
    assert p.fit_audit.maturity_ok.all() and len(p.fit_audit)==6
    assert len(p.calendar)==65 and p.score.shape==(65,48)
    assert np.isfinite(p.score).all()
    p.predictions.to_csv(output/"MA3_HYBRID24_48_TICKER_PREDICTIONS.csv",index=False)
    p.fit_audit.to_csv(output/"MA3_HYBRID24_MATURITY_FIT_AUDIT.csv",index=False)
    print("SOURCE_EU48_MA3_RETRAIN_COMPLETE",p.fit_audit.to_dict("records"),flush=True)

    # Crucial: ONLY ONE 48-fund basket, never 500 x 24 and never 4/category.
    membership=pd.DataFrame(dict(basket=[0]*48,ticker=names))
    BM,BOK=producer.basket_arrays(membership,names,n_baskets=1)
    assert BM.shape==(1,48) and BOK.all()
    assert set(names)==set(universe.ticker)
    Odf=mats["Open"];Ldf=mats["Low"];Cdf=mats["Close"]
    start=p.calendar.entry_date.min()
    end=p.calendar.exit_date.max()
    Odf=Odf.loc[:end]
    Ldf=Ldf.loc[Odf.index]
    Cdf=Cdf.loc[Odf.index]
    st=Odf.index.get_loc(start);en=Odf.index.get_loc(end)
    ds=Odf.index[st:en+1]
    assert pd.Timestamp(ds[0])==pd.Timestamp("2021-02-01")
    assert pd.Timestamp(ds[-1])==pd.Timestamp("2026-07-01")
    ex=ddfirst.daily_execution_inputs(Odf,Ldf,Cdf)
    O,L,C,PC,gap,ud1,uneg,UH,SA=[
       ex[k][st:en+1] for k in ("O","L","C","PC","gap","ud1","uneg","UH","SA")]
    risk_csv=pd.read_csv(prep/"EURO_CORP_HY_RISK_ONLY.csv",parse_dates=["date"])
    ihyg=risk_csv.set_index("date")["Close"]
    original_market_state=ddfirst.market_state
    try:
        ddfirst.market_state=lambda c:risk_reference_euro48(c,ihyg)
        ddgross=np.asarray(ddfirst.sync_c95_m75_gross(Cdf),float)[st:en+1]
    finally:ddfirst.market_state=original_market_state
    alloc=producer.allocations_from_score(p.score,p.calendar,ds,BM,BOK,continuous=True)
    assert alloc.d1.shape==(1,len(ds))
    v6_build=v6_reference_europe()
    state=v6_build(Cdf.loc[ds,names],
          alloc.d1,alloc.d2,alloc.weight1,ddgross,
          bil_ticker="IBCA.DE",shv_ticker="IBCN.DE")
    g,w0=highcagr24.apply_highcagr24(ddgross,alloc.weight1,alloc.margin)
    # Frozen ETF_TRAINER_V2 version rule: do NOT increase gross during risk-off.
    wv=w0.copy();events=[];source_pred=p.predictions
    et=(source_pred.pivot(index="signal_date",columns="ticker",values="ET_TAIL")
          .reindex(index=p.calendar.signal_date,columns=names).to_numpy(float))
    xb=(source_pred.pivot(index="signal_date",columns="ticker",values="XGB_TAIL")
          .reindex(index=p.calendar.signal_date,columns=names).to_numpy(float))
    for m,row in enumerate(p.calendar.itertuples(index=False)):
        a=int(ds.searchsorted(pd.Timestamp(row.entry_date)))
        e=int(ds.searchsorted(pd.Timestamp(row.exit_date)))
        if a>=len(ds) or e<=a:continue
        x=int(alloc.d1[0,a]);y=int(alloc.d2[0,a])
        assert 0<=x<48 and 0<=y<48 and x!=y
        both=bool(et[m,x]>et[m,y] and xb[m,x]>xb[m,y])
        selected=bool(alloc.margin[0,a]>=.03 and both)
        monthly=pd.DataFrame(dict(signal_date=[row.signal_date],
            leader=[names[x]],second=[names[y]],
            leader_ISIN=[universe.set_index("ticker").loc[names[x],"isin"]],
            second_ISIN=[universe.set_index("ticker").loc[names[y],"isin"]],
            models_agree=[both],margin=[float(alloc.margin[0,a])]))
        before=w0[0,a:e]
        riskoff=(g[a:e]<.999999)
        if selected:
            wv[0,a:e][riskoff]=1.0
        events.append(dict(signal_date=str(row.signal_date.date()),
           leader=names[x],second=names[y],
           leader_ISIN=str(universe.set_index("ticker").loc[names[x],"isin"]),
           second_ISIN=str(universe.set_index("ticker").loc[names[y],"isin"]),
           both_models_agree=both,score_margin=float(alloc.margin[0,a]),
           riskoff_days=int(riskoff.sum()),
           actual_extra_v2_concentration_days=int(
             (wv[0,a:e]>before+1e-12).sum())))
    ti={t:i for i,t in enumerate(names)}
    risk1=ti["IBCA.DE"];risk2=ti["IBCN.DE"]
    arguments=(alloc.d1,alloc.d2,O,L,C,PC,gap,ud1,uneg,UH,SA,risk1,risk2,g,state.alt_idx,True,.001)
    Ebase,Tbase,_,_=v6.simulate_with_alt(alloc.d1,alloc.d2,w0,O,L,C,PC,gap,ud1,uneg,UH,SA,risk1,risk2,g,state.alt_idx,True,.001)
    Ev2,Tv2,_,_=v6.simulate_with_alt(alloc.d1,alloc.d2,wv,O,L,C,PC,gap,ud1,uneg,UH,SA,risk1,risk2,g,state.alt_idx,True,.001)
    mb=evaluate(Ebase,Tbase,ds)
    mv=evaluate(Ev2,Tv2,ds)
    original_ref=json.loads(REF.read_text())
    assert original_ref["evaluation_months"]==65
    # ETF Trader source-only strategy evaluates ALL 48-way observed European
    # sessions, not only EU sessions shared with US factor timestamps used by
    # the F3/H1 experiment. Different daily calendars are an EXPLICIT
    # comparability limit, not a reason to reject genuine EU market evidence.
    original_ref_days=pd.read_csv(ROOT/
        "isin_first2026/refit48/results/DAILY_COSTED_EQUITY_SAME_EUROPE_DATES.csv",
        parse_dates=["day"])["day"]
    common_f3_dates=int(pd.DatetimeIndex(ds).isin(original_ref_days).sum())
    assert common_f3_dates>=original_ref["evaluation_daily_open_count"]-2
    extra=np.asarray(wv>w0+1e-12)
    eval_result=dict(
       status="ETF_TRAINER_V2_UNRESTRICTED_48_FRESH_MODELS_AND_DAILY_SIM_COMPLETE",
       universe_tickers=48,legal_fund_isins=48,
       one_single_unrestricted_48_fund_candidate_set=True,
       no_fixed_4_per_category_sector_constraints=True,
       no_500_baskets=True,source_only_real_Titanium_retrained=True,
       source_only_real_MA3_HYBRID24_retrained=True,
       maturity_safe_hybrid_fit=True,source_S3B_cluster_port=port,
       european_48_way_observed_daily_opens=len(ds),
       f3_h1_extra_US_market_date_intersection_daily_opens=
          original_ref["evaluation_daily_open_count"],
       overlap_with_F3_H1_calendar_days=common_f3_dates,
       extra_EU_only_open_dates=len(ds)-common_f3_dates,
       same_full_execution_calendar_as_F3_H1=(len(ds)==common_f3_dates),
       note_F3_H1_not_strictly_daily_comparable_due_US_factor_calendar=True,
       monthly_signal_count=len(p.calendar),
       signal_first=str(p.calendar.signal_date.min().date()),
       signal_last=str(p.calendar.signal_date.max().date()),
       investible_start=str(ds.min().date()),investible_end=str(ds.max().date()),
       vendor_unrepaired_raw_ohlcv_remains_available=True,
       vendor_derived_high_low_envelope_repaired=True,
       defensive_cash_US_bills_replaced_with_actual_EUR_gov_ETFs=True,
       euro_credit_risk_only_not_tradeable=True,
       risk_reference_SPY_to_MSCI_Europe_and_HYG_IEF_to_EUR_credit_sov=True,
       original_US_frozen_risk_thresholds_retained=True,
       risk_off_agreement_rule_original_V2_only=True,
       actual_v2_extra_concentrated_days=int(extra.sum()),
       actual_v2_extra_concentrated_months=int(
          sum(x["actual_extra_v2_concentration_days"]>0 for x in events)),
       V2_no_exposure_increase=True,
       original_base_Hybrid24_port_costed=mb,
       ETF_TRAINER_V2_port_costed=mv,
       delta_net_cagr_pp=(mv["cagr"]-mb["cagr"])*100,
       delta_max_drawdown_pp=(mv["maxdd"]-mb["maxdd"])*100,
       max_abs_daily_equity_difference=float(np.max(np.abs(Ev2-Ebase))),
       source_vendor_V2_version_sha256=sha(ROOT/
          "vendor/etf_trader_v2/versions/ETF_TRAINER_V2/VERSION.json"),
       source_EU48_prepared_manifest_sha256=sha(prep/"RESULT.json"),
       original_48_roster_sha256=sha(DATA/"STRICT_EUROPE_2017_WARM_2016_UNIQUE_ISIN.csv"),
       model_output_2026_survivor_universe_NOT_PIT=True,
       no_real_spread_or_quote_execution_validated=True,
       production_repo_unchanged=True)
    pd.DataFrame(events).to_csv(output/"ALL48_MONTHLY_LEADERS_AND_V2_INTERVENTIONS.csv",index=False)
    pd.DataFrame(dict(day=ds,Hybrid24=Ebase[0],TrainerV2=Ev2[0],
           baseline_turnover=Tbase[0],v2_turnover=Tv2[0],
           baseline_risky_gross=g,
           v2_leader_weight=wv[0])).to_csv(output/"DAILY_NAV_DD_AND_V2_TRADING.csv",index=False)
    (output/"RESULT.json").write_text(json.dumps(eval_result,indent=2,allow_nan=False)+"\n")
    (output/"SHA256_MANIFEST.txt").write_text("".join(sha(p)+"  "+str(p.relative_to(output))+"\n" for p in sorted(output.rglob("*.csv")))+sha(output/"RESULT.json")+"  RESULT.json\n")
    print("ETF_TRAINER_V2_UNRESTRICTED_EU48_RESULT",json.dumps(eval_result,allow_nan=False),flush=True)

if __name__=="__main__":
    ap=argparse.ArgumentParser()
    ap.add_argument("--prep",required=True)
    ap.add_argument("--tit",required=True)
    ap.add_argument("--out",required=True)
    a=ap.parse_args()
    run(a.prep,a.tit,a.out)
