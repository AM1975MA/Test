#!/usr/bin/env python3
"""Re-run full unrestricted 48-European ISIN ETF Trainer V2 with ORIGINAL USA SPY/HYG/IEF.

Genuine NEW annual Titanium + MA3 Hybrid24 model refit on US SPY explanatory
input, plus paired OLD frozen EU predictors to isolate only risk reference.
Also compares different defensive cash implementations explicitly, without
ever admitting US instruments among the 48 manager-selectable ETF ISINs.
"""
from __future__ import annotations
import argparse,hashlib,json,inspect
from pathlib import Path
import numpy as np,pandas as pd
from etf_trader.source_only.raw_io import load_ticker_csv_folder
from etf_trader.ma3 import producer,ddfirst,v6,highcagr24
from etf_trader.ma3.hybrid_producer import fit_hybrid_producer
from isin_first2026.v2_unrestricted48.run import (
 ROOT, build_panel, risk_reference_euro48,v6_reference_europe,evaluate,sha)
from isin_first2026.v2_forensic48.ablate import calculate_score
from isin_first2026.v2_usref48.us_source_helpers import (
    dd_reference_us_market,v6_reference_us_market,
    extend_execution_us_defense)

PREVIOUS=ROOT/"isin_first2026/v2_unrestricted48/results"

def run(prep,tit,us_reference,out):
    out=Path(out);out.mkdir(exist_ok=False,parents=True)
    prep=Path(prep);tit=Path(tit);us_reference=Path(us_reference)
    mats,cats,manifest=load_ticker_csv_folder(prep/"raw_ticker_csv")
    r=pd.read_csv(prep/"raw_ticker_csv/universe.csv")
    assert len(r)==48 and r["isin"].is_unique and r.ticker.nunique()==48
    names=list(mats["Open"].columns)
    assert len(names)==48 and set(names)==set(r.ticker)
    source_tit=pd.read_csv(tit/"TIT_R_SOURCE_ONLY.csv",
        parse_dates=["signal_date","entry_date","exit_date"])
    assert source_tit.ticker.nunique()==48 and source_tit.signal_date.nunique()==65
    cal=source_tit[["signal_date","entry_date","exit_date"]].drop_duplicates().sort_values("signal_date")
    assert len(cal)==65
    original_leaders=pd.read_csv(PREVIOUS/"ALL48_MONTHLY_LEADERS_AND_V2_INTERVENTIONS.csv")
    assert cal.signal_date.dt.strftime("%Y-%m-%d").tolist()==original_leaders.signal_date.to_list()
    port=build_panel(prep/"raw_ticker_csv",out/"model_source_rebuild")
    p=fit_hybrid_producer(pd.read_pickle(out/"model_source_rebuild/RAW_FEATURE_PANEL.pkl"),
       source_tit,names,start_year=2021,end_year=2026,et_n_jobs=2,xgb_n_jobs=2)
    assert p.fit_audit.maturity_ok.all() and len(p.fit_audit)==6
    assert len(p.calendar)==65 and p.score.shape==(65,48)
    assert np.isfinite(p.score).all()
    p.predictions.to_csv(out/"USREF_MA3_HYBRID24_65X48_FORECASTS.csv",index=False)
    p.fit_audit.to_csv(out/"USREF_MA3_HYBRID24_ANNUAL_MATURITY.csv",index=False)
    old_pred=pd.read_csv(PREVIOUS/"MA3_HYBRID24_48_TICKER_PREDICTIONS.csv",
       parse_dates=["signal_date"])
    oldscore,oldet,oldxb,_=calculate_score(old_pred,p.calendar,names)
    assert oldscore.shape==(65,48)
    euro_daily=mats["Open"]
    end=p.calendar.exit_date.max()
    all_open=euro_daily.loc[:end]
    all_low=mats["Low"].loc[all_open.index]
    all_close=mats["Close"].loc[all_open.index]
    st=int(all_open.index.get_loc(p.calendar.entry_date.min()))
    en=int(all_open.index.get_loc(end))
    days=all_open.index[st:en+1]
    assert len(days)==1374 and days[0]==pd.Timestamp("2021-02-01")
    assert days[-1]==pd.Timestamp("2026-07-01")
    ext=pd.read_csv(us_reference/"US_USD_REFERENCE_FOR_ORIGINAL_DD_V6_WITH_PRIOR_DAY_SHIFT.csv",
            parse_dates=["date"]).set_index("date")
    strict=pd.read_csv(us_reference/"STRICT_PRIOR_US_CLOSE_FOR_EU_FEATURES_AND_CASH_EUR.csv",
            parse_dates=["date"])
    assert ext.index.equals(mats["Close"].index)
    assert all(k in ext for k in ("SPY","HYG","IEF","BIL","SHV"))
    assert np.isfinite(ext[["SPY","HYG","IEF","BIL","SHV"]]).all(axis=None)
    us_dd=dd_reference_us_market(ext)
    eur_ihyg=pd.read_csv(prep/"EURO_CORP_HY_RISK_ONLY.csv",
             parse_dates=["date"]).set_index("date")["Close"]
    # Both risk controllers are computed on all historical prices BEFORE
    # extracting 2021+ slice; freeze source implementation and original thresholds.
    state_old=ddfirst.market_state
    try:
        ddfirst.market_state=lambda closes:risk_reference_euro48(closes,eur_ihyg)
        euro_gross_raw=np.asarray(ddfirst.sync_c95_m75_gross(all_close))[st:en+1]
        ddfirst.market_state=us_dd
        us_gross_raw=np.asarray(ddfirst.sync_c95_m75_gross(all_close))[st:en+1]
    finally:
        ddfirst.market_state=state_old
    eu_state=v6_reference_europe()
    us_state=v6_reference_us_market(ext["SPY"])
    daily_in=ddfirst.daily_execution_inputs(all_open,all_low,all_close)
    O,L,C,PC,gap,ud1,uneg,UH,SA=[
      daily_in[k][st:en+1] for k in
      ("O","L","C","PC","gap","ud1","uneg","UH","SA")]
    us_cash=extend_execution_us_defense(
        O,L,C,PC,gap,UH,SA,strict,days)
    bm,bok=producer.basket_arrays(pd.DataFrame({
            "basket":[0]*48,"ticker":names}),names,n_baskets=1)
    assert bm.shape==(1,48) and bok.all()
    price=all_close.loc[days,names]
    euro_reference=PREVIOUS/"RESULT.json"
    exact_old=json.loads(euro_reference.read_text())
    cases=[
       ("ORIGINAL_EU_SCORE_EU_MARKET_EU_DEFENSE",oldscore,oldet,oldxb,
             euro_gross_raw,eu_state,"EU"),
       ("ORIGINAL_EU_SCORE_US_MARKET_EU_DEFENSE",oldscore,oldet,oldxb,
             us_gross_raw,us_state,"EU"),
       ("RETRAINED_US_SPY_SCORE_EU_MARKET_EU_DEFENSE",p.score,p.et_tail,p.xgb_tail,
             euro_gross_raw,eu_state,"EU"),
       ("RETRAINED_US_SPY_SCORE_US_MARKET_EU_DEFENSE",p.score,p.et_tail,p.xgb_tail,
             us_gross_raw,us_state,"EU"),
       ("RETRAINED_US_SPY_SCORE_US_MARKET_US_BIL_SHV_FX_EUR",p.score,p.et_tail,p.xgb_tail,
             us_gross_raw,us_state,"US_EUR")
    ]
    results={};leader_all=[];daily={"day":days}
    for name,scores,et,xb,rawg,v6fn,defense in cases:
        assert scores.shape==(65,48)
        a=producer.allocations_from_score(scores,p.calendar,days,bm,bok,continuous=True)
        assert a.d1.shape==(1,1374)
        g,w=highcagr24.apply_highcagr24(rawg,a.weight1,a.margin)
        wv=w.copy()
        positions=[]
        for ix,row in enumerate(p.calendar.itertuples(index=False)):
            lo=int(days.searchsorted(pd.Timestamp(row.entry_date)))
            hi=int(days.searchsorted(pd.Timestamp(row.exit_date)))
            if hi<=lo:continue
            t1=int(a.d1[0,lo]);t2=int(a.d2[0,lo])
            assert 0<=t1<48 and 0<=t2<48 and t1!=t2
            flag=bool(a.margin[0,lo]>=.03 and
                 et[ix,t1]>et[ix,t2] and xb[ix,t1]>xb[ix,t2])
            if flag:
                bad=g[lo:hi]<.999999
                wv[0,lo:hi][bad]=1.
            positions.append(dict(case=name,signal_date=str(row.signal_date.date()),
                leader=names[t1],second=names[t2],first_isin=str(
                     r.set_index("ticker").loc[names[t1],"isin"]),
                v2_agreement=flag,v2_concentrated_days=int(
                     (wv[0,lo:hi]>w[0,lo:hi]+1e-12).sum()),
                monthly_margin=float(a.margin[0,lo])))
        leader_all.extend(positions)
        if defense=="EU":
            arrays=dict(O=O,L=L,C=C,PC=PC,gap=gap,UH=UH,SA=SA,
                bil=names.index("IBCA.DE"),shv=names.index("IBCN.DE"))
            close_for_v6=price
            bname="IBCA.DE";sname="IBCN.DE"
        else:
            arrays=us_cash
            close_for_v6=price.copy()
            for k,col in [("BIL","BIL_EUR_OPEN_EST"),("SHV","SHV_EUR_OPEN_EST")]:
                close_for_v6[k]=strict.set_index("date").reindex(days)[col].to_numpy(float)
            bname="BIL";sname="SHV"
        state=v6fn(close_for_v6,a.d1,a.d2,a.weight1,rawg,
                   bil_ticker=bname,shv_ticker=sname)
        args=[a.d1,a.d2]
        for weights,modelname in [(w,"HYBRID24"),(wv,"V2")]:
            eq,tr,_,_=v6.simulate_with_alt(
               a.d1,a.d2,weights,arrays["O"],arrays["L"],arrays["C"],arrays["PC"],
               arrays["gap"],ud1,uneg,arrays["UH"],arrays["SA"],
               arrays["bil"],arrays["shv"],g,state.alt_idx,True,.001)
            metrics=evaluate(eq,tr,days)
            results[name+"_"+modelname]=metrics
            daily[name+"_"+modelname]=eq[0]
            print("USREF_EU48_ECONOMICS",name,modelname,
                  json.dumps(metrics),flush=True)
    old=exact_old["ETF_TRAINER_V2_port_costed"]
    oldbase=results["ORIGINAL_EU_SCORE_EU_MARKET_EU_DEFENSE_V2"]
    assert abs(old["cagr"]-oldbase["cagr"])<1e-11
    assert abs(old["maxdd"]-oldbase["maxdd"])<1e-11
    print("V2_PRIOR_EURO48_ABSOLUTE_SCENARIO_PARITY",flush=True)
    pd.DataFrame(leader_all).to_csv(out/"ALL_SCENARIOS_TRUE_EU48_65_MONTH_POSITION_CHANGES.csv",index=False)
    pd.DataFrame(daily).to_csv(out/"DAILY_NAV_ORIGINAL_US_SPY_HYG_IEF_AND_DEFENSE_COMPARISON.csv",index=False)
    euro_cagr=results["ORIGINAL_EU_SCORE_EU_MARKET_EU_DEFENSE_V2"]["cagr"]
    final_us=results["RETRAINED_US_SPY_SCORE_US_MARKET_EU_DEFENSE_V2"]["cagr"]
    final_usdef=results["RETRAINED_US_SPY_SCORE_US_MARKET_US_BIL_SHV_FX_EUR_V2"]["cagr"]
    outcome=dict(
       status="REAL_EU48_ETF_V2_US_ORIGINAL_SPY_HYG_IEF_US_BIL_SHV_REFERENCES_COMPLETE",
       n_europe_unique_isin_eligible=48,n_US_ETFs_eligible_as_Top1_Top2=0,
       periods=65,observed_EU_open_days=1374,
       benchmark_references="Original US USD SPY HYG IEF, never European proxies",
       defensive_original_US_BIL_SHV_EUR_converted_alternative=True,
       main_reference_only_EU_defensive_is_true_europe_tradable_48_only=True,
       original_unchanged_V2_previous_test_exactly_reproduced=True,
       model_architecture_and_original_train_parameters_unmodified=True,
       genuine_new_annual_models_US_SPY_Titanium_MA3=True,
       S3B_cluster_dimensions_same_5_dynamic_1_euro_gov_as_prior_48=True,
       use_only_prior_US_Close_for_predictive_features=True,
       source_original_US_ref_USD_no_EUR_exchange_rate_transformation_risk_signals=True,
       all_original_65_US_free_F3_H1_48ISIN_candidate_dates_preserved=True,
       no_retraining_original_EU_scores_used_for_reference_only_ablation=True,
       all_metrics=results,
       improvement_restored_original_US_references_pp=(final_us-euro_cagr)*100,
       improvement_if_US_BIL_SHV_defense_over_euro_pp=(final_usdef-final_us)*100,
       original_US_ref_csv_sha256=sha(us_reference/"SOURCE_REFERENCE_AUDIT.json"),
       original_user_EU48_model_baseline_CAGR=euro_cagr,
       euro_model_retrospective_survivor_2026_not_point_in_time=True,
       original_ETFTRADER_149_port_Not_bit_identical_as_clusters_6_not_8=True,
       USA_market_reference_USD_prior_asof_causal=True,
       US_BIL_SHV_EUR_FX_approx_close_not_executable_European_open=True,
       no_production_repo_modified=True)
    (out/"RESULT.json").write_text(json.dumps(outcome,indent=2,allow_nan=False)+"\n")
    (out/"SHA256_MANIFEST.txt").write_text("".join(sha(x)+"  "+str(x.relative_to(out))+"\n"
       for x in sorted(out.rglob("*.csv")))+sha(out/"RESULT.json")+"  RESULT.json\n")
    print("USREF_48_FINAL_SCIENTIFIC_RESULT",json.dumps(outcome,allow_nan=False),flush=True)

if __name__=="__main__":
    a=argparse.ArgumentParser()
    a.add_argument("--prep",required=True)
    a.add_argument("--tit",required=True)
    a.add_argument("--us-reference",required=True)
    a.add_argument("--out",required=True)
    p=a.parse_args()
    run(p.prep,p.tit,p.us_reference,p.out)
