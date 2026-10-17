"""Immutable archived score and simulator inputs for the eight-arm audit."""
from pathlib import Path
import json
import numpy as np
import pandas as pd
from paper_ltr_v2.replay import read_frame,sha
def verify_archives(base,rank):
    b=json.loads((Path(base)/"RESULT.json").read_text())
    r=json.loads((Path(rank)/"RETURN_RANK_NDCG"/"RESULT.json").read_text())
    if b.get("variant")!="BASE" or r.get("variant")!="RETURN_RANK_NDCG":
        raise ValueError("Wrong prediction archive")
    if b["input_sha256"]!=r["input_sha256"]:
        raise ValueError("Frozen market snapshots differ")
    for path,manifest in ((Path(base),b),(Path(rank)/"RETURN_RANK_NDCG",r)):
        for f in ("NATIVE_PREDICTIONS.parquet","COMMON_PREDICTIONS.parquet"):
            if sha(path/f)!=manifest["files_sha256"][f]:
                raise ValueError("Prediction file hash mismatch")
    return b,r
def aligned(a,b):
    cols=["signal_date","ticker"]
    aa=a[cols].sort_values(cols).reset_index(drop=True)
    bb=b[cols].sort_values(cols).reset_index(drop=True)
    if not aa.equals(bb) or aa.duplicated().any():raise ValueError("Coverage mismatch")
def load_titanium(source,learner,tail_on):
    p=Path(source)/("baseline_control" if learner=="BASE" else "candidate")
    annual=read_frame(p/"ANNUAL_PREDICTIONS.csv")
    tit=read_frame(p/"TIT_R_SOURCE_ONLY.csv")
    aligned(annual,tit)
    if not tail_on:
        z=annual[["signal_date","ticker","compact21"]].copy()
        z["TIT_R"]=z.groupby("signal_date").compact21.rank(method="average",pct=True)
        tit=tit.drop(columns="TIT_R").merge(z[["signal_date","ticker","TIT_R"]],
            on=["signal_date","ticker"],validate="one_to_one")
        tit=tit[["signal_date","entry_date","exit_date","ticker","TIT_R"]].sort_values(["signal_date","ticker"]).reset_index(drop=True)
    return tit
def load_ensemble(source,tit):
    a=read_frame(Path(source)/"baseline_control"/"ENSEMBLE_TAIL_OOS.csv")
    b=read_frame(Path(source)/"candidate"/"ENSEMBLE_TAIL_OOS.csv")
    aligned(a,b)
    for col in a.columns:
        if col!="BASE" and not a[col].equals(b[col]):
            raise ValueError("A non-Titanium signal changed "+col)
    aligned(a,tit)
    merged=a.merge(tit[["signal_date","ticker","TIT_R"]],on=["signal_date","ticker"],validate="one_to_one")
    if merged.TIT_R.isna().any():raise ValueError("Missing Titan value")
    merged["BASE"]=merged["TIT_R"]
    return merged[a.columns]
def verify_exact_original(npz,source):
    with np.load(npz,allow_pickle=False) as a,np.load(Path(source)/"FULL_UNIVERSE_PATH.npz",allow_pickle=False) as b:
        for col in ("dates","equity","turnover","d1","d2","weight1","margin","alt_idx"):
            x,y=a[col],b[col]
            if x.shape!=y.shape:raise ValueError("All-on original dimensions changed: "+col)
            if np.issubdtype(x.dtype,np.number):
                if not np.allclose(x,y,atol=1e-12,rtol=0,equal_nan=True):
                    raise ValueError("All-on original data changed: "+col)
            elif not np.array_equal(x,y):raise ValueError("Original date calendar changed")
