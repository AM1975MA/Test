"""Data-only gate. Compare Original149 Compact21 complete-case cohorts, no model fits."""
import argparse, json
from pathlib import Path
import numpy as np
import pandas as pd

def census(roots,feature_path,out):
    features=json.loads(Path(feature_path).read_text())
    if len(features)!=125 or len(set(features))!=125:raise ValueError("Invalid frozen 125-feature contract")
    out=Path(out);out.mkdir(parents=True,exist_ok=False)
    panels=[]
    per_feature=[]
    per_year=[]
    signature=[]
    for i,r in enumerate(roots,1):
        p=Path(r)/"TI_COMPACT.parquet"
        d=pd.read_parquet(p)
        d.signal_date=pd.to_datetime(d.signal_date)
        if d.duplicated(["signal_date","ticker"]).any():raise ValueError("Duplicated keys")
        if any(x not in d for x in features):raise ValueError("Feature contract mismatch")
        z=d[features].to_numpy(float)
        if np.isinf(z).any():raise ValueError("Infinite features")
        valid=np.isfinite(z)
        num=valid.sum(axis=1)
        d=d[["signal_date","ticker"]].copy()
        d["valid"]=num
        d["eligible_30"]=num>=30
        d["eligible_all"]=num==125
        d["eligible_116"]=valid[:,[j for j,n in enumerate(features) if not n.startswith("downvol")]].all(axis=1)
        d["repeat"]=i
        panels.append(d)
        miss=(~valid).sum(axis=0)
        for j,n in enumerate(features):
            per_feature.append(dict(repeat=i,feature=n,missing=int(miss[j]),missing_pct=float(miss[j]/len(d)),
                first_eligible_rows=int(valid[:,j].sum())))
        for y,g in d.groupby(d.signal_date.dt.year):
            per_year.append(dict(repeat=i,year=int(y),rows=len(g),eligible_30=int(g.eligible_30.sum()),
              eligible_all=int(g.eligible_all.sum()),eligible_116=int(g.eligible_116.sum()),
              distinct_etfs_any_full=int(g.loc[g.eligible_all,"ticker"].nunique()),
              signal_dates_with_full=int(g.loc[g.eligible_all,"signal_date"].nunique()),
              missing_feature_count_mean=float((125-g.valid).mean())))
        signature.append(d[["signal_date","ticker","eligible_30","eligible_all","eligible_116"]])
    p=pd.concat(panels,ignore_index=True)
    cross=p.pivot_table(index=["signal_date","ticker"],columns="repeat",
        values=["eligible_30","eligible_all","eligible_116"],aggfunc="first")
    if len(cross)!=len(panels[0]) or cross.isna().any().any():raise ValueError("Vintage keys mismatched")
    pair=[]
    for typ in ("eligible_30","eligible_all","eligible_116"):
        for a,b in ((1,2),(1,3),(2,3)):
            z=cross[typ]
            pair.append(dict(criterion=typ,pair=f"{a}-{b}",changed_eligibility=int((z[a]!=z[b]).sum()),
              both_eligible=int((z[a]&z[b]).sum()),either_eligible=int((z[a]|z[b]).sum())))
    pf=pd.DataFrame(per_feature)
    summary=dict(status="INPUT_COMPLETENESS_CENSUS_FINISHED",source="FROZEN_ORIGINAL_TI",rows_per_vintage=len(panels[0]),
        feature_count=125,criteria=["at_least_30","all_125","all_116_except_downvol_family"],
        by_vintage=[dict(repeat=i,rows=len(df),count_30=int(df.eligible_30.sum()),
            count_125=int(df.eligible_all.sum()),count_116=int(df.eligible_116.sum()),
            fraction_125=float(df.eligible_all.mean()),
            any_missing=int((df.valid<125).sum()),
            min_valid=int(df.valid.min()),max_valid=int(df.valid.max())) for i,df in enumerate(panels,1)],
        pairwise=pair,most_missing=pf.groupby("feature").missing.sum().sort_values(ascending=False).head(25).to_dict(),
        models_trained=False,cagr_computed=False,quality_certified=False)
    pf.to_csv(out/"PER_FEATURE_MISSINGNESS.csv",index=False)
    pd.DataFrame(per_year).to_csv(out/"PER_YEAR_COHORT_COVERAGE.csv",index=False)
    pd.DataFrame(pair).to_csv(out/"PAIRWISE_COHORT_DRIFT.csv",index=False)
    p.to_csv(out/"PER_ROW_VALID_COUNTS.csv",index=False)
    (out/"RESULT.json").write_text(json.dumps(summary,indent=2,allow_nan=False)+"\n")
    print(json.dumps(summary,indent=2,allow_nan=False))
if __name__=="__main__":
    p=argparse.ArgumentParser()
    for x in ("r1","r2","r3","features","out"):p.add_argument("--"+x,required=True)
    a=p.parse_args()
    census([a.r1,a.r2,a.r3],a.features,a.out)
