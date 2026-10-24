#!/usr/bin/env python3
"""EU48 forensic: legacy V2 vs actual V3 corrected build_features on SAME data.

READ ONLY: mathematically quantify missing-cell and numeric feature differences
introduced by old V2 feature builder imported by V3 EU48 heads pipeline.
Cannot attribute low CAGR to feature mismatch unless differences are material.
"""
from __future__ import annotations
import hashlib,inspect,json,argparse,importlib.util
from pathlib import Path
import numpy as np,pandas as pd
from etf_trader.source_only import kernel as legacy
from etf_trader.source_only.raw_io import load_ticker_csv_folder
def fhash(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def patched_builder(module,prior,mats):
    spy=prior.set_index("date").SPY
    assert spy.index.equals(mats["Close"].index)
    source=inspect.getsource(module.build_features)
    clause="mkt=ret['SPY'] if 'SPY' in ret else ret.median(axis=1)"
    assert source.count(clause)==1
    x=source.replace(clause,"mkt=EU48_PRIOR_US_SPY_RETURN.reindex(ret.index)")
    module.EU48_PRIOR_US_SPY_RETURN=spy.pct_change(fill_method=None)
    context={}
    exec(compile(x,"<locked_isolated_kernel_EU48_diagnostic>","exec"),module.__dict__,context)
    return context["build_features"](mats)
def main():
    p=argparse.ArgumentParser()
    p.add_argument("--prep",required=True)
    p.add_argument("--strict",required=True)
    p.add_argument("--v3kernel",required=True)
    p.add_argument("--out",required=True)
    args=p.parse_args()
    out=Path(args.out);out.mkdir(parents=True,exist_ok=True)
    v3path=Path(args.v3kernel)
    spec=importlib.util.spec_from_file_location("frozen_real_v3_corrected_kernel",v3path)
    v3=importlib.util.module_from_spec(spec);spec.loader.exec_module(v3)
    mats,cat,_=load_ticker_csv_folder(Path(args.prep)/"raw_ticker_csv")
    assert len(cat)==48 and "SPY" not in cat
    prior=pd.read_csv(args.strict,parse_dates=["date"])
    assert prior.date.is_unique
    # Force exact same synchronized SPY input to both immutable functions.
    old_dates,old_panel,*_=patched_builder(legacy,prior,mats)
    new_dates,new_panel,*_=patched_builder(v3,prior,mats)
    assert old_dates.equals(new_dates)
    assert list(legacy.F2D_FEATURES)==list(v3.F2D_FEATURES)
    feats=list(v3.F2D_FEATURES);assert len(feats)==125
    old=old_panel.set_index(["signal_date","ticker"]).sort_index()
    new=new_panel.set_index(["signal_date","ticker"]).sort_index()
    assert old.index.equals(new.index)
    assert old.index.get_level_values("ticker").nunique()==48
    months=pd.read_csv("isin_first2026/compact21_base48/results/FITTED_3SEED_ANNUAL/BASE_ORIGINAL_125F_XGB_65x48_TRUE_OOS_SCORES.csv",parse_dates=["signal_date"])
    dates=sorted(months.signal_date.unique());assert len(dates)==65
    relevant=old.index.get_level_values("signal_date").isin(dates)
    a=old.loc[relevant,feats];b=new.loc[relevant,feats]
    assert a.shape==(65*48,125) and a.index.equals(b.index)
    table=[]
    for name in feats:
        x=a[name].to_numpy(float);y=b[name].to_numpy(float)
        valid=np.isfinite(x)&np.isfinite(y)
        delta=np.abs(x[valid]-y[valid]);tol=1e-12*np.maximum(1,np.abs(y[valid]))
        changed=int(np.sum(delta>tol))
        nanflip=int((np.isfinite(x)!=np.isfinite(y)).sum())
        table.append(dict(feature=name,changed_numeric_rows=changed,nan_flip_rows=nanflip,
            compared_finite_rows=int(valid.sum()),missing_legacy=int((~np.isfinite(x)).sum()),
            missing_v3=int((~np.isfinite(y)).sum()),
            max_abs_difference=float(delta.max()) if len(delta) else 0.0,
            median_abs_difference=float(np.median(delta)) if len(delta) else 0.0))
    df=pd.DataFrame(table).sort_values(["changed_numeric_rows","nan_flip_rows"],ascending=False)
    df.to_csv(out/"EXACT_125F_LEGACY_VS_V3_DIFF.csv",index=False)
    changed=df[(df.changed_numeric_rows>0)|(df.nan_flip_rows>0)]
    month=[]
    for dt in dates:
        x=a.xs(dt,level="signal_date").to_numpy(float)
        y=b.xs(dt,level="signal_date").to_numpy(float)
        flips=int((np.isfinite(x)!=np.isfinite(y)).sum())
        changes=int(((np.abs(x-y)>1e-12*np.maximum(1,np.abs(y))) & (np.isfinite(x)&np.isfinite(y))).sum())
        month.append(dict(signal_date=str(dt.date()),year=dt.year,n_features=125,
            cells=48*125,na_changes=flips,changed_cells=changes))
    pd.DataFrame(month).to_csv(out/"MONTHLY_FEATURE_MISMATCH.csv",index=False)
    report=dict(original_legacy_kernel_sha256=fhash(inspect.getfile(legacy)),
        corrected_real_v3_kernel_sha256=fhash(v3path),
        ranker_source="etf-trader-v3 corrected/experiments/europe48_transfer/v3_europe48_heads.py",
        same_EU48_vendor_adjusted_raw=True,same_US_SPY_asof_prices=True,
        n_features=125,n_tickers=48,n_signal_months=65,
        altered_feature_names=changed.feature.tolist(),
        n_altered_features=len(changed),
        changed_finite_feature_values=int(df.changed_numeric_rows.sum()),
        changed_missing_cells=int(df.nan_flip_rows.sum()),
        impact_on_ranker_predictions_unmeasured=True,
        original_hyperparams_127_leaf_confound=True,
        sample_from_previously_researched_calendar_not_holdout=True,
        production_files_changed=False)
    (out/"FEATURE_AUDIT.json").write_text(json.dumps(report,indent=2))
    print("EU48_KERNEL_FEATURE_DIFFERENCE_PASS",json.dumps(report,indent=2),flush=True)
    print(df.head(20).to_string(index=False),flush=True)
if __name__=="__main__":main()
