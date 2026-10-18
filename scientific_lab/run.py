#!/usr/bin/env python3
"""A0 coordinator: freeze 7 causal hypotheses, call specialists, audit/evaluate all."""
from __future__ import annotations
import argparse,json,shutil,sys
from pathlib import Path
import numpy as np
import pandas as pd
ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT),str(ROOT/"vendor/etf_trader_v2/src"),str(ROOT/"europe120/eu120_retrain")]
from etf_trader.source_only.raw_io import load_ticker_csv_folder
from europe_only75.refit import fixed_5050_common_open
from paper_ltr_v2.replay import sha
from scientific_lab.models import (POLICIES,top,daily_asof,market,entropy,
    observer,allocate,synthetic_gate)
from scientific_lab.ledger import evaluate,circular_block_ci
EXPECTED=.09978039091271884

def verified_input(args,out):
    target=pd.read_csv(ROOT/"europe_only75/UNIVERSE_EUR_LISTED_60.csv")
    tickers=target.ticker.astype(str).tolist()
    if len(tickers)!=60 or len(set(tickers))!=60:raise AssertionError("universe changed")
    sto=json.loads((Path(args.stoch)/"RESULT.json").read_text())
    ref=json.loads((Path(args.refit)/"RESULT.json").read_text())
    oracle=json.loads((Path(args.oracle)/"RESULT.json").read_text())
    assert sto["status"]=="STOCHASTIC_EUR60_COMPLETED"
    assert abs(sto["reference_cagr"]-EXPECTED)<1e-12
    assert sto["source_manifest_sha256"]==sha(ROOT/"data/eu120/manifest.json")
    assert ref["universe_count"]==60 and ref["training_guard_ALL_PASS"]
    assert oracle["source_60_EUR_names_sha256"]==sha(
        ROOT/"europe_only75/UNIVERSE_EUR_LISTED_60.csv")
    cal=pd.read_csv(Path(args.oracle)/"MONTHLY_ORACLE_113.csv",
        parse_dates=["signal_date","entry_date","exit_date"])
    cal=cal[["signal_date","entry_date","exit_date"]]
    assert len(cal)==113 and not cal.signal_date.duplicated().any()
    tmp=out/"_temp_raw";tmp.mkdir()
    target.to_csv(tmp/"universe.csv",index=False)
    for t in tickers:
        shutil.copyfile(ROOT/"data/eu120/raw_ticker_csv"/(t+".csv"),tmp/(t+".csv"))
    mats,_,_=load_ticker_csv_folder(tmp)
    close=mats["Close"].reindex(columns=tickers)
    opens=mats["Open"].reindex(columns=tickers)
    assert close.index.is_monotonic_increasing
    scores=pd.read_csv(Path(args.stoch)/"MONTHLY_SCORES.csv")
    assert len(scores)==113*60
    assert not scores.duplicated(["signal_date","ticker"]).any()
    dates=cal.signal_date.dt.strftime("%Y-%m-%d")
    frozen=scores.pivot(index="signal_date",columns="ticker",
        values="R_H_REFERENCE").reindex(index=dates,columns=tickers).to_numpy(float)
    assert frozen.shape==(113,60)
    parity=fixed_5050_common_open(frozen,cal,tickers,opens)
    expected=float(next(x["cagr"] for x in ref["fixed_5050"]
                        if x["variant"]=="R_H"))
    if abs(parity["cagr"]-expected)>1e-12:
        raise AssertionError(f"Frozen model parity invalid: {parity}/{expected}")
    print("A1_A2_FROZEN_REFERENCE_PARITY_PASS",parity,flush=True)
    return tickers,cal,close,opens,frozen

def main():
    parser=argparse.ArgumentParser()
    for name in ("stoch","oracle","refit","out"):
        parser.add_argument("--"+name,required=True)
    args=parser.parse_args()
    synthetic_gate()
    out=Path(args.out);out.mkdir(parents=True,exist_ok=False)
    tickers,cal,close,opens,frozen=verified_input(args,out)
    allocations={k:[] for k in POLICIES}
    observations=[];risk_rows=[];prior=[]
    for i,sd in enumerate(cal.signal_date):
        # All decisions use historical close <= signal, never entry/exit prices.
        ranked=[tickers[j] for j in top(frozen[i],n=5)]
        hist=daily_asof(close,sd)
        reg=market(hist);ent=entropy(hist)
        vol,kal=observer(close,sd,ranked[:2],hist)
        for arm in POLICIES:
            sel,w=allocate(arm,ranked,prior,vol,kal,reg,ent)
            allocations[arm].append((sel,w))
            if arm=="H5_RANK_HYSTERESIS":nextprior=sel
        prior=nextprior
        obs=dict(date=str(sd.date()),picks=ranked[:2],market=reg,entropy=ent,
                 historic_vol=vol,kalman=kal)
        observations.append(obs)
        entry=pd.Timestamp(cal.iloc[i].entry_date)
        exit_=pd.Timestamp(cal.iloc[i].exit_date)
        for name in ranked[:2]:
            realized=abs(float(np.log(opens.loc[exit_,name]/opens.loc[entry,name])))
            risk_rows.append(dict(signal_date=str(sd.date()),ticker=name,
                next_month_abs_log=realized,historic_vol=vol[name],
                kalman_unc=kal[name]["unc"]))
    result,ledger,monthly_logs=evaluate(allocations,cal,opens)
    if abs(result["H0_RH_5050"]["cagr"]-EXPECTED)>1e-12:
        raise AssertionError("A2 second implementation reference not equal")
    for key in POLICIES:
        if key=="H5_RANK_HYSTERESIS":continue
        if result[key]["selection_match_baseline"]!=1:
            raise AssertionError(f"A3 changed ranking unexpectedly: {key}")
    risk=pd.DataFrame(risk_rows)
    predictive={}
    for key in ("historic_vol","kalman_unc"):
        frame=risk[[key,"next_month_abs_log"]].replace(
            [np.inf,-np.inf],np.nan).dropna()
        corr=float(frame[key].corr(frame.next_month_abs_log,method="spearman"))
        predictive[key]=dict(n=len(frame),future_abs_return_spearman=
             corr if np.isfinite(corr) else None)
    bootstrap=circular_block_ci(monthly_logs)
    ledger.to_csv(out/"MONTHLY_LEDGER.csv",index=False)
    risk.to_csv(out/"RISK_FORECAST_AUDIT.csv",index=False)
    # All NaNs/inf become JSON null; never permit pseudo-valid JSON constants.
    def cleanse(v):
        if isinstance(v,dict):return {str(k):cleanse(x) for k,x in v.items()}
        if isinstance(v,(tuple,list)):return [cleanse(x) for x in v]
        if isinstance(v,(np.bool_,bool)):return bool(v)
        if isinstance(v,(np.integer,int)):return int(v)
        if isinstance(v,(np.floating,float)):
            return float(v) if np.isfinite(v) else None
        return v
    (out/"MONTHLY_STATES.json").write_text(
        json.dumps(cleanse(observations),indent=2,allow_nan=False)+"\n")
    entropy_months=sum(bool(o["entropy"] and o["entropy"]["fraction"]<.25
                           and o["market"]["shock"]) for o in observations)
    payload=dict(status="COMPLETED_EUR60_RESEARCH_ONLY",
        coordinator="A0",specialists=["A1_PIT","A2_EXECUTION","A3_RANKING",
          "A4_BAYES","A5_COMPLEXITY","A6_CONTROL","A7_ADVERSARIAL"],
        source_runs=[39071370480,39084898663,39087987551],
        reference_parity_pass=True,synthetic_no_lookahead_pass=True,
        historical_months=len(cal),universe_size=len(tickers),
        old_reference_cagr=EXPECTED,metrics=result,
        paired_bootstrap_12m=bootstrap,
        risk_observer_descriptive_predictive_skill=predictive,
        market_regime_gate_months=sum(bool(o["market"]["flag"]) for o in observations),
        entropy_gate_months=entropy_months,
        data_manifest_sha256=sha(ROOT/"data/eu120/manifest.json"),
        forward_untouched_holdout=False,production_unchanged=True,
        caveats=["retrospective_survivorship_selected_europe60",
          "unverified_PIT_ticker_and_ISIN_listing",
          "unverified_EUR_cash_and_market_proxy",
          "repeated_exploration_same_2017_2026_panel"],
        decision="ANALYTICAL_EVIDENCE_ONLY_NOT_DEPLOYABLE")
    txt=json.dumps(cleanse(payload),indent=2,allow_nan=False)+"\n"
    (out/"RESULT.json").write_text(txt)
    print("SCIENTIFIC_LAB_RESULT "+json.dumps(cleanse(payload),allow_nan=False),flush=True)

if __name__=="__main__":main()
