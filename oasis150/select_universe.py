#!/usr/bin/env python3
"""Freeze exactly 150 ETFs by OHLCV *coverage*, never performance or old ML scores.

Input pool: 149+70 Yahoo same-vintage CSVs in evidence_v1, both with
adjusted OHLC and raw Volume semantics. Full-period coverage selection is
retrospectively survivor-biased; this does NOT constitute PIT eligibility.
"""
from __future__ import annotations
import argparse,hashlib,json,shutil
from pathlib import Path
import numpy as np
import pandas as pd

ROOT=Path(__file__).resolve().parents[1]
SOURCES=("original149","holdout70")
ORIGIN=ROOT/"evidence_v1/data"
START=pd.Timestamp("2017-02-01")
PRE_CUTOFF=pd.Timestamp("2017-01-31")
END=pd.Timestamp("2026-07-01")

def sha(p):
    h=hashlib.sha256()
    with Path(p).open("rb") as f:
        for chunk in iter(lambda:f.read(1<<20),b""):
            h.update(chunk)
    return h.hexdigest()

def quality(path,ticker,category,group):
    data=pd.read_csv(path)
    required=("date","Open","High","Low","Close","Volume")
    if any(k not in data for k in required):return {"ticker":ticker,"source":group,"reason":"MISSING_COLUMNS"}
    date=pd.to_datetime(data["date"],errors="coerce")
    if date.isna().any():return {"ticker":ticker,"source":group,"reason":"BAD_DATES"}
    if date.duplicated().any():return {"ticker":ticker,"source":group,"reason":"DUPLICATE_DATES"}
    # No prices, profitability, volatility or model scores are used as selection signals.
    price=data[["Open","High","Low","Close"]].apply(pd.to_numeric,errors="coerce")
    volume=pd.to_numeric(data.Volume,errors="coerce")
    valid=np.isfinite(price.to_numpy(float)).all(axis=1)
    valid &= (price.to_numpy(float)>0).all(axis=1)
    valid &= np.isfinite(volume.to_numpy(float)) & (volume.to_numpy(float)>=0)
    # OHLC order not guaranteed on adjusted Yahoo historical quotes, so flag
    # violations as data quality, do not use those days for signals.
    valid &= (price.Low.to_numpy(float)<=np.minimum(price.Open.to_numpy(float),price.Close.to_numpy(float))+1e-6)
    valid &= (price.High.to_numpy(float)>=np.maximum(price.Open.to_numpy(float),price.Close.to_numpy(float))-1e-6)
    in_period=(date>=START)&(date<=END)
    pre=(date<=PRE_CUTOFF)
    future=(date==END)
    count=int((valid&in_period).sum())
    volcount=int((valid&in_period&(volume>0)).sum())
    precount=int((valid&pre).sum())
    complete_end=bool((valid&future).any())
    ok=complete_end and precount>=252 and count>=1500
    return {"ticker":ticker,"macro_category":category,"source":group,
            "source_path":str(path.relative_to(ROOT)),
            "sha256":sha(path),"rows_total":int(len(data)),
            "history_before_2017":precount,"observed_ohlc_in_study":count,
            "observed_positive_volume_study":volcount,
            "zero_volume_in_study":int((valid&in_period&(volume==0)).sum()),
            "invalid_ohlcv_rows":int((~valid).sum()),
            "observed_end":complete_end,"reason":"OK" if ok else
              ("NO_END_QUOTE" if not complete_end else
                ("INSUFFICIENT_PRIOR" if precount<252 else "INSUFFICIENT_STUDY_COVERAGE"))}

def main():
    p=argparse.ArgumentParser();p.add_argument("--out",required=True)
    a=p.parse_args()
    output=Path(a.out);output.mkdir(parents=True,exist_ok=False)
    stage=output/"selected_raw";stage.mkdir()
    records=[]; seen=set(); sources={}
    for group in SOURCES:
        folder=ORIGIN/group
        roster=pd.read_csv(folder/"universe.csv")
        manifest=json.loads((folder/"manifest.json").read_text())
        assert manifest["status"]=="UNIFORM_YAHOO_FRESH_RAW"
        assert manifest["price_semantics"]=="same-row Adj Close/raw Close adjustment for OHLC; raw Volume"
        assert len(roster)==manifest["tickers"]
        assert len(roster)==len(set(roster.ticker.astype(str)))
        declared=manifest["file_sha256"]
        sources[group]={"manifest_sha256":sha(folder/"manifest.json"),
                        "roster_sha256":sha(folder/"universe.csv"),
                        "declared_count":len(roster)}
        for row in roster.itertuples(index=False):
            ticker=str(row.ticker)
            if ticker in seen:raise AssertionError("Duplicate across archives: "+ticker)
            seen.add(ticker)
            file=folder/(ticker+".csv")
            if not file.is_file():raise AssertionError("Missing ticker source "+ticker)
            record=quality(file,ticker,str(row.macro_category),group)
            if record.get("sha256")!=declared.get(ticker):
                raise AssertionError("Frozen SHA mismatch: "+ticker)
            records.append(record)
    if len(records)!=219:raise AssertionError("Source pool must be 149 + 70")
    eligible=[x for x in records if x["reason"]=="OK"]
    eligible.sort(key=lambda r:(-r["observed_ohlc_in_study"],
        -r["observed_positive_volume_study"],-r["history_before_2017"],r["ticker"]))
    if len(eligible)<150:
        raise RuntimeError(f"UNIVERSE_GATE_BLOCKED insufficient data complete: {len(eligible)} of 219")
    selected=eligible[:150]
    roster=pd.DataFrame([{"ticker":r["ticker"],"macro_category":r["macro_category"],
       "source":r["source"],"source_path":r["source_path"],
       "source_sha256":r["sha256"],
       "valid_study_rows":r["observed_ohlc_in_study"],
       "valid_prior_rows":r["history_before_2017"],
       "positive_volume_study":r["observed_positive_volume_study"]}
       for r in selected])
    assert len(roster)==roster.ticker.nunique()==150
    roster.to_csv(output/"OASIS_TOP150.csv",index=False)
    # Only the loader-compatible two-column roster plus frozen source CSVs
    # enters the strategy engine. Additional fields stay in selection receipt.
    roster[["ticker","macro_category"]].to_csv(stage/"universe.csv",index=False)
    for item in selected:
        shutil.copyfile(ROOT/item["source_path"],stage/(item["ticker"]+".csv"))
        assert sha(stage/(item["ticker"]+".csv"))==item["sha256"]
    (output/"FULL_219_QUALITY_CENSUS.csv").write_text(
        pd.DataFrame(records).sort_values("ticker").to_csv(index=False))
    chosen_stats={"min_valid_study":min(r["observed_ohlc_in_study"] for r in selected),
      "max_valid_study":max(r["observed_ohlc_in_study"] for r in selected),
      "median_valid_study":int(np.median([r["observed_ohlc_in_study"] for r in selected])),
      "zero_volume_total":sum(r["zero_volume_in_study"] for r in selected),
      "selected_group_counts":{g:sum(r["source"]==g for r in selected) for g in SOURCES},
      "selected_nonzero_volume_min":min(r["observed_positive_volume_study"] for r in selected),
      "excluded_due_to_quality":{str(reason):sum(r["reason"]==reason for r in records)
          for reason in sorted(set(r["reason"] for r in records)) if reason!="OK"}}
    receipt={"status":"TOP150_FROZEN_BY_PRICE_COVERAGE","selected_count":150,
       "pool_size":219,"source_groups":sources,"period":[str(START.date()),str(END.date())],
       "selection_only_quality_not_performance":True,
       "uses_future_data_completeness":True,"point_in_time_universe":False,
       "sources_are_same_price_adjustment_convention":True,
       "universe_sha256":sha(output/"OASIS_TOP150.csv"),
       "census_sha256":sha(output/"FULL_219_QUALITY_CENSUS.csv"),
       "stats":chosen_stats,
       "top10_by_coverage":[r["ticker"] for r in selected[:10]]}
    (output/"SELECTION_RESULT.json").write_text(json.dumps(receipt,indent=2)+"\n")
    print("OASIS_150_SELECTION_RESULT "+json.dumps(receipt),flush=True)

if __name__=="__main__":main()
