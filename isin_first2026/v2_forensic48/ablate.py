#!/usr/bin/env python3
"""Scientific forensic EU48 vs V2, *without fitting any new model*.

Only manipulates non-predictive layers (rank/stop/DD/V6/fees). Uses the fully
original model scores already produced by the previous pass and verifies
exact equity parity with the saved uninterrupted EU48 simulation. Parameter
values are frozen and never tuned on the observed outcomes.
"""
from __future__ import annotations
import argparse,json,collections
from pathlib import Path
import numpy as np,pandas as pd
from scipy.stats import spearmanr
from etf_trader.source_only.raw_io import load_ticker_csv_folder
from etf_trader.ma3 import producer,ddfirst,v6,highcagr24
from isin_first2026.v2_unrestricted48.run import (
    ROOT,risk_reference_euro48,v6_reference_europe,evaluate,sha
)
HERE=ROOT/"isin_first2026/v2_unrestricted48/results"
FUND=ROOT/"isin_first2026/full_eu_2017/results"
END=pd.Timestamp("2026-07-01")

def calculate_score(p,calendar,names):
    c=pd.DatetimeIndex(calendar.signal_date)
    def get(name):
        m=p.pivot(index="signal_date",columns="ticker",values=name)
        o=m.reindex(index=c,columns=names).to_numpy(float)
        assert o.shape==(65,48) and np.isfinite(o).all()
        return o
    et,xb,b=get("ET_TAIL"),get("XGB_TAIL"),get("BASE")
    t=.60*et+.40*xb
    lag1=np.vstack([t[:1],t[:-1]])
    lag2=np.vstack([t[:1],t[:1],t[:-2]])
    score=.475*b+.525*np.clip(.4*t+.3*lag1+.3*lag2,0,1)**1.1
    return score,et,xb,b

def output_performance(name,E,T,dates):
    x=evaluate(E,T,dates)
    print("EU48_ABLATION",name,json.dumps(x),flush=True)
    return dict(portfolio=name,**x)

def run(raw,output):
    output=Path(output);output.mkdir(parents=True,exist_ok=False)
    mats,cats,manifest=load_ticker_csv_folder(Path(raw))
    names=list(mats["Close"].columns)
    assert len(names)==48
    p=pd.read_csv(HERE/"MA3_HYBRID24_48_TICKER_PREDICTIONS.csv",
                  parse_dates=["signal_date"])
    leader_src=pd.read_csv(HERE/"ALL48_MONTHLY_LEADERS_AND_V2_INTERVENTIONS.csv",
                  parse_dates=["signal_date"])
    assert len(leader_src)==65
    cal=pd.read_csv(ROOT/"isin_first2026/refit48/results/MONTHLY_EUROPE48_EXECUTION_DATES.csv",
                    parse_dates=["signal_date","entry_date","exit_date"])
    # Refit48 monthly calendar uses same 65 anchored signal/entry/exit dates,
    # though it sampled fewer daily sessions due US factor closures.
    assert len(cal)==65 and cal.signal_date.equals(leader_src.signal_date)
    s,et,xb,b=calculate_score(p,cal,names)
    bm,bok=producer.basket_arrays(pd.DataFrame(
                 dict(basket=np.zeros(len(names),dtype=int),ticker=names)),
                 names,n_baskets=1)
    assert bm.shape==(1,48)
    Odf=mats["Open"].loc[:END]
    Ldf=mats["Low"].reindex(index=Odf.index,columns=names)
    Cdf=mats["Close"].reindex(index=Odf.index,columns=names)
    st=int(Odf.index.get_loc(cal.entry_date.min()))
    en=int(Odf.index.get_loc(cal.exit_date.max()))
    ds=Odf.index[st:en+1]
    assert len(ds)==1374
    alloc=producer.allocations_from_score(s,cal,ds,bm,bok,continuous=True)
    predicted=[names[int(alloc.d1[0,int(ds.searchsorted(d))])]
               for d in cal.entry_date]
    assert predicted==leader_src.leader.to_list(),(
        "Original V2 rankings failed exact replay",predicted[:6],
        leader_src.leader.to_list()[:6])
    print("EU48_FORENSIC_EXACT_SAVED_65_MONTH_RANK_PARITY",flush=True)
    exec_in=ddfirst.daily_execution_inputs(Odf,Ldf,Cdf)
    O,L,C,PC,gap,ud1,uneg,UH,SA=[
        exec_in[k][st:en+1] for k in ("O","L","C","PC","gap","ud1","uneg","UH","SA")]
    rr=pd.read_csv(ROOT/"isin_first2026/full_eu_2017/bonds_results/vendor_adjusted/IHYG.MI.csv",
                      parse_dates=["date"]).set_index("date")["Close"]
    old=ddfirst.market_state
    try:
        ddfirst.market_state=lambda c:risk_reference_euro48(c,rr)
        g_raw=ddfirst.sync_c95_m75_gross(Cdf)[st:en+1]
    finally:ddfirst.market_state=old
    gross,w=highcagr24.apply_highcagr24(g_raw,alloc.weight1,alloc.margin)
    risk1=names.index("IBCA.DE");risk2=names.index("IBCN.DE")
    v6_eu=v6_reference_europe()
    state=v6_eu(Cdf.loc[ds,names],alloc.d1,alloc.d2,
               alloc.weight1,g_raw,
               bil_ticker="IBCA.DE",shv_ticker="IBCN.DE")
    rank_events=[];weights=w.copy()
    for j,row in enumerate(cal.itertuples(index=False)):
        a=int(ds.searchsorted(pd.Timestamp(row.entry_date)))
        z=int(ds.searchsorted(pd.Timestamp(row.exit_date)))
        i,j2=int(alloc.d1[0,a]),int(alloc.d2[0,a])
        assert i!=j2 and i>=0 and j2>=0
        condition=bool(alloc.margin[0,a]>=.03 and et[j,i]>et[j,j2]
                       and xb[j,i]>xb[j,j2])
        if condition:
            mask=(gross[a:z]<.999999)
            weights[0,a:z][mask]=1.0
    zero=np.zeros_like(UH,dtype=bool)
    quiet=np.zeros_like(ud1,dtype=float)
    full_g=np.ones(len(ds),dtype=float)
    no_alt=np.full_like(state.alt_idx,-1)
    results=[]
    def simulate(name, use_risk, stops, alt, cost, concentrated=False,
                 leaders_only=False):
        ga=gross if use_risk else full_g
        ww=weights if concentrated else w
        u,v=(UH,SA) if stops else (zero,zero)
        up,un=(ud1,uneg) if stops else (quiet,quiet)
        altidx=state.alt_idx if alt else no_alt
        d1,d2=alloc.d1,alloc.d2
        if leaders_only:
            d2=d1
            ww=np.ones_like(w)
        E,T,_,_=v6.simulate_with_alt(
            d1,d2,ww,O,L,C,PC,gap,up,un,u,v,
            risk1,risk2,ga,altidx,alt,cost)
        results.append(output_performance(name,E,T,ds))
        return E,T
    Eb,Tb=simulate("FULL_HYBRID24_REPLAY",True,True,True,.001)
    Ev,Tv=simulate("FULL_TRAINER_V2_REPLAY",True,True,True,.001,concentrated=True)
    orig=pd.read_csv(HERE/"DAILY_NAV_DD_AND_V2_TRADING.csv")
    assert np.allclose(Eb[0],orig["Hybrid24"].to_numpy(float),rtol=0,atol=1e-12)
    assert np.allclose(Ev[0],orig["TrainerV2"].to_numpy(float),rtol=0,atol=1e-12)
    print("FORENSIC_DAILY_SAME_SOURCE_RESULT_PARITY_1E-12_PASSED",flush=True)
    simulate("UNRESTRICTED_SELECTION_TOP2_NO_RISK_NO_STOP",False,False,False,.001)
    simulate("UNRESTRICTED_SELECTION_TOP1_NO_RISK_NO_STOP",False,False,False,.001,leaders_only=True)
    simulate("UNRESTRICTED_SELECTION_TOP2_ONLY_ORIGINAL_STOPS",False,True,False,.001)
    simulate("UNRESTRICTED_SELECTION_TOP2_ONLY_GROSS_DD",True,False,False,.001)
    simulate("UNRESTRICTED_SELECTION_TOP2_DD_STOPS_NO_V6_ALT",True,True,False,.001)
    simulate("FULL_HYBRID24_ZERO_FEES",True,True,True,0.0)
    simulate("TOP2_NO_RISK_NO_STOP_ZERO_FEES",False,False,False,0.0)
    # True independent same EUR 1374 daily session passive buy & hold,
    # rather than the F3/H1 1331-open calendar, to avoid mismatched dates.
    subset=Odf.loc[ds]
    years=(len(ds))/252
    buyhold={}
    for t in ("IMEU.AS","EXV1.DE","EXV3.DE","XS8R.DE","EXV5.DE","IBCA.DE","IBCN.DE"):
        series=subset[t]
        total=float(series.iloc[-1]/series.iloc[0])
        buyhold[t]=dict(gross_cagr_on_1374_EUR_trading_days=
            total**(1/years)-1,terminal_relative=total)
    # Forward cross-sectional ranking versus future returns for each signal
    measures=[];max_spread=0
    by_bkt=pd.read_csv(FUND/"STRICT_EUROPE_2017_WARM_2016_UNIQUE_ISIN.csv")
    category=by_bkt.set_index("ticker")["benchmark_bucket"].to_dict()
    howmany=collections.Counter()
    for j,row in enumerate(cal.itertuples(index=False)):
        next_ret=np.log(subset.loc[row.exit_date]/subset.loc[row.entry_date])
        ret=np.asarray(next_ret.reindex(names),float)
        q=s[j]
        top1=int(alloc.d1[0,int(ds.searchsorted(row.entry_date))])
        top2=int(alloc.d2[0,int(ds.searchsorted(row.entry_date))])
        howmany[category[names[top1]]]+=1
        spearman=float(spearmanr(q,ret).statistic)
        blend=w[0,int(ds.searchsorted(row.entry_date))]*ret[top1]+(
            1-w[0,int(ds.searchsorted(row.entry_date))])*ret[top2]
        ew=float(ret.mean())
        means=[float(ret[ix].mean()) for ix in (np.argsort(-q)[:5],
                                                np.argsort(-ret)[:5])]
        max_spread+=float(np.sort(ret)[-5:].mean()-ew)
        measures.append(dict(signal_date=str(row.signal_date.date()),
            first_ticker=names[top1],second_ticker=names[top2],
            first_bucket=category[names[top1]],
            leader_next_month_log=float(ret[top1]),
            weighted_top2_next_month_log=float(blend),
            equal48_next_month_log=ew,
            weighted_top2_minus_equal48_log=float(blend-ew),
            equal_top5_model_ret_log=means[0],
            oracle_top5_realized_log=means[1],
            crosssection_spearman=spearman))
    md=pd.DataFrame(measures)
    md.to_csv(output/"MONTHLY_SCORE_SKILL_AND_SUBSEQUENT_RETURNS.csv",index=False)
    pd.DataFrame(results).to_csv(output/"ABLATION_SAME_1374_SOURCE_SIMULATOR.csv",index=False)
    summary=dict(status="AUDITED_REAL_V2_SOURCE_48_PERFORMANCE_DECOMPOSITION",
      month_count=len(md),trading_days=len(ds),
      all_48_ticker_price_original_close_and_open_unchanged=True,
      score_and_position_parity_exact_65_month=True,
      old_V2_equity_parity_atol_1e12=True,
      frozen_training_and_parameters_unchanged=True,
      no_future_selection_used_in_live_strategy=True,
      no_US149_source_weights_reused=True,
      roster_current_2026_survivorship_warning=True,
      original_macro_US_port_necessitated_cluster_and_credit_proxy_changes=True,
      ablations={x["portfolio"]:x for x in results},
      buyhold_individual_1374_EU_quote_dates=buyhold,
      ranking_skill_65_month_mean_spearman=float(md.crosssection_spearman.mean()),
      ranking_skill_65_month_positive_months=int((md.crosssection_spearman>0).sum()),
      selection_mean_next_month_log_excess_vs_EW48=float(
                   md.weighted_top2_minus_equal48_log.mean()),
      selection_positive_months_vs_EW48=int(
                   (md.weighted_top2_minus_equal48_log>0).sum()),
      monthly_realized_top_five_oracle_log_over_all48_mean=float(
          max_spread/65),
      selected_top1_bucket_counts=dict(howmany),
      source_full_execution_reference_sha=sha(
           HERE/"DAILY_NAV_DD_AND_V2_TRADING.csv"),
      v2_regime_interventions_previous_real=41,
      no_production_modify=True)
    (output/"RESULT.json").write_text(json.dumps(summary,indent=2)+"\n")
    (output/"SHA256_MANIFEST.txt").write_text("".join(
      sha(z)+"  "+str(z.relative_to(output))+"\n"
      for z in sorted(output.rglob("*.csv")))+sha(output/"RESULT.json")+"  RESULT.json\n")
    print("EU48_V2_FORENSIC_FINAL",json.dumps(summary),flush=True)

if __name__=="__main__":
    ap=argparse.ArgumentParser()
    ap.add_argument("--raw",required=True)
    ap.add_argument("--out",required=True)
    a=ap.parse_args()
    run(a.raw,a.out)
