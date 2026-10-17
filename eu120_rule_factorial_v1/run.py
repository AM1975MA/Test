#!/usr/bin/env python3
"""EU120 16-arm allocation rule factorial: raw weight × margin gate × ET/XGB agreement."""
from __future__ import annotations
import argparse,json,os,sys
from pathlib import Path
import numpy as np
import pandas as pd

ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT),str(ROOT/"europe120/eu120_retrain"),
               str(ROOT/"vendor/etf_trader_v2/src")]
import run_eu120_retrain as eu
import replay_audited as au
from etf_trader.ma3 import producer
from etf_trader.source_only.raw_io import load_ticker_csv_folder
from eu120_compact_return_tail_v1.run import calculate_scores
from eu120_selection_weight_v1.run import original_reference_guard,strict_npz_parity
from paper_ltr_v2.replay import sha

ARMS=[(s,w,m,a) for s in ("H","R") for w in ("D","F")
      for m in (0,1) for a in (0,1)]
def label(s,w,m,a):return f"{s}_{w}_M{m}_A{a}"

def rule_replay(score,pm,calendar,candidates,refs,tickers,weight_mode,margin_gate,agreement):
    """Every invocation calls original audited EU120 daily-risk portfolio simulator."""
    orig_alloc=au.producer.allocations_from_score
    orig_agree=au.m.daily_state
    orig_conf=au.m.conf_weights
    trace={}
    def allocations(x,cal,dates,basket,valid,*,continuous=True):
        native=orig_alloc(x,cal,dates,basket,valid,continuous=continuous)
        w=(native.weight1.copy() if weight_mode=="D" else
           np.full_like(native.weight1,0.5,dtype=float))
        m=(native.margin.copy() if margin_gate else
           np.zeros_like(native.margin,dtype=float))
        trace["d1"]=native.d1.copy()
        trace["d2"]=native.d2.copy()
        trace["native_weight"]=native.weight1.copy()
        trace["native_margin"]=native.margin.copy()
        trace["raw_weight"]=w.copy()
        trace["fed_margin"]=m.copy()
        if not np.isfinite(w).all() or not np.isfinite(m).all():
            raise ValueError("Nonfinite EU120 intervention fields")
        return producer.AllocationResult(d1=native.d1,d2=native.d2,
                                          weight1=w,margin=m)
    def model_agreement(x,pm0,cal,dates,basket,valid):
        agreed=orig_agree(x,pm0,cal,dates,basket,valid)
        trace["native_agreement"]=agreed.copy()
        return agreed if agreement else np.zeros_like(agreed,dtype=bool)
    def confidences(base,g,agree):
        new=orig_conf(base,g,agree)
        if new.shape!=base.weight1.shape or not np.isfinite(new).all():
            raise ValueError("Invalid original confidence rule result")
        trace["post_conf_weight"]=new.copy()
        trace["market_risk"]=np.asarray(g,float).copy()
        trace["applied_agreement"]=agree.copy()
        return new
    try:
        au.producer.allocations_from_score=allocations
        au.m.daily_state=model_agreement
        au.m.conf_weights=confidences
        result,equity,turnover,dates=au.replay(score,pm,calendar,candidates,refs,tickers)
    finally:
        au.producer.allocations_from_score=orig_alloc
        au.m.daily_state=orig_agree
        au.m.conf_weights=orig_conf
    if len(dates)!=2432 or equity.shape!=(2432,) or len(trace)!=10:
        raise ValueError("Original EU120 daily simulator not fully intercepted")
    risk=trace["market_risk"][None,:]
    orig_margin=trace["native_margin"]
    orig_agreement=trace["native_agreement"]
    fed_margin=trace["fed_margin"]
    active=(trace["d1"]>=0)
    if int(active.sum())<2000:raise ValueError("Unusually little invested time")
    # Margin boost in risk-on; gated boost in risk-off, never confuse the two.
    threshold=float(au.m.highcagr24.TOP1_MARGIN)
    boost=active&(trace["post_conf_weight"]>trace["raw_weight"]+1e-12)
    trigger_on=active&(risk>=.999)&(fed_margin>=threshold)
    trigger_off=active&(risk<.999)&(fed_margin>=threshold)&trace["applied_agreement"]
    if not np.array_equal(boost,(trigger_on|trigger_off)&(trace["raw_weight"]<1.0-1e-12)):
        raise ValueError("Confidence boost not explained by canonical triggers")
    trace["boost_count"]=int(boost.sum())
    trace["risk_on_trigger_count"]=int(trigger_on.sum())
    trace["risk_off_trigger_count"]=int(trigger_off.sum())
    trace["market_risk_off_days"]=int((active&(risk<.999)).sum())
    trace["native_agreement_risk_off_days"]=int(
        (active&(risk<.999)&orig_agreement).sum())
    trace["native_margin_threshold_days"]=int(
        (active&(orig_margin>=threshold)).sum())
    trace["mean_raw_first_weight"]=float(trace["raw_weight"][active].mean())
    trace["mean_final_first_weight"]=float(trace["post_conf_weight"][active].mean())
    trace["max_daily_first_weight_change"]=float(np.max(np.abs(
        trace["post_conf_weight"]-trace["raw_weight"])))
    return result,equity,turnover,dates,trace

def main():
    p=argparse.ArgumentParser()
    for field in ("source","prior-six","raw149","out"):
        p.add_argument("--"+field,required=True)
    args=p.parse_args()
    source=Path(args.source).resolve();prior=Path(args.prior_six).resolve()
    out=Path(args.out).resolve()
    if out.exists() and any(out.iterdir()):raise ValueError("Refuse to overwrite prior research output")
    out.mkdir(parents=True)
    frozen=ROOT/"data/eu120"
    manifest=json.loads((frozen/"manifest.json").read_text())
    provenance=json.loads((frozen/"PROVENANCE.json").read_text())
    if (manifest.get("selected_count")!=120 or manifest.get("original149_overlap")!=0
        or provenance.get("source_run")!=36597035280
        or provenance.get("source_manifest_sha256")!=sha(frozen/"manifest.json")):
        raise ValueError("Missing original EU120 frozen input ledger")
    audit=pd.read_csv(source/"TRAINING_AUDIT.csv")
    if len(audit)!=10 or set(audit.year)!=set(range(2017,2027)):
        raise ValueError("10-year actual EU120 retraining results missing")
    for row in audit.itertuples(index=False):
        if not (bool(row.lookahead_guard_PASS)
            and pd.Timestamp(row.latest_training_label_exit)<pd.Timestamp(int(row.year),1,1)
            and pd.Timestamp(row.ma3_latest_exit)<pd.Timestamp(int(row.year),1,1)):
            raise ValueError("Unsafe model training future horizon")
    cp=pd.read_parquet(source/"COMPACT_REFITTED.parquet")
    hp=pd.read_parquet(source/"HYBRID_REFITTED.parquet")
    for frame in (cp,hp):
        frame["signal_date"]=pd.to_datetime(frame.signal_date)
        if frame.duplicated(["signal_date","ticker"]).any():
            raise ValueError("Duplicate frozen model output keys")
    target=pd.read_csv(ROOT/"europe120/eu120_retrain/UNIVERSE_120.csv")
    tickers=target.ticker.astype(str).tolist()
    if (len(tickers)!=120 or len(set(tickers))!=120 or
        set(tickers)!=set(pd.read_csv(frozen/"raw_ticker_csv/universe.csv").ticker)):
        raise ValueError("Original EU120 eligibility roster drift")
    scratch=out/"working"
    raw120=scratch/"raw120";rawref=scratch/"rawref"
    os.environ["FROZEN_EU120_ROOT"]=str(frozen)
    os.environ["FROZEN_149_ROOT"]=str(Path(args.raw149).resolve())
    eu.download_folder(target,raw120)
    eu.download_folder(pd.DataFrame(dict(ticker=eu.REF_TICKERS,
        macro_category=["REF_US","REF_CREDIT","REF_BOND","REF_CASH","REF_CASH"])),rawref)
    cand,_,_=load_ticker_csv_folder(raw120)
    ref,_,_=load_ticker_csv_folder(rawref)
    days=pd.DatetimeIndex(sorted(set(cp.signal_date)&set(hp.signal_date)))
    calendar=au.common_calendar(pd.concat(
        [cand["Open"][tickers],ref["Open"][eu.REF_TICKERS]],axis=1).sort_index(),days)
    if len(calendar)!=112:raise ValueError("Historical EU120 common-open period changed")
    cp=cp[cp.signal_date.isin(calendar.signal_date)]
    hp=hp[hp.signal_date.isin(calendar.signal_date)]
    scores,pm=calculate_scores(cp,hp,calendar,tickers)
    sh,sr=scores["H_ONLY"],scores["R_H"]
    original,control=original_reference_guard(source,calendar,sh,sr,tickers)
    if original.get("source_frozen_manifest_sha256")!=sha(frozen/"manifest.json"):
        raise ValueError("Frozen EU120 model source does not match manifest")
    rows=[];annual=[];traces={};dates_reference=None
    for sel,w,margin,agree in ARMS:
        name=label(sel,w,margin,agree)
        score=sh if sel=="H" else sr
        outcome,equity,turnover,dates,trace=rule_replay(
            np.where(np.isfinite(score),score,-1e6),
            pm,calendar,cand,ref,tickers,w,margin,agree)
        if dates_reference is None:dates_reference=dates
        elif not dates.equals(dates_reference):
            raise ValueError("Inconsistent original120 common-open daily calendar")
        archive=out/(name+".npz")
        np.savez_compressed(archive,equity=equity,turnover=turnover,
                            dates=dates.values,
                            d1=trace["d1"],d2=trace["d2"],
                            native_weight=trace["native_weight"],
                            native_margin=trace["native_margin"],
                            raw_weight=trace["raw_weight"],
                            fed_margin=trace["fed_margin"],
                            post_conf_weight=trace["post_conf_weight"],
                            native_agreement=trace["native_agreement"],
                            applied_agreement=trace["applied_agreement"])
        if sel=="H" and w=="D" and margin==1 and agree==1:
            strict_npz_parity(archive,source/"H_ONLY_EQUITY.npz")
            for field in ("cagr","maxdd","sharpe","terminal_equity","annualized_turnover"):
                if abs(outcome[field]-control["H_ONLY"][field])>1e-12:
                    raise ValueError("H historical baseline drift in "+field)
        if sel=="R" and w=="D" and margin==1 and agree==1:
            strict_npz_parity(archive,source/"R_H_EQUITY.npz")
            for field in ("cagr","maxdd","sharpe","terminal_equity","annualized_turnover"):
                if abs(outcome[field]-control["R_H"][field])>1e-12:
                    raise ValueError("R historical baseline drift in "+field)
        if w=="F" and margin==0 and agree==1:
            old="H_HALF" if sel=="H" else "R_HALF"
            with np.load(archive,allow_pickle=False) as a, np.load(prior/(old+".npz"),allow_pickle=False) as b:
                for key in ("equity","turnover","dates"):
                    x,y=a[key],b[key]
                    if x.shape!=y.shape:
                        raise ValueError("Previous six-arm fixed 50/50 shape drift: "+key)
                    if np.issubdtype(x.dtype,np.number):
                        if not np.allclose(x,y,atol=1e-12,rtol=0,equal_nan=True):
                            raise ValueError("Previous six-arm fixed 50/50 drift: "+key)
                    elif not np.array_equal(x,y):
                        raise ValueError("Previous six-arm fixed 50/50 calendar drift")
        drift=np.diff(np.log(np.r_[1.,equity]))
        independently=au.m.metrics(equity)
        for field in ("cagr","maxdd","sharpe","terminal_equity"):
            if abs(independently[field]-outcome[field])>1e-12:
                raise ValueError("Failed independent daily equity recompute")
        for yr in range(2017,2027):
            selected=(dates.year==yr)
            if selected.any():
                annual.append(dict(arm=name,year=yr,sessions=int(selected.sum()),
                    return_pct=100*float(np.expm1(drift[selected].sum()))))
        row=dict(arm=name,selector=sel,raw_weight_mode=w,margin_gate=margin,
            model_agreement=agree,**outcome,
            active_sessions=int((trace["d1"]>=0).sum()),
            boosted_sessions=trace["boost_count"],
            risk_on_triggers=trace["risk_on_trigger_count"],
            risk_off_triggers=trace["risk_off_trigger_count"],
            native_agreed_risk_off=trace["native_agreement_risk_off_days"],
            native_margin_threshold_sessions=trace["native_margin_threshold_days"],
            risk_off_active_sessions=trace["market_risk_off_days"],
            mean_raw_first_weight=trace["mean_raw_first_weight"],
            mean_final_first_weight=trace["mean_final_first_weight"],
            daily_path_sha256=sha(archive))
        rows.append(row)
        traces[name]=trace
        print("EU120_RULE_ABLATION "+json.dumps(
            {k:row[k] for k in ("arm","cagr","maxdd","sharpe",
                "boosted_sessions","risk_on_triggers","risk_off_triggers")}),flush=True)
    # Every gate alteration must preserve original ETF pair identities.
    for sel in ("H","R"):
        base=traces[label(sel,"D",1,1)]
        for w in ("D","F"):
            for margin in (0,1):
                for agree in (0,1):
                    path=label(sel,w,margin,agree)
                    for key in ("d1","d2"):
                        if not np.array_equal(traces[path][key],base[key]):
                            raise ValueError("Rule switch changed ETF selection: "+path)
    # Without margin boost, ET/XGB model agreement has no surviving effect.
    for sel in ("H","R"):
        for w in ("D","F"):
            n0=label(sel,w,0,0);n1=label(sel,w,0,1)
            with np.load(out/(n0+".npz")) as a, np.load(out/(n1+".npz")) as b:
                for key in ("equity","turnover","post_conf_weight"):
                    if not np.array_equal(a[key],b[key]):
                        raise ValueError("Agreement unexpectedly affects zero-margin arm")
    pd.DataFrame(rows).to_csv(out/"ECONOMICS.csv",index=False)
    pd.DataFrame(annual).to_csv(out/"ANNUAL_RETURN.csv",index=False)
    table=pd.DataFrame(rows).set_index("arm")
    comparisons=[]
    for sel in ("H","R"):
        for w in ("D","F"):
            for margin in (0,1):
                comparisons.append(dict(selector=sel,raw_weight_mode=w,margin_gate=margin,
                    agreement_ON_minus_OFF_cagr_pp=100*float(
                        table.loc[label(sel,w,margin,1),"cagr"]-
                        table.loc[label(sel,w,margin,0),"cagr"])))
        for w in ("D","F"):
            for agree in (0,1):
                comparisons.append(dict(selector=sel,raw_weight_mode=w,agreement=agree,
                    margin_ON_minus_OFF_cagr_pp=100*float(
                        table.loc[label(sel,w,1,agree),"cagr"]-
                        table.loc[label(sel,w,0,agree),"cagr"])))
        for margin in (0,1):
            for agree in (0,1):
                comparisons.append(dict(selector=sel,margin_gate=margin,agreement=agree,
                    dynamic_minus_fixed_cagr_pp=100*float(
                        table.loc[label(sel,"D",margin,agree),"cagr"]-
                        table.loc[label(sel,"F",margin,agree),"cagr"])))
    result=dict(status="EU120_16_ARM_MARGIN_AGREEMENT_WEIGHT_COMPLETE",
        original_retraining_run=39063271012,certified_eu120_replay_run=39064123941,
        source_six_arm_run=39065982541,model_retraining_this_test=0,
        original_ETFs=120,monthly_signals=112,common_open_daily_sessions=2432,
        original_all_rules_active_PARITY=True,
        prior_six_arm_no_margin_fixed_weight_PARITY=True,
        original_agreement_has_zero_effect_when_margin_disabled=True,
        all_selection_ids_unchanged_within_each_policy=True,
        protocol_sha256=sha(Path(__file__).with_name("PROTOCOL.md")),
        source_hybrid_forecast_sha256=sha(source/"HYBRID_REFITTED.parquet"),
        source_return_forecast_sha256=sha(source/"COMPACT_REFITTED.parquet"),
        retrospective_universe_selection_bias=True,production_modified=False,
        arms=rows,factorial_conditional_contrasts=comparisons)
    (out/"RESULT.json").write_text(json.dumps(result,indent=2,allow_nan=False)+"\n")
    print("EU120_RULE_FACTORIAL_SUCCESS "+json.dumps(
        {q["arm"]:q["cagr"] for q in rows}),flush=True)

if __name__=="__main__":
    main()
