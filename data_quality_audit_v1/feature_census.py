"""Data-only full-column census on the three immutable TI feature panels."""
import argparse,json
from pathlib import Path
import numpy as np
import pandas as pd

KEY=("signal_date","ticker")
NONINPUT_PREFIXES=("fwd_","target_","exit_")
NONINPUT_EXACT={"entry_date","exit_date","y_tailmix","target_rank_pct","target_multi_rank"}
def census(roots,name):
    tables=[]
    for root in roots:
        p=Path(root)/name
        if not p.is_file():raise ValueError(f"Missing expected original panel: {p}")
        df=pd.read_parquet(p)
        if not set(KEY).issubset(df):raise ValueError(f"Not keyed: {p}")
        if df.duplicated(list(KEY)).any() or df[list(KEY)].isna().any().any():
            raise ValueError("Duplicate or null vintage keys")
        df["signal_date"]=pd.to_datetime(df.signal_date)
        tables.append(df.sort_values(list(KEY)).reset_index(drop=True))
    f=tables[0]
    expected=set(f.columns)
    for df in tables[1:]:
        if set(df.columns)!=expected:raise ValueError("Feature schema differs")
        pd.testing.assert_frame_equal(df[list(KEY)],f[list(KEY)],check_exact=True)
    feats=[c for c in f if c not in KEY and c not in NONINPUT_EXACT
           and not c.startswith(NONINPUT_PREFIXES) and
           all(pd.api.types.is_numeric_dtype(df[c]) for df in tables)]
    if not feats:raise ValueError("No numeric features found")
    per=[];pair=[]
    for feature in feats:
        values=[pd.to_numeric(df[feature],errors="raise").to_numpy(float) for df in tables]
        for i,v in enumerate(values,1):
            if np.isinf(v).any():raise ValueError(f"Inf in {name} {feature} repeat{i}")
            finite=v[np.isfinite(v)]
            per.append(dict(panel=name,feature=feature,repeat=i,rows=len(v),
                missing=int(np.isnan(v).sum()),missing_pct=float(np.isnan(v).mean()),
                finite_count=len(finite),zero_count=int((finite==0).sum()),
                q01=float(np.quantile(finite,.01)) if len(finite) else None,
                q50=float(np.median(finite)) if len(finite) else None,
                q99=float(np.quantile(finite,.99)) if len(finite) else None))
        for i,j in ((1,2),(1,3),(2,3)):
            a,b=values[i-1],values[j-1]
            maska=np.isfinite(a);maskb=np.isfinite(b);joint=maska&maskb
            d=np.abs(a[joint]-b[joint])
            rankd=None
            if joint.any():
                rankd=np.abs(pd.Series(a[joint]).rank(pct=True,method="average")-
                    pd.Series(b[joint]).rank(pct=True,method="average")).mean()
            pair.append(dict(panel=name,feature=feature,pair=f"{i}-{j}",
                missing_mask_changed=int(np.count_nonzero(maska!=maskb)),
                jointly_finite=int(joint.sum()),
                changed_finite_exact=int(np.count_nonzero(d>0)),
                changed_finite_gt1e_10=int(np.count_nonzero(d>1e-10)),
                max_abs_diff=float(d.max()) if len(d) else None,
                p95_abs_diff=float(np.quantile(d,.95)) if len(d) else None,
                rank_mean_abs=float(rankd) if rankd is not None else None))
    return per,pair,len(feats),len(f)

def main():
    ap=argparse.ArgumentParser()
    for arg in ("r1","r2","r3","out"):ap.add_argument("--"+arg,required=True)
    a=ap.parse_args();roots=[getattr(a,f"r{i}") for i in (1,2,3)]
    out=Path(a.out);out.mkdir(parents=True,exist_ok=False)
    stats=[];pair=[];panels={}
    for name in ("TI_COMPACT.parquet","TI_TAIL.parquet"):
        s,p,count,rows=census(roots,name)
        stats.extend(s);pair.extend(p);panels[name]={"feature_columns":count,"rows_per_repeat":rows}
    df=pd.DataFrame(stats);pd.DataFrame(pair).to_csv(out/"FEATURE_PAIR_DRIFT.csv",index=False)
    df.to_csv(out/"FEATURE_MISSINGNESS.csv",index=False)
    pp=pd.DataFrame(pair)
    overall=dict(status="FEATURE_PANEL_CENSUS_COMPLETE", source_run=37150436612,
        panels=panels,missing_mask_changes=int(pp.missing_mask_changed.sum()),
        columns_with_any_missing_mask_change=int(pp.groupby(["panel","feature"]).missing_mask_changed.sum().gt(0).sum()),
        columns_with_any_finite_drift=int(pp.groupby(["panel","feature"]).changed_finite_exact.sum().gt(0).sum()),
        changed_features_by_panel={
          key:int(group.groupby("feature").changed_finite_exact.sum().gt(0).sum())
          for key,group in pp.groupby("panel")},models_trained=False,production_adoption=False,
        complete_input_gate_pass=False,ma3_and_macro_not_yet_certified=True)
    (out/"RESULT.json").write_text(json.dumps(overall,indent=2,allow_nan=False)+"\n")
    (out/"REPORT.md").write_text("# Original149 independent per-feature input census\n\n"
       "Three Original149 snapshots, all numeric inputs from original Compact and Tail panels. "
       "No training, no cleaning imputation, no CAGR.\n\n"+
       "\n".join(f"- {k}: {v['feature_columns']} numeric input columns × {v['rows_per_repeat']} rows/vintage" for k,v in panels.items())+
       f"\n- Features with a finite difference in at least one pair: {overall['columns_with_any_finite_drift']}\n"
       f"- Features with changing null masks in at least one pair: {overall['columns_with_any_missing_mask_change']}\n"
       f"- Total per-pair changed null-mask cells (can repeat same source event): {overall['missing_mask_changes']}\n\n"
       "Full by-field and by-pair detail in CSV; this is NOT a certification of MA3, macro, "
       "corporate-action ground truth or the suitability of any correction.\n")
    print((out/"REPORT.md").read_text())

if __name__=="__main__":main()
