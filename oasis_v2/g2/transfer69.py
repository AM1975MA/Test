#!/usr/bin/env python3
"""G2 out-of-roster (not untouched/PIT) structural diversification transfer, 69 ETFs."""
import argparse,json,math,hashlib
from pathlib import Path
from collections import Counter
import numpy as np
import pandas as pd
from oasis.observers import prepare,market_states
from oasis.daily_backtest import simulate as old_oasis_simulate
from oasis_v2.g2.risk_portfolio import (ARMS, GROUPS,simulate as g2_simulate,
    summarize,paired_month_bootstraps,digest)
ROOT=Path(__file__).resolve().parents[2]
BASE=ROOT/"oasis150/results/frozen"

def excluded_universe():
    a=pd.read_csv(BASE/"OASIS_TOP150.csv")
    census=pd.read_csv(BASE/"FULL_219_QUALITY_CENSUS.csv")
    assert len(a)==150 and len(census)==219
    excluded=census[~census.ticker.isin(a.ticker)].copy().sort_values("ticker")
    assert len(excluded)==69 and excluded.ticker.nunique()==69
    assert set(excluded.macro_category)==set(GROUPS)
    # All 69 have corresponding exact-content source receipts.
    for r in excluded.itertuples(index=False):
        file=ROOT/r.source_path
        if digest(file)!=r.sha256:raise AssertionError("source drift "+r.ticker)
        if int(r.observed_ohlc_in_study)!=2366:
            raise AssertionError("Missing opening-market study quote for "+r.ticker)
    excluded["source_sha256"]=excluded.sha256
    return excluded

def load_group(excluded):
    C={};O={}
    for r in excluded.itertuples(index=False):
        f=pd.read_csv(ROOT/r.source_path,parse_dates=["date"]).set_index("date").sort_index()
        C[r.ticker]=f.Close
        O[r.ticker]=f.Open
    close=pd.concat(C,axis=1).reindex(columns=excluded.ticker.tolist())
    opens=pd.concat(O,axis=1).reindex(columns=excluded.ticker.tolist())
    ref=pd.read_csv(BASE/"P0_MONTHLY_GREEDY.csv",parse_dates=["day","signal_date"])
    assert len(ref)==2366
    assert opens.loc[ref.day].notna().all().all()
    assert close.loc[ref.signal_date].notna().all().all()
    return opens,close,ref

def run():
    a=argparse.ArgumentParser();a.add_argument("--out",required=True);args=a.parse_args()
    out=Path(args.out);out.mkdir(parents=True,exist_ok=False)
    sample=excluded_universe()
    O,C,calendar=load_group(sample)
    f=prepare(C)
    states=market_states(f)
    anchor=old_oasis_simulate("P0_MONTHLY_GREEDY",f,states,O,
          list(calendar.day),list(calendar.signal_date))
    results={};tables={}
    for arm in ARMS:
        z=g2_simulate(arm,sample,O,C,calendar,f)
        summary=summarize(z)
        results[arm]=summary;tables[arm]=z
        z.to_csv(out/(arm+".csv"),index=False)
        print("G2_69_ARM",arm,json.dumps(summary),flush=True)
    r0=tables["R0_TWO_REFERENCE"].wealth.to_numpy(float)
    old=anchor.wealth.to_numpy(float)
    error=float(np.max(np.abs(r0-old)))
    if error>1e-8:raise AssertionError(f"69-source reference parity failed {error}")
    ref=results["R0_TWO_REFERENCE"]
    success={}
    for key in ("R2_ONE_PER_GROUP_EQUAL","R3_GROUP_INV_VOL"):
        v=results[key]
        success[key]=bool(v["daily_maxdd"]>ref["daily_maxdd"]
             and v["daily_es5"]>ref["daily_es5"]
             and v["cagr"]>=ref["cagr"]-.03)
    report=dict(status="G2_69_OUT_OF_ROSTER_TRANSFER_COMPLETED",
       previously_mined_2017_to_2026_source=True,
       independent_prospective_validation=False,
       original_150_training_roster_unused=True,
       source_69_no_matured_g1_alpha=True,
       roster_69_names=sample.ticker.tolist(),
       source_219_sha256=digest(BASE/"FULL_219_QUALITY_CENSUS.csv"),
       source_150_sha256=digest(BASE/"OASIS_TOP150.csv"),
       n_excluded=69,n_days=2366,
       group_member_counts=sample.groupby("macro_category").size().to_dict(),
       original_P0_reference_parity_error=error,
       metrics=results,paired_bootstrap=paired_month_bootstraps(tables),
       preregistered_diversification_gate=success,
       difference_from_source_150="UNIVERSE_69_EXCLUDED_FROM_ORIGINAL_COMPLETENESS_SELECTED_150",
       caveats=["not an untouched year or new fund birth sample",
          "prior source holdout70 already previously studied in other research",
          "raw Yahoo historical prices cannot verify executable broker spreads",
          "not verified fund point-in-time/delistings or EUR trading venues"])
    (out/"RESULT.json").write_text(json.dumps(report,indent=2,allow_nan=False)+"\n")
    print("OASIS_G2_69_TRANSFER_RESULT "+json.dumps(report,allow_nan=False),flush=True)
if __name__=="__main__":run()
