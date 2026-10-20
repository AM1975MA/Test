#!/usr/bin/env python3
"""Original fully-stacked ETF Trader V2 Stage19 risk/stop engine port to 48 EU ISINs.

The 2017-2026 USA31.758% was one unrestricted-149 *fully stacked source V2*
per 3 historical price vintages. This study replaces mistakenly used
MA3-only v6 simulator with original vendor/p45/v2_stage19_kernel.py
source_score_matrix, risk_gross_transform, confidence_weights,
simulate_arch, plus original SPY/HYG/IEF macro and BIL/SHV defense EUR marked.

European source 2021-26 frozen FULL Titanium+MA3 48 fits already certified in
run 39326985222. Additional 125F source Compact21 separately certified in run
39343219473, included as explicitly labeled optional rank-source diagnostic;
NEITHER model is trained on 2021-26 future returns in this replay.
"""
from __future__ import annotations
import argparse,importlib.util,json,hashlib
from pathlib import Path
import numpy as np,pandas as pd
from etf_trader.ma3 import producer,ddfirst
from etf_trader.source_only.raw_io import load_ticker_csv_folder
from isin_first2026.v2_usref48.us_source_helpers import (
    dd_reference_us_market,v6_reference_us_market,extend_execution_us_defense)
from isin_first2026.v2_usref48.original_us_references import asof_quotes
from isin_first2026.v2_unrestricted48.run import ROOT,sha
COMPLETE48=ROOT/"isin_first2026/v2_usref48/results"
ORIGINAL48=ROOT/"isin_first2026/v2_unrestricted48/results"
COMP125=ROOT/"isin_first2026/compact21_base48/results/FITTED_3SEED_ANNUAL/BASE_ORIGINAL_125F_XGB_65x48_TRUE_OOS_SCORES.csv"
SRC=ROOT/"vendor/p45/v2_stage19_kernel.py"
sp=importlib.util.spec_from_file_location("source_v2_stage19_unchanged",SRC)
stage19=importlib.util.module_from_spec(sp);sp.loader.exec_module(stage19)

def main(data,us,fx,out):
    out=Path(out);out.mkdir(parents=True,exist_ok=False)
    data=Path(data)
    matrices,cat,origin=load_ticker_csv_folder(data/"raw_ticker_csv")
    roster=pd.read_csv(data/"raw_ticker_csv/universe.csv")
    assert len(roster)==48 and roster["isin"].nunique()==48
    names=list(matrices["Open"].columns)
    assert len(names)==48 and set(names)==set(roster.ticker)
    sourcepred=pd.read_csv(COMPLETE48/"USREF_MA3_HYBRID24_65X48_FORECASTS.csv",parse_dates=["signal_date"])
    assert len(sourcepred)==65*48 and sourcepred.groupby("signal_date").ticker.nunique().eq(48).all()
    orig=pd.read_csv(ORIGINAL48/"ALL48_MONTHLY_LEADERS_AND_V2_INTERVENTIONS.csv",parse_dates=["signal_date"])
    assert len(orig)==65
    # Recreate the authentic 48-ETF same-calendar execution, source training
    # original MA3 predictions did not contain execution dates.
    common_days=matrices["Open"].index
    mend=pd.Series(common_days,index=common_days).groupby(common_days.to_period("M")).max()
    signals=pd.DatetimeIndex(sorted(sourcepred.signal_date.unique()))
    assert signals.equals(pd.DatetimeIndex(orig.signal_date))
    rec=[]
    for dt in signals:
        pos=int(common_days.get_loc(dt))
        month=int(mend.searchsorted(dt))+1
        nxt=mend.iloc[month];nextpos=int(common_days.get_loc(nxt))+1
        assert nextpos<len(common_days)
        rec.append(dict(signal_date=dt,entry_date=common_days[pos+1],
                        exit_date=common_days[nextpos]))
    cal=pd.DataFrame(rec)
    assert len(cal)==65
    assert cal.entry_date.iloc[0]==pd.Timestamp("2021-02-01")
    assert cal.exit_date.iloc[-1]==pd.Timestamp("2026-07-01")
    Odf=matrices["Open"].loc[:cal.exit_date.max()][names]
    Ldf=matrices["Low"].reindex(index=Odf.index,columns=names)
    Cdf=matrices["Close"].reindex(index=Odf.index,columns=names)
    st=int(Odf.index.get_loc(cal.entry_date.iloc[0]))
    en=int(Odf.index.get_loc(cal.exit_date.iloc[-1]))
    days=Odf.index[st:en+1]
    assert len(days)==1374
    # Exact USD original reference data from source 149, no alternative EU
    # substitutes for SPY HYG IEF, strict prior close for EU opening marks.
    asof_quotes(us,matrices["Open"].index,fx,out/"US_REFERENCE_AUDIT")
    inclusive=pd.read_csv(out/"US_REFERENCE_AUDIT/US_USD_REFERENCE_FOR_ORIGINAL_DD_V6_WITH_PRIOR_DAY_SHIFT.csv",
                          parse_dates=["date"]).set_index("date")
    strict=pd.read_csv(out/"US_REFERENCE_AUDIT/STRICT_PRIOR_US_CLOSE_FOR_EU_FEATURES_AND_CASH_EUR.csv",
                          parse_dates=["date"])
    assert inclusive.index.equals(matrices["Close"].index)
    usd_risk=dd_reference_us_market(inclusive)
    original_market=ddfirst.market_state
    try:
        ddfirst.market_state=usd_risk
        ddgross=np.asarray(ddfirst.sync_c95_m75_gross(Cdf),float)[st:en+1]
    finally:
        ddfirst.market_state=original_market
    g_risk=stage19.risk_gross_transform(ddgross)
    original_us_v6=v6_reference_us_market(inclusive["SPY"])
    ex=ddfirst.daily_execution_inputs(Odf,Ldf,Cdf)
    original={k:ex[k][st:en+1] for k in (
      "O","L","C","PC","gap","ud1","uneg","UH","SA")}
    cand50=extend_execution_us_defense(
       original["O"],original["L"],original["C"],original["PC"],
       original["gap"],original["UH"],original["SA"],strict,days)
    bm=np.arange(48,dtype=np.int32)[None,:]
    bok=np.ones_like(bm,dtype=bool)
    native=pd.read_csv(COMP125,parse_dates=["signal_date"])
    assert len(native)==3120 and native.groupby("signal_date").ticker.nunique().eq(48).all()
    true_comp=native.pivot(index="signal_date",columns="ticker",values="pred").reindex(
       index=signals,columns=names)
    assert true_comp.notna().all(axis=None)
    comp_pct=true_comp.rank(axis=1,pct=True,method="average")
    assert np.isfinite(comp_pct.to_numpy(float)).all()
    assert true_comp.shape==(65,48)
    original_df=sourcepred.rename(columns={"ET_TAIL":"ET_RANK","XGB_TAIL":"XGB_RANK"})
    assert set(["signal_date","ticker","BASE","ET_RANK","XGB_RANK"])<=set(original_df)
    augmented=original_df.merge(
      comp_pct.stack().rename("COMP125_PCT").reset_index().rename(
          columns={"level_0":"signal_date","level_1":"ticker"}),
      on=["signal_date","ticker"],how="left",validate="one_to_one")
    assert augmented.COMP125_PCT.notna().all()
    # Refit of original EU-only 125F Compact is deliberately a second, clearly
    # labeled injection into ORIGINAL Stage19 full architecture. Original
    # prior US market factor remains from original source 48 fit.
    systems={
      "MA3_US_SPY_FITTED_AND_ORIGINAL_V2_FULL_STAGE19":original_df,
      "125F_COMPACT21_SOURCE_REPLACES_MA3_BASE_IN_ORIGINAL_STAGE19":
           augmented.assign(BASE=augmented.COMP125_PCT)
    }
    results={};daily={"day":days};positions=[]
    for name,forecast in systems.items():
        baseforecast=forecast[["signal_date","ticker","BASE","ET_RANK","XGB_RANK"]].copy()
        assert baseforecast.groupby("signal_date").ticker.nunique().eq(48).all()
        score=stage19.score_matrix(baseforecast,cal,names)
        pm=stage19.pred_matrices(baseforecast,cal,names)
        assert score.shape==(65,48) and np.isfinite(score).all()
        alloc=producer.allocations_from_score(score,cal,days,bm,bok,continuous=True)
        assert alloc.d1.shape==(1,1374) and alloc.d1.max()<48 and alloc.d2.max()<48
        # V6 original needs the *reference names* BIL/SHV visible but they
        # are never among the 48 candidate columns indexed by ranker.
        stateclose=Cdf.loc[days,names].copy()
        priordaily=strict.set_index("date").reindex(days)
        stateclose["BIL"]=priordaily["BIL_EUR_OPEN_EST"].to_numpy(float)
        stateclose["SHV"]=priordaily["SHV_EUR_OPEN_EST"].to_numpy(float)
        source_state=original_us_v6(stateclose,alloc.d1,alloc.d2,alloc.weight1,ddgross,
                   bil_ticker="BIL",shv_ticker="SHV")
        assert np.all((source_state.alt_idx<48)|(source_state.alt_idx<0)),(
            "Non-EU alternative must never be promoted into 48 European candidate ALT")
        _,agree,agreeall=stage19.daily_monthly_state(score,pm,cal,days,bm,bok)
        weights=stage19.confidence_weights(alloc,g_risk,agree,agreeall,
                  "current_plus_models_riskoff")
        # EXACT original BASE score-relative gross controller and stage19
        # original concentration. Do not call v6.simulate_with_alt at all.
        gross=np.tile(g_risk,(1,1))
        E,T,X,AW=stage19.simulate_arch(
           alloc.d1,alloc.d2,weights,
           cand50["O"],cand50["L"],cand50["C"],cand50["PC"],cand50["gap"],
           original["ud1"],original["uneg"],cand50["UH"],cand50["SA"],
           cand50["bil"],cand50["shv"],gross,g_risk,
           source_state.alt_idx,True,.001)
        assert E.shape==(1,1374) and np.isfinite(E).all() and (E>0).all()
        m=stage19.metrics(E,np.ones(len(days),bool))
        results[name]=dict(cagr=m["cagr"],maxdd=m["maxdd"],sharpe=m["sharpe"],
             terminal_nav=float(E[0,-1]),annual_turnover=float(T.mean()*252),
             risk_macro_SPY_HYG_IEF_USD=True,defensive_BIL_SHV_USD_in_EUR_mark=True,
             actual_real_months=65,original_stage19_score_included=True)
        daily[name]=E[0]
        for row in cal.itertuples(index=False):
            pos=int(days.searchsorted(row.entry_date))
            t1,t2=names[int(alloc.d1[0,pos])],names[int(alloc.d2[0,pos])]
            assert t1!=t2
            positions.append(dict(case=name,signal_date=str(row.signal_date.date()),
                    leader=t1,second=t2,
                    leader_isin=roster.set_index("ticker").loc[t1,"isin"],
                    top1_weight=float(weights[0,pos]),
                    gross=float(g_risk[pos])))
        print("CANONICAL_V2_SOURCE_STAGE19_EU48_CASE",name,json.dumps(results[name]),flush=True)
    pd.DataFrame(daily).to_csv(out/"ORIGINAL_V2_STAGE19_EU48_DAILY_NAV_COSTED.csv",index=False)
    pd.DataFrame(positions).to_csv(out/"ORIGINAL_V2_STAGE19_EU48_MONTHLY_LEADERS.csv",index=False)
    md=dict(status="EU48_REAL_ORIGINAL_FULL_V2_STAGE19_SOURCE_STACK_MATCHED_65_MONTHS",
        original_stage19_vendor_source_SHA256=sha(SRC),
        genuine_48_source_only_original_Titanium_and_MA3_USSPY_refit_archived=True,
        genuine_48_source_only_original_125feature_compact21_XGB_yearly_source_fit_archived=True,
        original_V2_full_stage19_not_LATER_V6_SIMPLIFIED=True,
        predictions_65x48_with_no_future_labels=True,
        portfolio_one_unrestricted_europe48=True,
        original_149_trading_system_CAGR_31P76_from_three_data_vintages_not_500_baskets=True,
        n_european_isins=48,n_tradeable_predictive_US_tickers=0,
        n_original_macro_reference_US_tickers=5,n_europe_sessions=1374,n_months=65,
        source_149_score_model_cannot_exactly_clone_on_48_ISIN=True,
        48_dynamic_cluster_original_149_7_dynamic_not_possible_with_41_equity=True,
        original_SPY_HYG_IEF_USD_risk=True,
        original_BIL_SHV_USD_cash_marked_as_EUR_with_last_prior_close_fx=True,
        original_BIL_SHV_cash_euro_open_quotes_NOT_real_broker_executable=True,
        staged_125F_compact21_override_is_EXPLICIT_DIAGNOSTIC_not_plain_canonical=True,
        original_EU_48_quote_49_HighLow_repairs_flag=True,
        no_outcome_optimisation_or_new_refits_during_test=True,
        2026_roster_survivorship_and_Yahoo_adjusted_backfilled_caveats=True,
        all_cases=results)
    (out/"RESULT.json").write_text(json.dumps(md,indent=2,allow_nan=False)+"\n")
    (out/"SHA256_MANIFEST.txt").write_text("".join(
       sha(p)+"  "+str(p.relative_to(out))+"\n"
       for p in sorted(out.rglob("*.csv")))+sha(out/"RESULT.json")+"  RESULT.json\n")
    print("EUROPE48_CANONICAL_SOURCE_STAGE19_COMPLETED",json.dumps(md),flush=True)
if __name__=="__main__":
    a=argparse.ArgumentParser()
    for arg in ["data","us","fx","out"]:a.add_argument("--"+arg,required=True)
    p=a.parse_args();main(p.data,p.us,p.fx,p.out)
