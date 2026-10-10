"""Audit cross-sectional robust deviation missingness; no model fitting or imputation."""
import argparse, ast, json
from pathlib import Path
import numpy as np
import pandas as pd

def feature_names():
    tree=ast.parse(Path("vendor/etf_trader_v2/src/etf_trader/source_only/kernel.py").read_text())
    return next(ast.literal_eval(n.value) for n in tree.body
        if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=="F2D_FEATURES" for t in n.targets))

def analyze(path, repeat, features):
    d=pd.read_parquet(path)
    d.signal_date=pd.to_datetime(d.signal_date)
    d=d.sort_values(["signal_date","ticker"]).reset_index(drop=True)
    if d.duplicated(["signal_date","ticker"]).any():raise ValueError("Duplicate keys")
    arr=d[features].to_numpy(float)
    if np.isinf(arr).any():raise ValueError("Infinite values")
    eligible=np.isfinite(arr).sum(axis=1)>=30
    dev=[f for f in features if f.endswith("_dev")]
    records=[];exceptions=[]
    for f in dev:
        base=f[:-4]
        if base not in d:raise ValueError(f"Missing source feature {base}")
        v=d[base].astype(float)
        # Identical semantics to canonical kernel cs_robust_dev: row median, MAD, replace 0 with NaN.
        med=v.groupby(d.signal_date).transform("median")
        absdev=(v-med).abs()
        mad=absdev.groupby(d.signal_date).transform("median")
        out=d[f].astype(float)
        bad=eligible & out.isna()
        input_missing=bad & v.isna()
        mad_zero=bad & v.notna() & mad.eq(0)
        mad_undefined=bad & v.notna() & mad.isna()
        unexplained=bad & ~(input_missing|mad_zero|mad_undefined)
        # Recompute original formula to certify its missingness, including cross-section ties.
        reconstructed=((v-med)/(1.4826*mad.replace(0,np.nan))).clip(-8,8)
        if not out.isna().equals(reconstructed.isna()):
            ix=np.flatnonzero((out.isna()!=reconstructed.isna()).to_numpy())
            raise ValueError(f"Source parity failure {f}: {len(ix)} missing-mask mismatches")
        if unexplained.any():
            z=d.loc[unexplained,["signal_date","ticker"]]
            exceptions.extend(dict(repeat=repeat,feature=f,date=str(r.signal_date.date()),ticker=r.ticker,
                source_value=float(v.loc[k]),mad=float(mad.loc[k])) for k,r in z.iterrows())
        records.append(dict(repeat=repeat,feature=f,base=base,eligible_missing=int(bad.sum()),
            source_missing=int(input_missing.sum()),mad_exact_zero=int(mad_zero.sum()),
            mad_undefined=int(mad_undefined.sum()),unexplained=int(unexplained.sum()),
            zero_mad_dates=int(d.loc[eligible & v.notna() & mad.eq(0),"signal_date"].nunique()),
            source_missing_dates=int(d.loc[input_missing,"signal_date"].nunique())))
    return d,records,exceptions

def main():
    p=argparse.ArgumentParser()
    for x in ("r1","r2","r3","out"):p.add_argument("--"+x,required=True)
    a=p.parse_args();out=Path(a.out);out.mkdir(parents=True,exist_ok=False)
    features=feature_names()
    allrows=[];exception=[];keys=[]
    for i in (1,2,3):
        d,r,e=analyze(Path(getattr(a,f"r{i}"))/"TI_COMPACT.parquet",i,features)
        allrows+=r;exception+=e
        keys.append(d[["signal_date","ticker"]])
    for z in keys[1:]:pd.testing.assert_frame_equal(keys[0],z,check_exact=True)
    f=pd.DataFrame(allrows);f.to_csv(out/"DEV_NAN_CAUSES.csv",index=False)
    pd.DataFrame(exception,columns=["repeat","feature","date","ticker","source_value","mad"]).to_csv(out/"UNEXPLAINED.csv",index=False)
    totals=f.groupby("repeat")[["eligible_missing","source_missing","mad_exact_zero","mad_undefined","unexplained"]].sum().reset_index()
    details=f.loc[f.repeat.eq(1)].sort_values("eligible_missing",ascending=False).head(18).to_dict("records")
    report={"status":"DEV_NAN_CAUSAL_AUDIT_PASS" if not f.unexplained.any() else "DEV_NAN_CAUSAL_AUDIT_UNEXPLAINED",
        "num_dev_features":int(len(f)//3),"by_vintage":totals.to_dict("records"),
        "largest_devs_repeat1":details,"source_panel_changed":False,"model_trained":False,
        "strict_no_nan_gate_not_yet_certified":True}
    (out/"RESULT.json").write_text(json.dumps(report,indent=2,allow_nan=False)+"\n")
    print(json.dumps(report,indent=2,allow_nan=False))
if __name__=="__main__":main()
