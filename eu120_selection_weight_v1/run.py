#!/usr/bin/env python3
"""Frozen EU120 OOS selector-vs-weight counterfactuals on original common-open V2."""
from __future__ import annotations
import argparse,hashlib,json,os,sys
from pathlib import Path
import numpy as np,pandas as pd

ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT),str(ROOT/"europe120/eu120_retrain"),str(ROOT/"vendor/etf_trader_v2/src")]
import run_eu120_retrain as eu
import replay_audited as au
from etf_trader.ma3 import producer
from etf_trader.source_only.raw_io import load_ticker_csv_folder
from eu120_compact_return_tail_v1.run import calculate_scores
from paper_ltr_v2.replay import sha

ARMS=(("H_H","H","H"),("R_R","R","R"),
      ("H_R","H","R"),("R_H","R","H"),
      ("H_HALF","H","HALF"),("R_HALF","R","HALF"))
EXPECTED={"H":dict(cagr=.07629973872693391,maxdd=-.3002630685516753,
                         sharpe=.5100544103155337),
          "R":dict(cagr=.12035027404841482,maxdd=-.34268662636227976,
                         sharpe=.701814245153649)}
def strict_npz_parity(actual,reference):
    with np.load(actual,allow_pickle=False) as a, np.load(reference,allow_pickle=False) as b:
        if set(b.files)!={"equity","turnover","dates"}:raise ValueError("Changed certified reference")
        for field in ("equity","turnover","dates"):
            x,y=a[field],b[field]
            if x.shape!=y.shape:raise ValueError("Different original daily field shape: "+field)
            if np.issubdtype(x.dtype,np.number):
                if not np.allclose(x,y,rtol=0,atol=1e-12,equal_nan=True):
                    raise ValueError("Certified 2026 EU120 path parity failure: "+field)
            elif not np.array_equal(x,y):
                raise ValueError("Certified EU120 daily timeline parity failure: "+field)

def replays(selector,weight_source,cal,ds,prices,refs,tickers,pm,selection_score,other_score):
    """Patch ONLY original producer allocation boundary; all downstream risk untouched."""
    select_score=np.where(np.isfinite(selection_score),selection_score,-1e6)
    borrowed_score=np.where(np.isfinite(other_score),other_score,-1e6)
    original_alloc=au.producer.allocations_from_score
    trace={}
    def interceptor(score,calendar,dates,basket,valid,*,continuous=True):
        selected=original_alloc(select_score,calendar,dates,basket,valid,continuous=continuous)
        if weight_source=="HALF":
            wk=np.full_like(selected.weight1,.5,dtype=float)
            mg=np.zeros_like(selected.margin,dtype=float)
        elif weight_source==selector:
            wk=selected.weight1.copy();mg=selected.margin.copy()
        else:
            borrowed=original_alloc(borrowed_score,calendar,dates,basket,valid,continuous=continuous)
            wk=borrowed.weight1.copy();mg=borrowed.margin.copy()
        if selected.d1.shape!=wk.shape or selected.d2.shape!=mg.shape:
            raise ValueError("Borrowed weight shape doesn't match chosen calendar")
        if not np.isfinite(wk).all() or np.any((wk<0)|(wk>1)):
            raise ValueError("Invalid borrowed portfolio weights")
        trace.update(d1=selected.d1.copy(),d2=selected.d2.copy(),
                     base_weight1=wk.copy(),margin=mg.copy())
        return producer.AllocationResult(
            d1=selected.d1.copy(),d2=selected.d2.copy(),weight1=wk,margin=mg)
    try:
        au.producer.allocations_from_score=interceptor
        # au.replay still recomputes risk transformer, agreement from *selector*,
        # post-agreement confidence weights, V6 alternative and actual returns.
        result,equity,turnover,dates=au.replay(select_score,pm,cal,prices,refs,tickers)
    finally:
        au.producer.allocations_from_score=original_alloc
    if not trace or equity.shape!=(len(dates),) or trace["d1"].shape[1]!=len(dates):
        raise ValueError("Missing original simulator allocation interception")
    if np.any((trace["d1"]<-1)|(trace["d1"]>=120)) or np.any(
        (trace["d2"]<-1)|(trace["d2"]>=120)):
        raise ValueError("Invalid selected EU120 ticker identifier")
    if np.any((trace["d1"]==-1)!=(trace["d2"]==-1)):
        raise ValueError("Unpaired unavailable ETF state")
    return result,equity,turnover,dates,trace

def original_reference_guard(source,cal,score_h,score_r,tickers):
    record=json.loads((source/"RESULT.json").read_text())
    if (record["status"]!="EU120_REFITTED_5_POLICY_COMMON_OPEN_COMPLETE"
        or record["completed_months"]!=112 or record["annual_fold_count"]!=10
        or not record["training_guard_ALL_PASS"]
        or record["universe_count"]!=120 or record["original149_candidate_overlap"]!=0):
        raise ValueError("Unverified refit archive")
    original={r["variant"]:r for r in record["economics"]}
    if len(original)!=5 or not all(r in original for r in ("H_ONLY","R_H")):
        raise ValueError("Missing frozen EU120 V2 baseline")
    if sha(source/"COMPACT_REFITTED.parquet")==sha(source/"HYBRID_REFITTED.parquet"):
        raise ValueError("Unexpected duplicate distinct learned source")
    if score_h.shape!=(len(cal),len(tickers)) or score_r.shape!=score_h.shape:
        raise ValueError("Unmatched original score matrices")
    for key,s in (("H_ONLY",score_h),("R_H",score_r)):
        if np.isfinite(s).sum(axis=1).min()<40:raise ValueError("Missing 120 ETF model coverage")
        if original[key]["signals"]!=len(cal) or original[key]["sessions"]!=2432:
            raise ValueError("Original EU120 execution support altered")
    return record,original

def main():
    p=argparse.ArgumentParser()
    for key in ("source","raw149","out"):p.add_argument("--"+key,required=True)
    a=p.parse_args();src=Path(a.source).resolve();out=Path(a.out).resolve()
    if out.exists() and any(out.iterdir()):raise ValueError("New output directory required")
    out.mkdir(parents=True)
    frozen=ROOT/"data/eu120"
    manifest=json.loads((frozen/"manifest.json").read_text())
    prov=json.loads((frozen/"PROVENANCE.json").read_text())
    original=json.loads((src/"RESULT.json").read_text())
    if (manifest.get("selected_count")!=120 or manifest.get("original149_overlap")!=0
        or prov.get("source_run")!=36597035280
        or prov.get("source_manifest_sha256")!=sha(frozen/"manifest.json")
        or original.get("source_frozen_manifest_sha256")!=sha(frozen/"manifest.json")):
        raise ValueError("Original EU120 frozen manifest/provenance mismatch")
    training=pd.read_csv(src/"TRAINING_AUDIT.csv")
    if len(training)!=10 or set(training.year)!=set(range(2017,2027)) or not training.lookahead_guard_PASS.all():
        raise ValueError("Missing 10 maturity-safe annual fits")
    for year in range(2017,2027):
        row=training.loc[training.year.eq(year)].iloc[0]
        if not (pd.Timestamp(row.latest_training_label_exit)<pd.Timestamp(year,1,1)
            and pd.Timestamp(row.ma3_latest_exit)<pd.Timestamp(year,1,1)):
            raise ValueError("Model fitted on unmatured futures")
    cp=pd.read_parquet(src/"COMPACT_REFITTED.parquet")
    hp=pd.read_parquet(src/"HYBRID_REFITTED.parquet")
    for x in (cp,hp):x["signal_date"]=pd.to_datetime(x.signal_date)
    if cp.duplicated(["signal_date","ticker"]).any() or hp.duplicated(["signal_date","ticker"]).any():
        raise ValueError("Duplicate trained OOS forecast rows")
    membership=pd.read_csv(ROOT/"europe120/eu120_retrain/UNIVERSE_120.csv")
    tickers=membership.ticker.astype(str).tolist()
    frozen_membership=pd.read_csv(frozen/"raw_ticker_csv/universe.csv")
    if len(tickers)!=120 or set(tickers)!=set(frozen_membership.ticker) or len(set(tickers))!=120:
        raise ValueError("Original frozen ETF selection changed")
    scratch=out/"working";raw120=scratch/"raw120";rawref=scratch/"rawref"
    os.environ["FROZEN_EU120_ROOT"]=str(frozen)
    os.environ["FROZEN_149_ROOT"]=str(Path(a.raw149).resolve())
    eu.download_folder(membership,raw120)
    eu.download_folder(pd.DataFrame(dict(ticker=eu.REF_TICKERS,
        macro_category=["REF_US","REF_CREDIT","REF_BOND","REF_CASH","REF_CASH"])),rawref)
    prices,_,_=load_ticker_csv_folder(raw120)
    refs,_,_=load_ticker_csv_folder(rawref)
    days=pd.DatetimeIndex(sorted(set(cp.signal_date)&set(hp.signal_date)))
    cal=au.common_calendar(pd.concat([prices["Open"][tickers],
        refs["Open"][eu.REF_TICKERS]],axis=1).sort_index(),days)
    if len(cal)!=112:raise ValueError("Original completed EU120 signal calendar mismatch")
    cp=cp[cp.signal_date.isin(cal.signal_date)].copy()
    hp=hp[hp.signal_date.isin(cal.signal_date)].copy()
    allscores,pm=calculate_scores(cp,hp,cal,tickers)
    sh=allscores["H_ONLY"];sr=allscores["R_H"]
    rec,reference=original_reference_guard(src,cal,sh,sr,tickers)
    results=[];yearlies=[];traces={};dates_by_arm={}
    for name,s,w in ARMS:
        score=sh if s=="H" else sr
        opposite=sr if w=="R" else sh
        outcome,equity,turnover,dates,trace=replays(
            s,w,cal,None,prices,refs,tickers,pm,score,opposite)
        if len(equity)!=2432 or len(dates)!=2432 or not np.isfinite(equity).all() or equity.min()<=0:
            raise ValueError("Uncertified same-day 2432 EU120 V2 execution")
        saved=out/f"{name}.npz"
        np.savez_compressed(saved,equity=equity,turnover=turnover,
            dates=dates.values,**trace)
        traces[name]=trace;dates_by_arm[name]=dates
        if name in ("H_H","R_R"):
            archive="H_ONLY" if name=="H_H" else "R_H"
            strict_npz_parity(saved,src/f"{archive}_EQUITY.npz")
            for field in ("cagr","maxdd","sharpe","terminal_equity","annualized_turnover"):
                if abs(outcome[field]-reference[archive][field])>1e-12:
                    raise ValueError("Failed prior full original120 path metric equality "+field)
        drift=np.diff(np.log(np.r_[1.,equity]))
        for year in range(2017,2027):
            mask=dates.year==year
            if mask.any():yearlies.append(dict(arm=name,year=year,
                sessions=int(mask.sum()),return_pct=100*float(np.expm1(drift[mask].sum()))))
        result=dict(arm=name,selector=s,weight_source=w,**outcome,
            trading_days=len(dates),active_days=int((trace["d1"][0]>=0).sum()),
            top1_fraction=float(np.mean(trace["d1"][0]>=0)),
            source_full_equity_sha256=sha(saved))
        results.append(result)
        print("EU120_MEDIATION_PATH "+json.dumps(result),flush=True)
    for name,_,_ in ARMS:
        if not dates_by_arm[name].equals(dates_by_arm["H_H"]):
            raise ValueError("Cross-policy EU120 daily calendar differs")
    for baseline,group in (("H_H",("H_R","H_HALF")),("R_R",("R_H","R_HALF"))):
        for name in group:
            for key in ("d1","d2"):
                if not np.array_equal(traces[name][key],traces[baseline][key]):
                    raise ValueError("Counterfactual accidentally changed ETF choice "+name)
    result_table=pd.DataFrame(results)
    result_table.to_csv(out/"ECONOMICS.csv",index=False)
    pd.DataFrame(yearlies).to_csv(out/"ANNUAL_RETURN.csv",index=False)
    result=dict(status="EU120_SELECTOR_WEIGHT_6_ARM_COMPLETE",
        source_training_RUN=39063271012,source_replay_RUN=39064123941,
        refitted_eu120_annual_models=80,refitted_here=0,
        source_manifest_sha256=sha(frozen/"manifest.json"),
        source_compact_prediction_sha256=sha(src/"COMPACT_REFITTED.parquet"),
        source_hybrid_prediction_sha256=sha(src/"HYBRID_REFITTED.parquet"),
        source_training_audit_sha256=sha(src/"TRAINING_AUDIT.csv"),
        protocol_sha256=sha(Path(__file__).with_name("PROTOCOL.md")),
        control_full_daily_equity_turnover_PARITY=True,
        completed_monthly_signals=112,common_open_daily_sessions=2432,
        retrospective_universe_selection_bias=True,
        rules_parameters_tuned=False,production_modified=False,
        original_simple_5050={x["variant"]:x["cagr"] for x in rec["fixed_5050"]},
        arms=results,annual_returns=yearlies,
        first_top1_selection_diff_day_fraction=float(np.mean(
            traces["H_H"]["d1"]!=traces["R_R"]["d1"])),
        first_top2_selection_diff_day_fraction=float(np.mean(
            traces["H_H"]["d2"]!=traces["R_R"]["d2"])),
        delta_cagr_pp={
            "selector_R_minus_H_given_weights_H":100*float(
                result_table.set_index("arm").loc["R_H","cagr"]-result_table.set_index("arm").loc["H_H","cagr"]),
            "selector_R_minus_H_given_weights_R":100*float(
                result_table.set_index("arm").loc["R_R","cagr"]-result_table.set_index("arm").loc["H_R","cagr"]),
            "weights_R_minus_H_given_selector_H":100*float(
                result_table.set_index("arm").loc["H_R","cagr"]-result_table.set_index("arm").loc["H_H","cagr"]),
            "weights_R_minus_H_given_selector_R":100*float(
                result_table.set_index("arm").loc["R_R","cagr"]-result_table.set_index("arm").loc["R_H","cagr"])})
    (out/"RESULT.json").write_text(json.dumps(result,indent=2,allow_nan=False)+"\n")
    print("EU120_6_ARM_ALL_CONTROLS_PASS "+json.dumps(result["delta_cagr_pp"]),flush=True)
if __name__=="__main__":main()
