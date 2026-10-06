#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path

import pandas as pd

from etf_trader.source_only import kernel as k
from etf_trader.source_only.features import build as build_extra_features
from etf_trader.source_only.models import fit_predict, variants
from etf_trader.source_only.raw_io import load_ticker_csv_folder


def main() -> int:
    ap=argparse.ArgumentParser()
    ap.add_argument("--data",required=True,help="raw ticker CSV folder: universe.csv + <TICKER>.csv")
    ap.add_argument("--output",default="artifact/titanium_source_only")
    ap.add_argument("--xgb-workers",type=int,default=3,
                    help="parallel isolated XGBoost seed workers per horizon")
    ap.add_argument("--xgb-threads-per-worker",type=int,default=1,
                    help="XGBoost threads used inside each isolated worker")
    args=ap.parse_args()
    out=Path(args.output);out.mkdir(parents=True,exist_ok=True)
    if args.xgb_workers<1 or args.xgb_threads_per_worker<1:
        raise ValueError("XGBoost worker/thread counts must be >=1")
    os.environ["ETF_TRADER_XGB_WORKERS"]=str(args.xgb_workers)
    os.environ["ETF_TRADER_XGB_THREADS_PER_WORKER"]=str(args.xgb_threads_per_worker)

    mats,cats,raw_manifest=load_ticker_csv_folder(args.data)
    cols=list(mats["Close"].columns)
    k.ALL_TICKERS=sorted(cols)
    k.TICKER_CATEGORY=cats
    k.CATEGORY_TICKERS={c:sorted([t for t in cols if cats[t]==c]) for c in sorted(set(cats.values()))}

    dates=k.month_end_dates(mats["Close"].index)
    if len(dates) and dates[-1]==mats["Close"].index[-1]:
        dates=dates[:-1]

    _,compact,tail,_=k.build_features(mats)
    compact=compact[compact.signal_date.isin(dates)].copy()
    tail=tail[tail.signal_date.isin(dates)].copy()
    compact=k.add_labels(compact,mats["Open"],dates)
    tail=k.add_labels(tail,mats["Open"],dates)
    tail_no_labels=tail.drop(columns=[c for c in tail if c.startswith(("fwd_","target_","exit_")) or c in ["entry_date","y_tailmix"]])
    macro,mfeatures=k.build_macro_panel(tail_no_labels,tail)
    extra=build_extra_features(mats,cats,dates)

    pred=fit_predict(k,compact,tail,macro,mfeatures,extra,out/"annual_models")
    pred=pred[(pred.signal_date>="2017-01-31")&(pred.signal_date<="2026-06-30")].copy()
    baseline=variants(pred)["baseline"].rename(columns={"score":"TIT_R"})
    calendar=pred[["signal_date","ticker","entry_date","exit_date"]].drop_duplicates(["signal_date","ticker"])
    panel=baseline.merge(calendar,on=["signal_date","ticker"],how="inner",validate="one_to_one")
    panel=panel[["signal_date","entry_date","exit_date","ticker","TIT_R"]].sort_values(["signal_date","ticker"])
    panel.to_csv(out/"TIT_R_SOURCE_ONLY.csv",index=False)

    manifest={
        "status":"SOURCE_ONLY_TIT_R_REBUILT",
        "productive_inputs":["raw per-ticker OHLCV CSV","universe.csv","repository source"],
        "historical_tit_r_consumed":False,
        "historical_paths_consumed":False,
        "rows":int(len(panel)),
        "signal_dates":int(panel.signal_date.nunique()),
        "tickers":int(panel.ticker.nunique()),
        "raw_manifest":raw_manifest,
        "producer":{
            "kernel":"src/etf_trader/source_only/kernel.py",
            "models":"src/etf_trader/source_only/models.py",
            "features":"src/etf_trader/source_only/features.py",
            "variant":"baseline",
            "xgb_execution":{
                "mode":"isolated_parallel_workers",
                "workers_per_horizon":args.xgb_workers,
                "threads_per_worker":args.xgb_threads_per_worker,
            },
        },
    }
    (out/"TIT_R_SOURCE_ONLY_MANIFEST.json").write_text(json.dumps(manifest,indent=2,default=str)+"\n")
    print(json.dumps({k:v for k,v in manifest.items() if k!="raw_manifest"},indent=2))
    return 0


if __name__=="__main__":
    raise SystemExit(main())