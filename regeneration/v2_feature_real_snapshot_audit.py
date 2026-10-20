#!/usr/bin/env python3
"""Frozen 149-ETF OHLCV feature coverage audit. Read-only and label-free."""
import argparse,sys,json
from pathlib import Path
import numpy as np
import pandas as pd
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"regeneration"/"campaign"))
from etf_trader.source_only import kernel as k, features as extra
from etf_trader.source_only.raw_io import load_ticker_csv_folder

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--raw",default="etf_trader_raw")
    p.add_argument("--out",default="runs/v2_feature_formula_audit")
    p.add_argument("--max-days",type=int,default=390)
    args=p.parse_args()
    out=Path(args.out);out.mkdir(parents=True,exist_ok=True)
    mats,cats,metadata=load_ticker_csv_folder(args.raw)
    if len(cats)!=149:raise RuntimeError("Expected 149 frozen tickers")
    mats={key:v.iloc[-args.max_days:].copy() for key,v in mats.items()}
    k.TICKER_CATEGORY=cats
    dates,compact,tail,D=k.build_features(mats)
    z=extra.build(mats,cats,dates)
    assert len(k.F2D_FEATURES)==125 and len(k.TAIL_FEATURES)==60
    assert len(extra.GROUPS["session"]+extra.GROUPS["residual"]+extra.GROUPS["flow"])==18
    tables=[("compact",compact,k.F2D_FEATURES),("tail",tail,k.TAIL_FEATURES),
            ("extra",z,sum(extra.GROUPS.values(),[]))]
    rows=[]
    for family,frame,names in tables:
        for col in names:
            x=pd.to_numeric(frame[col],errors="coerce")
            v=x.to_numpy(float)
            finite=v[np.isfinite(v)]
            rows.append({"group":family,"feature":col,"row_count":len(frame),
                "finite_count":len(finite),"missing_fraction":float(x.isna().mean()),
                "finite_unique":int(len(np.unique(finite))),
                "finite_min":float(np.min(finite)) if len(finite) else None,
                "finite_max":float(np.max(finite)) if len(finite) else None})
    q=pd.DataFrame(rows);q.to_csv(out/"FEATURE_COVERAGE_ALL203.csv",index=False)
    assert q.feature.size==203
    # Some rank/entropy variables can be constant for special ETF categories.
    # All 203 features must be actually computed on an authentic OHLCV sample.
    invalid=q[q.finite_count.eq(0)]
    if len(invalid):raise RuntimeError("All-NaN feature columns: "+invalid[["group","feature"]].to_json(orient="records"))
    C=mats["Close"]
    ret=np.log(C.where(C>0)).diff()
    historical=[]
    for h in (21,63,126):
        old=ret.where(ret<0).rolling(h,min_periods=max(10,h//2)).std(ddof=0)*np.sqrt(252)
        new=k.rolling_downvol(ret,h)
        old=old.reindex(dates);new=new.reindex(dates)
        historical.append({"feature":f"downvol{h}",
                           "old_nan_fraction":float(old.isna().to_numpy().mean()),
                           "new_nan_fraction":float(new.isna().to_numpy().mean()),
                           "new_finite_fraction":float(new.notna().to_numpy().mean()),
                           "changed_values":int((old.fillna(-999).to_numpy()!=new.fillna(-999).to_numpy()).sum())})
    pd.DataFrame(historical).to_csv(out/"DOWNVOL_OLD_VS_NEW.csv",index=False)
    (out/"MANIFEST.json").write_text(json.dumps({"source":"Frozen OHLCV raw run 39482809691",
        "source_format":"ticker OHLCV CSV 149","input_days":args.max_days,"dates":len(dates),
        "tickers":149,"features_compact":125,"features_tail":60,"features_extra":18,
        "labels_or_future_returns_used":False,"n_all_nan_features":len(invalid)},indent=2))
    print("FEATURE_CERT_PASS",{"compact":125,"tail":60,"extra":18,"all_nan":len(invalid)},flush=True)
    print(pd.DataFrame(historical).to_string(index=False),flush=True)

if __name__=="__main__":
    main()
