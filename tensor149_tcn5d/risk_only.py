"""Negative controls: rank ETF by past as-of realized volatility, no predictive model fit.
Matches exactly Tensor149 five-session anchors, as-of tradability, Top5 equal weights,
next open entries and conservative full 20-bp roundtrip costs.
"""
from __future__ import annotations
import argparse,json
from pathlib import Path
import numpy as np
import pandas as pd
from tensor149_tcn5d.features import FIELDS,load_frozen,daily_compact,labels_next_open,eligible
from tensor149_tcn5d.run import anchor_indices,LAST_MATURE,scoring_frame,nav_path

CONTROLS={"VOL21":"vol21","VOL63":"vol63","DOWNVOL21":"downvol21"}
def main():
    ap=argparse.ArgumentParser();ap.add_argument("--out",required=True)
    a=ap.parse_args()
    mats,raw_audit,roster_sha=load_frozen("evidence_v1/data/original149")
    date=mats["Open"].index;tickers=list(mats["Open"].columns)
    x=daily_compact(mats);ret,y=labels_next_open(mats,5)
    avail=eligible(x,mats["Open"].to_numpy(float))
    rows=[]
    for t in anchor_indices(date):
        if date[t]<pd.Timestamp("2017-01-01") or date[t]>pd.Timestamp("2026-06-30"):continue
        if date[t+6]>LAST_MATURE:continue
        ids=np.flatnonzero(avail[t])
        if len(ids)<100:raise ValueError("Panel too sparse")
        if not np.isfinite(ret[t,ids]).all():raise ValueError("Nonfinite mature price")
        for kind,f in CONTROLS.items():
            scores=x[t,ids,FIELDS.index(f)]
            if not np.isfinite(scores).all():
                # Missing historical volatility is not evidence of zero risk.
                scores=np.nan_to_num(scores,nan=-1000.,posinf=-1000.,neginf=-1000.)
            out=scoring_frame(date[t],ids,ret[t],y[t],{kind:scores},tickers)
            out[0]["t_idx"]=int(t)
            rows.extend(out)
    f=pd.DataFrame(rows);out=Path(a.out);out.mkdir(parents=True,exist_ok=True)
    f.to_csv(out/"RISK_ONLY_WEEKLY.csv",index=False)
    results={}
    for period in ("full","pilot"):
        df=f if period=="full" else f[f.date.between("2024-01-01","2025-12-31")]
        results[period]={}
        for kind,group in df.groupby("model"):
            nav,eco=nav_path(df,date,mats,kind)
            nav.to_csv(out/f"NAV_{period}_{kind}.csv",header=["NAV"],index_label="date")
            results[period][kind]={**eco,"rank_ic":float(group.rank_ic.mean()),
              "top5_overlap":float(group.top5_overlap.mean()),
              "top1_percentile":float(group.top1_realized_rank_pct.mean()),
              "topdecile_regret":float(group.topdecile_regret.mean())}
    summary={"status":"ORIGINAL149_RISK_ONLY_5D_NEGATIVE_CONTROL","roster_sha":roster_sha,
       "source_only_no_train":True,"risk_signals":CONTROLS,"comparison":results,
       "raw_manifest":raw_audit,"production_modified":False}
    (out/"RESULT.json").write_text(json.dumps(summary,indent=2,allow_nan=False)+"\n")
    print(json.dumps({"status":summary["status"],"comparison":results},indent=2),flush=True)
if __name__=="__main__":
    main()
