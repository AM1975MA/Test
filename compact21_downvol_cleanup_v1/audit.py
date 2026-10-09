"""First-stage DOWNVOL cleanup QA: only Repeat1 raw and its frozen original TI panel."""
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
from compact21_downvol_cleanup_v1.clean import repair_downvol_family, downside_semideviation

KEYS=["signal_date","ticker"]
HS=(21,63,126)
START=pd.Timestamp("2017-01-01")
END=pd.Timestamp("2026-06-30")


def numeric_equal(a,b):
    a=np.asarray(a,dtype=float)
    b=np.asarray(b,dtype=float)
    mask=np.isfinite(a); other=np.isfinite(b)
    return (np.array_equal(mask,other) and
            bool(np.allclose(a[mask],b[mask],atol=1e-12,rtol=0)))


def verify_legacy_panel(panel,returns,dates):
    indices=pd.MultiIndex.from_frame(panel[KEYS])
    out={}
    for h in HS:
        legacy=k.rolling_downvol(returns,h).reindex(dates).stack(dropna=False).reindex(indices).to_numpy(dtype=float)
        actual=panel[f"downvol{h}"].to_numpy(float)
        if not numeric_equal(legacy,actual):
            different=np.count_nonzero((np.isfinite(legacy)!=np.isfinite(actual)) |
                (np.isfinite(legacy)&np.isfinite(actual)&(np.abs(legacy-actual)>1e-12)))
            raise ValueError(f"Legacy input lineage mismatch downvol{h}, cells={different}")
        out[str(h)]={"matched_panel_cells":int(len(legacy)),
                      "nan_mask_exact":True,"finite_atol":1e-12}
    return out


def analyze(raw,ti,out):
    if sha(ti/"TI_COMPACT.parquet")!=FROZEN_TI["1"]:
        raise ValueError("Frozen original Repeat1 TI panel mismatch")
    mats,categories,manifest=load_ticker_csv_folder(raw)
    if manifest["tickers"]!=149:
        raise ValueError("Frozen raw Original149 universe differs")
    panel=pd.read_parquet(ti/"TI_COMPACT.parquet").copy()
    if not set(KEYS+k.F2D_FEATURES).issubset(panel.columns):
        raise ValueError("Wrong frozen Compact21 feature schema")
    panel.signal_date=pd.to_datetime(panel.signal_date)
    if panel[KEYS].isna().any().any() or panel.duplicated(KEYS).any():
        raise ValueError("Nonunique original (date,ticker) rows")
    dates=pd.DatetimeIndex(sorted(panel.signal_date.unique()))
    close=mats["Close"]
    ret=np.log(close.where(close>0)).diff()
    lineage=verify_legacy_panel(panel,ret,dates)
    new=repair_downvol_family(panel,ret,dates,HS)
    locked=[x for x in panel.columns if x not in [f"downvol{h}{suffix}" for h in HS
                        for suffix in ("","_pct","_dev")]]
    pd.testing.assert_frame_equal(panel[locked],new[locked],check_exact=True)
    eligible_original=panel[k.F2D_FEATURES].notna().sum(axis=1)>=30
    eligible_repaired=new[k.F2D_FEATURES].notna().sum(axis=1)>=30
    selected=panel.signal_date.ge(START)&panel.signal_date.le(END)
    if not selected.any() or panel.loc[selected,"signal_date"].nunique()!=114:
        raise ValueError("Missing original 114-month data window")
    before=panel.loc[selected].reset_index(drop=True)
    after=new.loc[selected].reset_index(drop=True)
    report={"status":"SINGLE_SNAPSHOT_DOWNVOL_QA_COMPLETE",
            "original_raw_run":37121749852,"original_ti_run":37150436612,
            "repeat":1,"compared_downloads":1,
            "panel_sha256":FROZEN_TI["1"],
            "source_file_sha256":{ticker:record["sha256"]
                                  for ticker,record in manifest["files"].items()},
            "tickers":manifest["tickers"],
            "overall_rows":len(panel),
            "evaluated_rows":len(before),
            "evaluated_months":114,
            "all_other_116_features_and_labels_exact":True,
            "baseline_feature_lineage":lineage,
            "original_available_feature_eligibility_count":int(eligible_original.loc[selected].sum()),
            "cleaned_available_feature_eligibility_count":int(eligible_repaired.loc[selected].sum()),
            "changed_eligibility_rows":int((eligible_original.ne(eligible_repaired)&selected).sum()),
            "treatment_changes_definition":True,
            "cagr_computed":False,"production_adoption":False,"three_repeat_model_test_executed":False,
            "per_horizon":{}}
    date_to_group=before.signal_date.dt.year
    audit_rows=[]
    indices=pd.MultiIndex.from_frame(before[KEYS])
    for h in HS:
        negative=ret.lt(0).astype(float).where(ret.notna()).rolling(h,min_periods=h).sum()
        completeness=ret.notna().astype(float).rolling(h,min_periods=h).sum()
        n=negative.reindex(dates).stack(dropna=False).reindex(indices).to_numpy(dtype=float)[selected.reindex(panel.index).loc[selected].to_numpy()] if False else None
        # Direct source alignment to original selected query keys; no key dropping.
        observed=negative.reindex(dates).stack(dropna=False).reindex(indices).to_numpy(dtype=float)
        valid_full=completeness.reindex(dates).stack(dropna=False).reindex(indices).to_numpy(dtype=float)
        old=before[f"downvol{h}"].to_numpy(dtype=float)
        recent=after[f"downvol{h}"].to_numpy(dtype=float)
        if len(observed)!=len(old) or len(valid_full)!=len(old):
            raise ValueError("Unexpected source alignment")
        window_complete=valid_full==h
        threshold=max(10,h//2)
        count_crossed=np.isnan(old)&np.isfinite(recent)&window_complete&(observed<threshold)
        explained=np.isnan(old)&np.isfinite(recent)&window_complete
        if count_crossed.sum()!=explained.sum():
            raise ValueError("Unexpected repair beyond original negative-count threshold")
        new_missing=np.isfinite(old)&np.isnan(recent)
        counts={}
        for suffix in ("","_pct","_dev"):
            key=f"downvol{h}{suffix}"
            before_mask=before[key].isna()
            after_mask=after[key].isna()
            counts[key]={"original_missing":int(before_mask.sum()),
                         "cleaned_missing":int(after_mask.sum()),
                         "missing_reduced":int(before_mask.sum()-after_mask.sum()),
                         "original_missing_percent":round(100*float(before_mask.mean()),5),
                         "cleaned_missing_percent":round(100*float(after_mask.mean()),5)}
        by_year={}
        for year in sorted(date_to_group.unique()):
            group=(date_to_group==year).to_numpy()
            by_year[str(year)]={"rows":int(group.sum()),
                "legacy_raw_missing":int(np.isnan(old[group]).sum()),
                "cleaned_raw_missing":int(np.isnan(recent[group]).sum()),
                "complete_windows_but_legacy_nan":int(explained[group].sum())}
        report["per_horizon"][str(h)]={"negative_count_threshold":threshold,
               "complete_rolling_return_windows":int(window_complete.sum()),
               "missing_legacy_with_complete_returns":int(explained.sum()),
               "missing_legacy_due_negative_threshold":int(count_crossed.sum()),
               "proposed_missing_but_legacy_finite":int(new_missing.sum()),
               "cleaned_zero_values":int(np.count_nonzero(recent==0)),
               "source_incomplete_windows":int((~window_complete).sum()),
               "features":counts,"by_year":by_year}
        rows=np.flatnonzero(explained)
        for ix in rows[:30]:
            audit_rows.append({"signal_date":str(before.iloc[ix].signal_date.date()),
                "ticker":str(before.iloc[ix].ticker),"horizon":h,
                "negative_returns_in_window":int(observed[ix]),"required_negative":threshold,
                "legacy_value":None,"cleaned_value":float(recent[ix])})
    report["code_sha256"]=sha(ROOT/"compact21_downvol_cleanup_v1/clean.py")
    report["qa_sha256"]=sha(ROOT/"compact21_downvol_cleanup_v1/audit.py")
    report["protocol_sha256"]=sha(ROOT/"compact21_downvol_cleanup_v1/PREREGISTRATION.md")
    out.mkdir(parents=True,exist_ok=False)
    (out/"QA.json").write_text(json.dumps(report,indent=2,allow_nan=False)+"\n")
    pd.DataFrame(audit_rows).to_csv(out/"EXAMPLES.csv",index=False)
    details=["# First-stage source feature cleanup — single Original149 acquisition","",
        "This is a *read-only* acquisition-1 QA of source-derived `downvol21/63/126`. Not a new strategy, not CAGR, not a three-repeat test.",
        "A valid historical price window may yield legacy NaN because its number of negative returns is below an arbitrary threshold. The replacement uses all available historical returns in the complete window, assigning zero contribution to non-negative returns.",
        "","| Feature | Legacy null cells | Cleaned null cells | Repaired complete-window cells | New missing cells |",
        "|---|---:|---:|---:|---:|"]
    for h,d in report["per_horizon"].items():
        f=d["features"][f"downvol{h}"]
        details.append(f"| downvol{h} | {f['original_missing']} | {f['cleaned_missing']} | "+
                       f"{d['missing_legacy_due_negative_threshold']} | {d['proposed_missing_but_legacy_finite']} |")
    details += ["",f"- 114 monthly queries; {report['evaluated_rows']} source-panel rows.",
        f"- Original eligibility (>=30 original valid features): {report['original_available_feature_eligibility_count']}.",
        f"- Proposed eligibility: {report['cleaned_available_feature_eligibility_count']}; changed rows: {report['changed_eligibility_rows']} (must freeze old eligibility during paired model comparison).",
        "- Every untouched feature, label, ticker and date is preserved byte-exactly.",
        "- Cleaning changes downside feature semantics, and must not be described as merely filling missing cells.",
        "- Three-snapshot repeatability, predictive performance, trading simulation and CAGR remain UNTESTED.",
        "- Source provenance, per-year breakdowns and derived-feature NaN rates are in QA.json."]
    (out/"QA.md").write_text("\n".join(details)+"\n")
    print((out/"QA.md").read_text(),flush=True)


def main():
    p=argparse.ArgumentParser()
    p.add_argument("--raw",type=Path,required=True)
    p.add_argument("--ti",type=Path,required=True)
    p.add_argument("--out",type=Path,required=True)
    a=p.parse_args()
    analyze(a.raw,a.ti,a.out)

if __name__=="__main__":
    main()
