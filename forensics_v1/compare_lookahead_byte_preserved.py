#!/usr/bin/env python3
from __future__ import annotations
import argparse,json
from pathlib import Path
import numpy as np
import pandas as pd
from etf_trader.ma3.producer import FEATURES_42

KEY=["signal_date","ticker"]
def load(p):
    return {"meta":json.loads((p/"META.json").read_text()),"panel":pd.read_parquet(p/"PANEL.parquet"),
            "tit":pd.read_parquet(p/"TIT.parquet"),"pred":pd.read_parquet(p/"PRED.parquet"),
            "score":pd.read_parquet(p/"SCORE.parquet"),"audit":pd.read_csv(p/"FIT_AUDIT.csv")}
def cmp(A,B,cols,keys=KEY):
    x=A[keys+cols].merge(B[keys+cols],on=keys,suffixes=("_a","_b"),how="inner");o={}
    for c in cols:
        u=pd.to_numeric(x[c+"_a"],errors="coerce").to_numpy(float);v=pd.to_numeric(x[c+"_b"],errors="coerce").to_numpy(float)
        m=np.isfinite(u)&np.isfinite(v);d=np.abs(u-v)
        o[c]={"n":int(m.sum()),"changed_gt1e12":int(np.sum(m&(d>1e-12))),"max_abs":float(np.max(d[m])) if m.any() else None,
              "exact_pass":bool(not np.any(m&(d>1e-12)))}
    return o
def main():
    ap=argparse.ArgumentParser();ap.add_argument("--root",required=True);ap.add_argument("--out",required=True);a=ap.parse_args()
    root=Path(a.root);R={m:load(root/m) for m in ["base","mutate","truncate"]}
    cutoff=pd.Timestamp(R["base"]["meta"]["cutoff"])
    res={"status":"LOOKAHEAD_BYTE_PRESERVED_COMPARISON_COMPLETE","cutoff":str(cutoff.date()),"comparisons":{}}
    for mode in ["mutate","truncate"]:
        A=R["base"];B=R[mode];q={}
        q["prefix_bytes_exact"]=A["meta"]["historical_prefix_sha256"]==B["meta"]["historical_prefix_sha256"]
        feats=[c for c in FEATURES_42 if c in A["panel"] and c in B["panel"]]
        q["features"]=cmp(A["panel"],B["panel"],feats)
        q["features_all_exact"]=all(v["exact_pass"] for v in q["features"].values())
        q["matured_targets"]={}
        for h in [21,42,63]:
            ex=f"exit_date_{h}";tg=f"target_rank_{h}"
            if ex not in A["panel"] or tg not in A["panel"]: continue
            aa=A["panel"][pd.to_datetime(A["panel"][ex])<=cutoff]
            bb=B["panel"][pd.to_datetime(B["panel"][ex])<=cutoff]
            q["matured_targets"][tg]=cmp(aa,bb,[tg])[tg]
        q["matured_targets_all_exact"]=all(v["exact_pass"] for v in q["matured_targets"].values())
        q["tit"]=cmp(A["tit"],B["tit"],["TIT_R"])["TIT_R"]
        q["predictions"]=cmp(A["pred"],B["pred"],["ET_TAIL","XGB_TAIL","TAIL_HYBRID"])
        q["score"]=cmp(A["score"],B["score"],["FINAL_SCORE"])["FINAL_SCORE"]
        fa=B["audit"].copy();fa["max_train_exit63"]=pd.to_datetime(fa.max_train_exit63);fa["cutoff"]=pd.to_datetime(fa.cutoff)
        q["maturity_gate"]={"rows":len(fa),"violations":int((fa.max_train_exit63>=fa.cutoff).sum()),"PASS":bool((fa.max_train_exit63<fa.cutoff).all())}
        q["PASS"]=bool(q["prefix_bytes_exact"] and q["features_all_exact"] and q["matured_targets_all_exact"] and q["tit"]["exact_pass"]
                       and all(v["exact_pass"] for v in q["predictions"].values()) and q["score"]["exact_pass"] and q["maturity_gate"]["PASS"])
        res["comparisons"][mode]=q
    res["PASS"]=bool(all(v["PASS"] for v in res["comparisons"].values()))
    Path(a.out).write_text(json.dumps(res,indent=2)+"\n");print(json.dumps(res,indent=2))
if __name__=="__main__":main()
