"""Prepare one independent cleaned source panel; no model, no cross-vintage joins."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

import numpy as np
import pandas as pd

ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT),str(ROOT/"vendor/etf_trader_v2/src")]
from etf_trader.source_only import kernel as k
from etf_trader.source_only.raw_io import load_ticker_csv_folder
from compact21_semidev_v1.run import FROZEN_TI
from compact21_semidev_v1.view import sha
from compact21_downvol_cleanup_v1.clean import repair_downvol_family
from compact21_downvol_cleanup_v1.audit import verify_legacy_panel


def main():
    p=argparse.ArgumentParser()
    p.add_argument("--raw",type=Path,required=True)
    p.add_argument("--original",type=Path,required=True)
    p.add_argument("--repeat",type=int,choices=[1,2,3],required=True)
    p.add_argument("--out",type=Path,required=True)
    a=p.parse_args()
    if a.out.exists() and any(a.out.iterdir()):
        raise ValueError("Fresh destination required")
    if sha(a.original/"TI_COMPACT.parquet")!=FROZEN_TI[str(a.repeat)]:
        raise ValueError("Source TI original SHA mismatch")
    mats,categories,source=load_ticker_csv_folder(a.raw)
    if source["tickers"]!=149:
        raise ValueError("Not the frozen Original149 universe")
    original=pd.read_parquet(a.original/"TI_COMPACT.parquet")
    original.signal_date=pd.to_datetime(original.signal_date)
    if original.duplicated(["signal_date","ticker"]).any():
        raise ValueError("Duplicate source keys")
    if any(col not in original for col in k.F2D_FEATURES):
        raise ValueError("Missing 125 original Compact21 features")
    dates=pd.DatetimeIndex(sorted(original.signal_date.unique()))
    ret=np.log(mats["Close"].where(mats["Close"]>0)).diff()
    source_parity=verify_legacy_panel(original,ret,dates)
    transformed=repair_downvol_family(original,ret,dates,(21,63,126))
    features=k.F2D_FEATURES
    native_eligible=(original[features].notna().sum(axis=1)>=30)
    cleaned_eligible=(transformed[features].notna().sum(axis=1)>=30)
    if not native_eligible.equals(cleaned_eligible):
        raise ValueError(f"Original >=30 features cohort would change: {(native_eligible!=cleaned_eligible).sum()} rows")
    original_keys=original[["signal_date","ticker"]].reset_index(drop=True)
    pd.testing.assert_frame_equal(transformed[["signal_date","ticker"]],original_keys,check_exact=True)
    a.out.mkdir(parents=True,exist_ok=True)
    transformed.to_parquet(a.out/"TI_COMPACT.parquet",index=False)
    yearmask=transformed.signal_date.between("2017-01-01","2026-06-30")
    counts={f"downvol{h}{suffix}":{
          "old_nans":int(original.loc[yearmask,f"downvol{h}{suffix}"].isna().sum()),
          "new_nans":int(transformed.loc[yearmask,f"downvol{h}{suffix}"].isna().sum())}
          for h in (21,63,126) for suffix in ("","_pct","_dev")}
    report={"status":"CLEANED_SOURCE_PANEL_COMPLETE","variant":"CLEAN_DOWNVOL_SEMIDEV",
        "acquisition":a.repeat,"raw_source_run":37121749852,"ti_original_run":37150436612,
        "original_ti_sha256":FROZEN_TI[str(a.repeat)],
        "cleaned_ti_sha256":sha(a.out/"TI_COMPACT.parquet"),
        "cleaning_source_sha256":sha(ROOT/"compact21_downvol_cleanup_v1/clean.py"),
        "preregistration_sha256":sha(ROOT/"compact21_downvol_cleanup_v1/TRAINING_PREREGISTRATION.md"),
        "source_file_hashes":{ticker:f["sha256"] for ticker,f in source["files"].items()},
        "original_feature_parity":source_parity,
        "all_non_downvol_columns_byte_exact":True,
        "original_eligibility_preserved":True,
        "rows":len(transformed),
        "mature_monthly_rows":int(yearmask.sum()),
        "monthly_dates":int(transformed.loc[yearmask].signal_date.nunique()),
        "feature_nulls":counts,"production_adoption":False}
    if report["monthly_dates"]!=114 or report["mature_monthly_rows"]!=16986:
        raise ValueError("Wrong original development inference cohort")
    (a.out/"SOURCE_PROVENANCE.json").write_text(json.dumps(report,indent=2,allow_nan=False)+"\n")
    print(json.dumps({k:report[k] for k in ("status","acquisition","cleaned_ti_sha256","monthly_dates","feature_nulls")}),flush=True)


if __name__=="__main__":
    main()
