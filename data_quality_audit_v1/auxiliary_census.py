"""Read-only schema and missingness profile of auxiliary historical input panels."""
import argparse,json
from pathlib import Path
import pandas as pd
import numpy as np

def main():
    p=argparse.ArgumentParser()
    for key in ("r1","r2","r3","out"):p.add_argument("--"+key,required=True)
    a=p.parse_args();roots=[Path(getattr(a,f"r{i}")) for i in (1,2,3)]
    out=Path(a.out);out.mkdir(parents=True,exist_ok=False)
    features=[];profiles=[]
    for name in ("TI_EXTRA.parquet","TI_MACRO.parquet","TI_MODEL_RAW_SCORES.parquet"):
        data=[]
        for i,root in enumerate(roots,1):
            f=root/name
            if not f.is_file():raise ValueError(f"Missing historical artifact {name} repeat{i}")
            df=pd.read_parquet(f)
            data.append(df)
            keycols=[x for x in ("signal_date","ticker","macro_category","cluster_id") if x in df]
            if not keycols:raise ValueError(f"No audited natural key in {name}")
            unique=df.duplicated(keycols).sum()
            if unique:raise ValueError(f"Nonunique key in {name}, repeat{i}: {unique}")
            numeric=[c for c in df if c not in keycols and pd.api.types.is_numeric_dtype(df[c])]
            featureonly=[c for c in numeric if not (c.startswith(("target","fwd_","exit_","label_","y_")) or c.endswith("_target"))]
            x=df[featureonly].select_dtypes(include="number")
            arr=x.to_numpy(float)
            inf=int(np.isinf(arr).sum())
            if inf:raise ValueError(f"Inf in {name} repeat{i}")
            profiles.append(dict(panel=name,repeat=i,rows=len(df),total_cols=len(df.columns),
              columns=list(df.columns),keycols=keycols,numeric_cols=len(numeric),
              input_candidate_cols=len(featureonly),zero_input_candidates=len(featureonly)==0,
              null_cells=int(x.isna().sum().sum()),inf_cells=inf))
        ks=[x for x in ("signal_date","ticker","macro_category","cluster_id") if x in data[0]]
        for d in data[1:]:
            if set(d.columns)!=set(data[0].columns):raise ValueError(f"Schema drift in {name}")
        if len(set([len(d) for d in data]))!=1:
            raise ValueError(f"Different row counts in {name}")
        names=[c for c in data[0] if c not in ks and pd.api.types.is_numeric_dtype(data[0][c])
               and not(c.startswith(("target","fwd_","exit_","label_","y_")) or c.endswith("_target"))]
        z=[d.sort_values(ks).reset_index(drop=True) for d in data]
        for d in z[1:]:
            pd.testing.assert_frame_equal(d[ks],z[0][ks],check_exact=True)
        for namefeature in names:
            v=[d[namefeature].to_numpy(float) for d in z]
            for i,j in ((1,2),(1,3),(2,3)):
                a1,b1=v[i-1],v[j-1]
                mask=np.isfinite(a1)&np.isfinite(b1)
                dif=np.abs(a1[mask]-b1[mask])
                features.append(dict(panel=name,feature=namefeature,pair=f"{i}-{j}",
                    missing_mask_changes=int(np.count_nonzero(np.isfinite(a1)!=np.isfinite(b1))),
                    changed_finite_exact=int((dif>0).sum()),
                    max_abs_difference=float(dif.max()) if len(dif) else None))
    pd.DataFrame(features).to_csv(out/"AUX_FEATURE_DRIFT.csv",index=False)
    (out/"SCHEMA_AND_MISSINGNESS.json").write_text(json.dumps(profiles,indent=2,allow_nan=False,default=str)+"\n")
    dr=pd.DataFrame(features)
    lines=["# Original149 auxiliary data-only input audit", "",
       "This profile is NOT independent adjusted-price validation and is NOT MA3 RAW_FEATURE_PANEL.pkl certification.",""]
    for name in sorted(dr.panel.unique()):
        q=dr.loc[dr.panel.eq(name)]
        pr=next(x for x in profiles if x["panel"]==name)
        lines.append(f"- {name}: {pr['rows']} rows, {pr['input_candidate_cols']} numeric non-label columns, "+
                     f"{int(q.groupby('feature').missing_mask_changes.sum().gt(0).sum())} with changing missing masks; "+
                     f"{int(q.groupby('feature').changed_finite_exact.sum().gt(0).sum())} with value revisions")
    (out/"REPORT.md").write_text("\n".join(lines)+"\n")
    print((out/"REPORT.md").read_text())
if __name__=="__main__":main()
