#!/usr/bin/env python3
from __future__ import annotations
import argparse,json
from pathlib import Path
import numpy as np
import pandas as pd

def numcmp(A,B,keys,cols):
    x=A[keys+cols].merge(B[keys+cols],on=keys,suffixes=("_a","_b"),how="inner")
    out={}
    for c in cols:
        u=pd.to_numeric(x[c+"_a"],errors="coerce").to_numpy(float)
        v=pd.to_numeric(x[c+"_b"],errors="coerce").to_numpy(float)
        m=np.isfinite(u)&np.isfinite(v); d=np.abs(u-v)
        out[c]={"n":int(m.sum()),"changed_gt1e12":int(np.sum(m&(d>1e-12))),"max_abs":float(np.max(d[m])) if m.any() else None,"exact_pass":bool(not np.any(m&(d>1e-12)))}
    return out

def load(root,mode):
    p=root/mode
    return {
        "meta":json.loads((p/"META.json").read_text()),
        "tit":pd.read_parquet(p/"TIT.parquet"),
        "pred":pd.read_parquet(p/"PRED.parquet"),
        "score":pd.read_parquet(p/"SCORE.parquet"),
        "panel":pd.read_parquet(p/"PANEL.parquet"),
        "audit":pd.read_csv(p/"FIT_AUDIT.csv"),
    }

def main():
    ap=argparse.ArgumentParser(); ap.add_argument("--root",required=True); ap.add_argument("--out",required=True); a=ap.parse_args()
    root=Path(a.root); R={m:load(root,m) for m in ["base","mutate","truncate"]}
    res={"status":"LOOKAHEAD_ISOLATED_COMPARISON_COMPLETE","comparisons":{}}
    for mode in ["mutate","truncate"]:
        A=R["base"]; B=R[mode]; q={}
        panel_cols=[c for c in A["panel"].columns if c not in ["signal_date","ticker","exit_date_63"] and c in B["panel"].columns]
        q["panel"]=numcmp(A["panel"],B["panel"],["signal_date","ticker"],panel_cols)
        q["panel_all_exact"]=bool(all(v["exact_pass"] for v in q["panel"].values()))
        q["tit"]=numcmp(A["tit"],B["tit"],["signal_date","ticker"],["TIT_R"])["TIT_R"]
        q["predictions"]=numcmp(A["pred"],B["pred"],["signal_date","ticker"],["ET_TAIL","XGB_TAIL","TAIL_HYBRID"])
        q["score"]=numcmp(A["score"],B["score"],["signal_date","ticker"],["FINAL_SCORE"])["FINAL_SCORE"]
        fa=B["audit"].copy()
        fa["max_train_exit63"]=pd.to_datetime(fa["max_train_exit63"]); fa["cutoff"]=pd.to_datetime(fa["cutoff"])
        q["maturity_gate"]={"rows":len(fa),"violations":int((fa.max_train_exit63>=fa.cutoff).sum()),"PASS":bool((fa.max_train_exit63<fa.cutoff).all())}
        q["PASS"]=bool(q["panel_all_exact"] and q["tit"]["exact_pass"] and all(v["exact_pass"] for v in q["predictions"].values()) and q["score"]["exact_pass"] and q["maturity_gate"]["PASS"])
        res["comparisons"][mode]=q
    res["PASS"]=bool(all(v["PASS"] for v in res["comparisons"].values()))
    Path(a.out).write_text(json.dumps(res,indent=2)+"\n")
    print(json.dumps(res,indent=2))
if __name__=="__main__": main()
