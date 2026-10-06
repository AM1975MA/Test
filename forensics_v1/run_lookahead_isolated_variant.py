#!/usr/bin/env python3
from __future__ import annotations
import argparse, importlib.util, json, os, shutil, hashlib
from pathlib import Path
import numpy as np
import pandas as pd

def load_module(path: Path, tag: str):
    sp=importlib.util.spec_from_file_location("iso_"+tag,path)
    m=importlib.util.module_from_spec(sp); sp.loader.exec_module(m); return m

def copy_variant(src:Path,dst:Path,cutoff:pd.Timestamp,mode:str):
    if dst.exists(): shutil.rmtree(dst)
    dst.mkdir(parents=True)
    shutil.copyfile(src/"universe.csv",dst/"universe.csv")
    tickers=pd.read_csv(src/"universe.csv").ticker.astype(str).tolist()
    for ti,t in enumerate(tickers):
        d=pd.read_csv(src/f"{t}.csv")
        dates=pd.to_datetime(d["date"])
        if mode=="truncate":
            d=d.loc[dates<=cutoff].copy()
        elif mode=="mutate":
            m=dates>cutoff
            if m.any():
                idx=np.arange(len(d),dtype=float)
                fac=1.0+0.20*np.sin(0.173*idx+0.071*ti)+0.08*np.cos(0.037*idx+0.113*ti)
                fac=np.clip(fac,0.60,1.40)
                mm=m.to_numpy()
                for c in ["Open","High","Low","Close"]:
                    d.loc[m,c]=pd.to_numeric(d.loc[m,c],errors="coerce").to_numpy(float)*fac[mm]
                d.loc[m,"Volume"]=np.maximum(1,np.round(pd.to_numeric(d.loc[m,"Volume"],errors="coerce").to_numpy(float)*(1.0+0.35*np.sin(0.051*idx[mm]+ti)))).astype("int64")
        elif mode!="base":
            raise ValueError(mode)
        d.to_csv(dst/f"{t}.csv",index=False)

def hash_frame(df: pd.DataFrame, cols):
    q=df[list(cols)].copy()
    for c in q.columns:
        if np.issubdtype(q[c].dtype, np.datetime64):
            q[c]=q[c].astype("datetime64[ns]").astype("int64")
    h=pd.util.hash_pandas_object(q,index=False).to_numpy(np.uint64)
    return hashlib.sha256(h.tobytes()).hexdigest()

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--raw",required=True)
    ap.add_argument("--compare-script",required=True)
    ap.add_argument("--cutoff",required=True)
    ap.add_argument("--mode",choices=["base","mutate","truncate"],required=True)
    ap.add_argument("--out",required=True)
    a=ap.parse_args()
    raw=Path(a.raw).resolve(); cutoff=pd.Timestamp(a.cutoff); out=Path(a.out).resolve()
    if out.exists(): shutil.rmtree(out)
    out.mkdir(parents=True)
    use_raw=raw
    if a.mode!="base":
        use_raw=out/"raw_variant"; copy_variant(raw,use_raw,cutoff,a.mode)
    os.environ["FROZEN_149_ROOT"]=str(use_raw.parent)
    os.environ["FROZEN_HOLDOUT70_ROOT"]=str(use_raw.parent)
    mod=load_module(Path(a.compare_script).resolve(),a.mode)
    mod.FROZEN149=use_raw; mod.FROZEN70=use_raw; mod.OUT=out/"work"
    state=mod.build_source_only_state("original149",use_raw)

    tit=state["tit"].copy(); tit["signal_date"]=pd.to_datetime(tit["signal_date"])
    pred=state["pred"].copy(); pred["signal_date"]=pd.to_datetime(pred["signal_date"])
    panel=pd.read_pickle(state["ma3_panel_path"]).copy(); panel["signal_date"]=pd.to_datetime(panel["signal_date"])
    p=pred.rename(columns={"ET_TAIL":"ET_RANK","XGB_TAIL":"XGB_RANK"}).copy()
    cal=tit[["signal_date","entry_date","exit_date"]].drop_duplicates().sort_values("signal_date").reset_index(drop=True)
    score=mod.stage19.score_matrix(p,cal,state["candidate_tickers"])
    score=(pd.DataFrame(score,index=pd.DatetimeIndex(cal.signal_date),columns=state["candidate_tickers"]).stack(dropna=False).rename("FINAL_SCORE").reset_index())
    score.columns=["signal_date","ticker","FINAL_SCORE"]

    tit=tit[tit.signal_date<=cutoff].copy()
    pred=pred[pred.signal_date<=cutoff].copy()
    score=score[score.signal_date<=cutoff].copy()
    panel=panel[panel.signal_date<=cutoff].copy()

    keep_panel=[c for c in ["signal_date","ticker","exit_date_63","target_rank_21","target_rank_42","target_rank_63"] if c in panel.columns]
    from etf_trader.ma3.producer import FEATURES_42
    keep_panel += [c for c in FEATURES_42 if c in panel.columns and c not in keep_panel]
    panel_small=panel[keep_panel].copy().sort_values(["signal_date","ticker"]).reset_index(drop=True)

    tit.to_parquet(out/"TIT.parquet",index=False)
    pred.to_parquet(out/"PRED.parquet",index=False)
    score.to_parquet(out/"SCORE.parquet",index=False)
    panel_small.to_parquet(out/"PANEL.parquet",index=False)
    fa=pd.read_csv(state["base"]/"ENSEMBLE_FIT_AUDIT.csv")
    fa.to_csv(out/"FIT_AUDIT.csv",index=False)
    meta={
        "status":"LOOKAHEAD_ISOLATED_VARIANT_COMPLETE",
        "mode":a.mode,"cutoff":str(cutoff.date()),
        "tit_rows":len(tit),"pred_rows":len(pred),"score_rows":len(score),"panel_rows":len(panel_small),
        "panel_hash":hash_frame(panel_small,panel_small.columns),
        "tit_hash":hash_frame(tit,["signal_date","ticker","TIT_R"]),
        "pred_hash":hash_frame(pred,["signal_date","ticker","ET_TAIL","XGB_TAIL","TAIL_HYBRID"]),
        "score_hash":hash_frame(score,["signal_date","ticker","FINAL_SCORE"]),
    }
    (out/"META.json").write_text(json.dumps(meta,indent=2)+"\n")
    print(json.dumps(meta,indent=2))
if __name__=="__main__": main()
