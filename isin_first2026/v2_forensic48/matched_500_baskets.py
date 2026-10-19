#!/usr/bin/env python3
"""Actual Europe 48 trained scores: 500 original canonical balanced baskets vs unrestricted full48.

Counterfactual solves ONE difference in scientific comparisons with USA149:
original US V2 24.897% historic CAGR is MEAN of 500 distinct 24-fund basket
annualized returns, not single all149 unrestricted portfolio. Frozen Europe
scores, daily quote execution, risk parameters and 65 monthly windows unchanged.
This side experiment is comparative, not the user's requested 'free' strategy.
"""
from __future__ import annotations
import argparse,json,collections
from pathlib import Path
import numpy as np,pandas as pd
from etf_trader.source_only.raw_io import load_ticker_csv_folder
from etf_trader.source_only.baskets import build_canonical_baskets
from etf_trader.ma3 import producer,ddfirst,v6,highcagr24
from isin_first2026.v2_unrestricted48.run import (
 ROOT,risk_reference_euro48,v6_reference_europe,sha
)
from isin_first2026.v2_forensic48.ablate import calculate_score
BASE=ROOT/"isin_first2026/v2_unrestricted48/results"

def calc_metrics(E,T,ds):
    lr=np.diff(np.log(np.column_stack([np.ones(E.shape[0]),E])),axis=1)
    gain=np.expm1(lr.sum(axis=1)*252/lr.shape[1])
    r=np.expm1(lr);means=r.mean(axis=1)
    sd=r.std(axis=1,ddof=1)
    sharpe=np.divide(means*np.sqrt(252),sd,out=np.zeros_like(sd),where=sd>0)
    peak=np.maximum.accumulate(np.column_stack([np.ones(E.shape[0]),E]),axis=1)[:,1:]
    draw=(E/peak-1).min(axis=1)
    return dict(baskets=int(E.shape[0]),n_days=len(ds),
        mean_cagr=float(gain.mean()),median_cagr=float(np.median(gain)),
        p05_cagr=float(np.quantile(gain,.05)),p10_cagr=float(np.quantile(gain,.1)),
        max_cagr=float(gain.max()),min_cagr=float(gain.min()),
        mean_maxdd=float(draw.mean()),worst_basket_maxdd=float(draw.min()),
        mean_sharpe=float(sharpe.mean()),
        percentage_cagr_positive=float((gain>0).mean()*100),
        mean_turnover_ann=float(T.mean()*252)),gain,draw

def run(raw,out):
    out=Path(out);out.mkdir(parents=True,exist_ok=False)
    mats,categories,source_info=load_ticker_csv_folder(Path(raw))
    names=list(mats["Open"].columns)
    assert len(names)==48
    roster=pd.read_csv(Path(raw)/"universe.csv")
    assert len(roster)==48 and roster["isin"].nunique()==48
    pred=pd.read_csv(BASE/"MA3_HYBRID24_48_TICKER_PREDICTIONS.csv",parse_dates=["signal_date"])
    sigs=pd.DatetimeIndex(sorted(pred.signal_date.unique()))
    days=mats["Close"].index
    mend=pd.DatetimeIndex(pd.Series(days,index=days).groupby(days.to_period("M")).max().values)
    rows=[]
    for sd in sigs:
        cur=int(days.get_loc(sd));pos=int(mend.searchsorted(sd))+1
        nxt=mend[pos];ex=int(days.get_loc(nxt))+1
        rows.append(dict(signal_date=sd,entry_date=days[cur+1],exit_date=days[ex]))
    cal=pd.DataFrame(rows)
    assert len(cal)==65
    score,et,xb,base=calculate_score(pred,cal,names)
    mem=build_canonical_baskets(roster,names)
    # The authentic 500 x 24 membership generator records basket and ticker,
    # not the originating category; rejoin the immutable validated 48 roster.
    mem=mem.merge(roster[["ticker","macro_category"]],
                  on="ticker",how="left",validate="many_to_one")
    assert mem.macro_category.notna().all()
    assert len(mem)==12000 and mem.basket.nunique()==500
    assert mem.groupby("basket").ticker.nunique().eq(24).all()
    for b,g in mem.groupby("basket"):
        assert len(g.macro_category.value_counts())==6
        assert (g.macro_category.value_counts()==4).all()
    bm,bok=producer.basket_arrays(mem,names,n_baskets=500)
    assert bm.shape==(500,24)
    Odf=mats["Open"].loc[:cal.exit_date.max()]
    Ldf=mats["Low"].reindex(index=Odf.index,columns=names)
    Cdf=mats["Close"].reindex(index=Odf.index,columns=names)
    st=int(Odf.index.get_loc(cal.entry_date.iloc[0]))
    en=int(Odf.index.get_loc(cal.exit_date.iloc[-1]))
    ds=Odf.index[st:en+1]
    assert len(ds)==1374
    exe=ddfirst.daily_execution_inputs(Odf,Ldf,Cdf)
    O,L,C,PC,gap,ud1,uneg,UH,SA=[
      exe[k][st:en+1] for k in ("O","L","C","PC","gap","ud1","uneg","UH","SA")]
    highyield=pd.read_csv(ROOT/
      "isin_first2026/full_eu_2017/bonds_results/vendor_adjusted/IHYG.MI.csv",
      parse_dates=["date"]).set_index("date")["Close"]
    old=ddfirst.market_state
    try:
        ddfirst.market_state=lambda c:risk_reference_euro48(c,highyield)
        raw_gross=ddfirst.sync_c95_m75_gross(Cdf)[st:en+1]
    finally:ddfirst.market_state=old
    picks=producer.allocations_from_score(score,cal,ds,bm,bok,continuous=True)
    assert picks.d1.shape==(500,1374)
    alt=v6_reference_europe()(Cdf.loc[ds,names],
         picks.d1,picks.d2,picks.weight1,raw_gross,
         bil_ticker="IBCA.DE",shv_ticker="IBCN.DE")
    gross,w0=highcagr24.apply_highcagr24(raw_gross,picks.weight1,picks.margin)
    wv=w0.copy();v2changes=0;months=set()
    for m,row in enumerate(cal.itertuples(index=False)):
        a=int(ds.searchsorted(pd.Timestamp(row.entry_date)))
        b=int(ds.searchsorted(pd.Timestamp(row.exit_date)))
        idx1=picks.d1[:,a].astype(int)
        idx2=picks.d2[:,a].astype(int)
        assert np.all(idx1!=idx2) and idx1.min()>=0 and idx2.min()>=0
        es=np.arange(len(idx1))
        agrees=(picks.margin[:,a]>=.03)&(et[m,idx1]>et[m,idx2])&(
            xb[m,idx1]>xb[m,idx2])
        off=(gross[a:b]<.999999)[None,:]
        expand=agrees[:,None]&off
        wv[:,a:b][expand]=1.0
        n=int((wv[:,a:b]>w0[:,a:b]+1e-12).sum())
        v2changes+=n
        if n:months.add(str(row.signal_date.date()))
    ti={t:i for i,t in enumerate(names)}
    args=(picks.d1,picks.d2,O,L,C,PC,gap,ud1,uneg,UH,SA,
          ti["IBCA.DE"],ti["IBCN.DE"],gross,alt.alt_idx,True,.001)
    E0,T0,_,_=v6.simulate_with_alt(
        picks.d1,picks.d2,w0,O,L,C,PC,gap,ud1,uneg,UH,SA,
        ti["IBCA.DE"],ti["IBCN.DE"],gross,alt.alt_idx,True,.001)
    E1,T1,_,_=v6.simulate_with_alt(
        picks.d1,picks.d2,wv,O,L,C,PC,gap,ud1,uneg,UH,SA,
        ti["IBCA.DE"],ti["IBCN.DE"],gross,alt.alt_idx,True,.001)
    m0,c0,dd0=calc_metrics(E0,T0,ds)
    m1,c1,dd1=calc_metrics(E1,T1,ds)
    base_ref=json.loads((BASE/"RESULT.json").read_text())
    assert base_ref["universe_tickers"]==48 and base_ref["one_single_unrestricted_48_fund_candidate_set"]
    report=dict(status="EU48_500_BALANCED_24_VS_SINGLE_48_UNRESTRICTED_PARITY_STYLE_CONTROL",
        original_US_500_basket_metric_is_mean_basket_CAGR=True,
        European_trained_model_predictions_unchanged=True,
        Europe_price_and_risk_source_same_as_unrestricted_48=True,
        period_equal_65_signals_and_1374_EU_actual_open_dates=True,
        balanced_500_pockets_each_24_by_6categories4_each=True,
        trained_Europe48_rankings_and_hyperparams_never_refitted=True,
        controls_single_unrestricted48={
          "Hybrid24":base_ref["original_base_Hybrid24_port_costed"],
          "TrainerV2":base_ref["ETF_TRAINER_V2_port_costed"]},
        balanced_500_Hybrid24=m0,balanced_500_V2=m1,
        V2_vs_baseline_balanced_delta_mean_cagr_pp=(m1["mean_cagr"]-m0["mean_cagr"])*100,
        balanced_V2_baskets_improved_pct=float(np.mean(c1>c0)*100),
        V2_extra_concentration_basket_days=v2changes,
        number_months_any_balanced_basket_V2_changed=len(months),
        residual_interpretation="Even same 500 balanced 24-ETF crosssection carries Europe-specific returns; cannot claim US strategy generalizes if returns remain low",
        basket_cagr_is_not_CAGR_of_single_pooled_tradable_portfolio=True,
        user_requested_full_48_unrestricted_strategy_remains_the_primary_test=True,
        no_production_changes=True)
    pd.DataFrame(dict(basket=np.arange(500),cagr_baseline=c0,cagr_v2=c1,
      dd_baseline=dd0,dd_v2=dd1)).to_csv(out/"EU48_500_MATCHED_BASKETS_METRICS.csv",index=False)
    (out/"RESULT.json").write_text(json.dumps(report,indent=2)+"\n")
    (out/"SHA256_MANIFEST.txt").write_text("".join(
        sha(p)+"  "+str(p.relative_to(out))+"\n"
        for p in sorted(out.rglob("*.csv")))+sha(out/"RESULT.json")+"  RESULT.json\n")
    print("EUROPE48_MATCHED_500_BASKET_EXPERIMENT",json.dumps(report),flush=True)

if __name__=="__main__":
    ap=argparse.ArgumentParser()
    ap.add_argument("--raw",required=True)
    ap.add_argument("--out",required=True)
    a=ap.parse_args()
    run(a.raw,a.out)
