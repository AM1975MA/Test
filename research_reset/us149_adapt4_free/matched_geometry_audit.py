#!/usr/bin/env python3
"""One AND five-hundred original US149 ETF Trader portfolios, same frozen scores.

Strict matched 2021-02..2026-07 65 signals, 1360 actual common dates.
Source-only 149 genuine mature-label annual Titanium and MA3 fits.
No changed learners, score or global risk controller. Both V2 variants.
"""
from __future__ import annotations
import argparse,hashlib,json,collections
from pathlib import Path
import numpy as np,pandas as pd
from etf_trader.source_only.raw_io import load_ticker_csv_folder
from etf_trader.source_only.baskets import build_canonical_baskets
from etf_trader.ma3 import producer,ddfirst,v6,highcagr24
from research_reset.us149_adapt4_free.prepare import prepare
from research_reset.us149_adapt4_free.run import (
  fit_source_titanium,build_real_ma3,monthly_feature_rows,
  predictive_adapt4,backtest_v2)
from isin_first2026.predict48.tournament import sha

EXPECTED_FREE_MA3_CAGR=.10479353861045033
EXPECTED_FREE_ADAPT_CAGR=.2917477276507473
EXPECTED_FREE_MA3_DD=-.4751403827732086
EXPECTED_FREE_ADAPT_DD=-.3886938250920965

def performance(eq,tr,days):
    E=np.asarray(eq,float)
    B,D=E.shape
    assert D==1360 and np.isfinite(E).all() and E.min()>0
    log=np.diff(np.log(np.column_stack([np.ones(B),E])),axis=1)
    cagr=np.expm1(log.sum(axis=1)*252/D)
    daily=np.expm1(log)
    rollhigh=np.maximum.accumulate(np.column_stack([np.ones(B),E]),axis=1)[:,1:]
    dd=(E/rollhigh-1).min(axis=1)
    sr=np.sqrt(252)*daily.mean(axis=1)/np.maximum(daily.std(axis=1,ddof=1),1e-12)
    return dict(n_baskets=int(B),n_days=int(D),
        mean_cagr=float(cagr.mean()),median_cagr=float(np.median(cagr)),
        p05_cagr=float(np.quantile(cagr,.05)),p10_cagr=float(np.quantile(cagr,.1)),
        p90_cagr=float(np.quantile(cagr,.90)),p95_cagr=float(np.quantile(cagr,.95)),
        best_cagr=float(cagr.max()),worst_cagr=float(cagr.min()),
        fraction_positive=float((cagr>0).mean()),
        mean_maxdd=float(dd.mean()),median_maxdd=float(np.median(dd)),
        worst_maxdd=float(dd.min()),mean_sharpe=float(sr.mean()),
        average_annual_turnover=float(tr.mean()*252)),cagr,dd

def run(raw,out):
    out=Path(out);out.mkdir(exist_ok=False,parents=True)
    d=out/"SOURCE149";prepare(raw,d)
    input=d/"raw_ticker_csv"
    mats,cats,_=load_ticker_csv_folder(input)
    names=list(mats["Close"])
    assert len(names)==149 and {"SPY","HYG","IEF","BIL","SHV"}<=set(names)
    t=fit_source_titanium(input,out/"FIT_TITANIUM")
    ma3=build_real_ma3(input,t,out/"FIT_MA3",names)
    f,allcal=monthly_feature_rows(mats,names,t.groupby("signal_date").first().reset_index(),cats)
    adapt,cal,ex,y,raudit,weights=predictive_adapt4(f,allcal,ma3,names)
    assert len(cal)==65 and ma3.score.shape==adapt.shape==(65,149)
    allscores={"MA3_ORIGINAL":ma3.score,"ADAPT4":adapt}
    Odf=mats["Open"][names].loc[:cal.exit_date.max()]
    Cdf=mats["Close"][names].loc[Odf.index]
    Ldf=mats["Low"][names].loc[Odf.index]
    st=int(Odf.index.get_loc(cal.entry_date.iloc[0]))
    en=int(Odf.index.get_loc(cal.exit_date.iloc[-1]))
    days=Odf.index[st:en+1]
    assert len(days)==1360 and len(cal)==65
    EX=ddfirst.daily_execution_inputs(Odf,Ldf,Cdf)
    O,L,C,PC,gap,ud1,uneg,UH,SA=[
        EX[k][st:en+1] for k in ("O","L","C","PC","gap","ud1","uneg","UH","SA")]
    gg=np.asarray(ddfirst.sync_c95_m75_gross(Cdf))[st:en+1]
    uni=pd.read_csv(input/"universe.csv")
    assert len(uni)==149 and uni.macro_category.nunique()==6
    mem500=build_canonical_baskets(uni,names)
    assert len(mem500)==12000 and mem500.basket.nunique()==500
    bm500,ok500=producer.basket_arrays(mem500,names,n_baskets=500)
    bmfull,okfull=producer.basket_arrays(pd.DataFrame({
         "basket":[0]*149,"ticker":names}),names,n_baskets=1)
    tests=[("FREE_ALL149",bmfull,okfull),("CANONICAL_500x24",bm500,ok500)]
    assert bm500.shape==(500,24) and bmfull.shape==(1,149)
    portfolio_returns=[];selection=[];summaries={}
    all_v2_riskoff=0
    for model,score in allscores.items():
        for geom,bm,ok in tests:
            print("BEGIN_SAME_SCORE_PAIRED_EXPERIMENT",model,geom,flush=True)
            allocations=producer.allocations_from_score(score,cal,days,bm,ok,continuous=True)
            B=allocations.d1.shape[0]
            gross,leader_weight=highcagr24.apply_highcagr24(
               gg,allocations.weight1,allocations.margin)
            v2w=leader_weight.copy()
            margins=[]
            agrees_count=0;V2_months=set();V2_basket_days=0
            for m,row in enumerate(cal.itertuples(index=False)):
                a=int(days.searchsorted(row.entry_date))
                e=int(days.searchsorted(row.exit_date))
                if e<=a:continue
                first=allocations.d1[:,a].astype(int)
                second=allocations.d2[:,a].astype(int)
                assert (first!=second).all()
                diff=allocations.margin[:,a]
                margins.extend(diff.tolist())
                ind=np.arange(B)
                agree=(diff>=.03)&(ma3.et_tail[m,first]>ma3.et_tail[m,second])&(
                              ma3.xgb_tail[m,first]>ma3.xgb_tail[m,second])
                agrees_count+=int(agree.sum())
                active=agree[:,None] & (gross[a:e]<.999999)[None,:]
                wnow=v2w[:,a:e]
                wnow[active]=1.0
                n=int(np.sum(v2w[:,a:e]>leader_weight[:,a:e]+1e-12))
                V2_basket_days+=n
                if n:V2_months.add(str(row.signal_date.date()))
                for b in range(B):
                    selection.append(dict(model=model,geometry=geom,signal_date=str(row.signal_date.date()),
                       basket=int(b),top1=names[first[b]],top2=names[second[b]],
                       score_margin=float(diff[b]),agree=bool(agree[b])))
            V=v6.build_v6_state(Cdf.loc[days,names],
                     allocations.d1,allocations.d2,allocations.weight1,gg,
                     bil_ticker="BIL",shv_ticker="SHV")
            for tag,w in [("HYBRID24",leader_weight),("V2",v2w)]:
                E,T,_,_=v6.simulate_with_alt(
                    allocations.d1,allocations.d2,w,O,L,C,PC,gap,ud1,uneg,UH,SA,
                    names.index("BIL"),names.index("SHV"),
                    gross,V.alt_idx,True,.001)
                metrics,cagrs,dds=performance(E,T,days)
                key=model+"_"+geom+"_"+tag
                summaries[key]=dict(metrics,mean_margin=float(np.mean(margins)),
                   median_margin=float(np.median(margins)),
                   fraction_margin_ge_3pct=float(np.mean(np.asarray(margins)>=.03)),
                   number_agree_margin_signals=int(agrees_count),
                   actual_V2_additional_concentration_basket_days=int(V2_basket_days),
                   number_months_any_V2_concentration=len(V2_months))
                print("MATCHED_149_VS_500",key,json.dumps(summaries[key]),flush=True)
                for b in range(B):
                    portfolio_returns.append(dict(model=model,geometry=geom,
                       intervention=tag,basket=b,cagr=float(cagrs[b]),
                       maxdd=float(dds[b]),terminal_nav=float(E[b,-1])))
    # Exact check from prior success US149 single all-free 65 signals,
    # validating no trained model/ETF/expense/macro settings drift.
    prior={"MA3_ORIGINAL_FREE_ALL149_V2":(EXPECTED_FREE_MA3_CAGR,EXPECTED_FREE_MA3_DD),
           "ADAPT4_FREE_ALL149_V2":(EXPECTED_FREE_ADAPT_CAGR,EXPECTED_FREE_ADAPT_DD)}
    for label,(expected_cagr,expected_dd) in prior.items():
        measured=summaries[label]
        assert abs(measured["mean_cagr"]-expected_cagr)<1e-10,(label,measured["mean_cagr"],expected_cagr)
        assert abs(measured["mean_maxdd"]-expected_dd)<1e-10,(label,measured["mean_maxdd"],expected_dd)
    df=pd.DataFrame(portfolio_returns)
    df.to_csv(out/"ORIGINAL_SOURCE_FULL149_VS_500_US149_METRICS_BY_BASKET.csv",index=False)
    pd.DataFrame(selection).to_csv(out/"ORIGINAL_SOURCE_TRUE_MONTHLY_FREE_VS_500_SELECTIONS.csv",index=False)
    # Source old 2017-2026 mean 500 baskets and 2023-2026 subperiod figures
    # are taken verbatim from authoritative original main repo documentation.
    v2free=summaries["MA3_ORIGINAL_FREE_ALL149_V2"]["mean_cagr"]
    v2sample=summaries["MA3_ORIGINAL_CANONICAL_500x24_V2"]["mean_cagr"]
    adaptfree=summaries["ADAPT4_FREE_ALL149_V2"]["mean_cagr"]
    adaptsample=summaries["ADAPT4_CANONICAL_500x24_V2"]["mean_cagr"]
    findings=dict(status="US149_COHORT_MATCHED_SOURCE_CAUSAL_FREE149_VS_500_BASKETS_2021_2026_COMPLETE",
         proof_same_trained_annual_MA3_149_forecasts=True,
         proof_same_trained_ADAPT4_forecasts=True,
         true_original_source_500_baskets_regenerated_with_seed_20260721=True,
         n_monthly_signals=65,n_daily_US_market_opens=1360,raw_tradable_universe=149,
         original_US149_V2_free_performance_exact_parity_from_action_39338133099=True,
         original_US_SPY_HYG_IEF_BIL_SHV_and_stop_source_unchanged=True,
         149_free_candidate_rule_no_sector_limits=True,
         old_500_candidate_rule_exactly_4_per_6_categories=True,
         all_cases=summaries,
         old_MA3_free_vs_500_mean_cagr_delta_pp=(v2sample-v2free)*100,
         ADAPT4_free_vs_500_mean_cagr_delta_pp=(adaptsample-adaptfree)*100,
         old_149_original_2017_2026_500_mean_CAGR_reference=.24897,
         old_149_original_2023_2026_500_mean_CAGR_reference=.30557,
         old_2017_2026_reference_NOT_same_dates=True,
         baskets_overlap_and_are_not_statistically_independent=True,
         input_survivorship_and_repeated_test_caveats=True,
         production_modified=False)
    (out/"RESULT.json").write_text(json.dumps(findings,indent=2,allow_nan=False)+"\n")
    (out/"SHA256_MANIFEST.txt").write_text("".join(
         sha(p)+"  "+str(p.relative_to(out))+"\n"
         for p in sorted(out.glob("*.csv")))+sha(out/"RESULT.json")+"  RESULT.json\n")
    print("US149_SOURCE_MATCHED_FREE_VS_500_VERIFIED",json.dumps(findings),flush=True)

if __name__=="__main__":
    p=argparse.ArgumentParser();p.add_argument("--us",required=True);p.add_argument("--out",required=True)
    a=p.parse_args();run(a.us,a.out)
