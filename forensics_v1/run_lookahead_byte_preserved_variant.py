#!/usr/bin/env python3
from __future__ import annotations
import argparse,csv,hashlib,importlib.util,json,os,shutil
from pathlib import Path
import numpy as np
import pandas as pd

def load_module(path:Path,tag:str):
    sp=importlib.util.spec_from_file_location("lookahead_bp_"+tag,path)
    m=importlib.util.module_from_spec(sp);sp.loader.exec_module(m);return m

def line_date(line:str,date_idx:int)->pd.Timestamp:
    row=next(csv.reader([line]))
    return pd.Timestamp(row[date_idx])

def byte_preserved_variant(src:Path,dst:Path,cutoff:pd.Timestamp,mode:str):
    if dst.exists(): shutil.rmtree(dst)
    dst.mkdir(parents=True)
    shutil.copyfile(src/"universe.csv",dst/"universe.csv")
    tickers=pd.read_csv(src/"universe.csv").ticker.astype(str).tolist()
    for ti,t in enumerate(tickers):
        sp=src/f"{t}.csv"; dp=dst/f"{t}.csv"
        with sp.open("r",encoding="utf-8",newline="") as f:
            header=f.readline()
            header_row=next(csv.reader([header]))
            date_idx=header_row.index("date")
            idx={c:header_row.index(c) for c in ["Open","High","Low","Close","Volume"]}
            body=f.readlines()
        out=[header]
        for li,line in enumerate(body):
            dt=line_date(line,date_idx)
            if dt<=cutoff:
                # Critical invariant: historical prefix is copied as exact original text bytes.
                out.append(line)
                continue
            if mode=="truncate":
                continue
            if mode=="mutate":
                row=next(csv.reader([line]))
                phase=float(li)
                fac=float(np.clip(1.0+0.20*np.sin(0.173*phase+0.071*ti)+0.08*np.cos(0.037*phase+0.113*ti),0.60,1.40))
                for c in ["Open","High","Low","Close"]:
                    j=idx[c]
                    try: row[j]=repr(float(row[j])*fac)
                    except Exception: pass
                j=idx["Volume"]
                try:
                    vf=1.0+0.35*np.sin(0.051*phase+ti)
                    row[j]=str(max(1,int(round(float(row[j])*vf))))
                except Exception: pass
                from io import StringIO
                s=StringIO(newline="")
                w=csv.writer(s,lineterminator="\n");w.writerow(row)
                out.append(s.getvalue())
            elif mode=="base":
                out.append(line)
            else:
                raise ValueError(mode)
        with dp.open("w",encoding="utf-8",newline="") as f: f.writelines(out)

def prefix_sha(raw:Path,cutoff:pd.Timestamp)->str:
    h=hashlib.sha256()
    u=pd.read_csv(raw/"universe.csv")
    for t in u.ticker.astype(str):
        p=raw/f"{t}.csv"
        with p.open("r",encoding="utf-8",newline="") as f:
            header=f.readline(); hr=next(csv.reader([header])); di=hr.index("date")
            h.update(t.encode()+b"\0");h.update(header.encode())
            for line in f:
                if line_date(line,di)<=cutoff: h.update(line.encode())
    return h.hexdigest()

def frame_hash(df,cols):
    q=df[list(cols)].copy()
    for c in q:
        if pd.api.types.is_datetime64_any_dtype(q[c]): q[c]=q[c].astype("datetime64[ns]").astype("int64")
    x=pd.util.hash_pandas_object(q,index=False).to_numpy(np.uint64)
    return hashlib.sha256(x.tobytes()).hexdigest()

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--raw",required=True);ap.add_argument("--compare-script",required=True)
    ap.add_argument("--cutoff",required=True);ap.add_argument("--mode",choices=["base","mutate","truncate"],required=True)
    ap.add_argument("--out",required=True)
    a=ap.parse_args(); raw=Path(a.raw).resolve(); cutoff=pd.Timestamp(a.cutoff); out=Path(a.out).resolve()
    if out.exists(): shutil.rmtree(out)
    out.mkdir(parents=True)
    use=raw
    if a.mode!="base":
        use=out/"raw_variant";byte_preserved_variant(raw,use,cutoff,a.mode)
        assert prefix_sha(raw,cutoff)==prefix_sha(use,cutoff),"historical prefix bytes changed"
    os.environ["FROZEN_149_ROOT"]=str(use.parent);os.environ["FROZEN_HOLDOUT70_ROOT"]=str(use.parent)
    mod=load_module(Path(a.compare_script).resolve(),a.mode)
    mod.FROZEN149=use;mod.FROZEN70=use;mod.OUT=out/"work"
    st=mod.build_source_only_state("original149",use)
    tit=st["tit"].copy();tit["signal_date"]=pd.to_datetime(tit.signal_date)
    pred=st["pred"].copy();pred["signal_date"]=pd.to_datetime(pred.signal_date)
    panel=pd.read_pickle(st["ma3_panel_path"]).copy();panel["signal_date"]=pd.to_datetime(panel.signal_date)
    for c in ["exit_date_21","exit_date_42","exit_date_63"]:
        if c in panel: panel[c]=pd.to_datetime(panel[c])
    p=pred.rename(columns={"ET_TAIL":"ET_RANK","XGB_TAIL":"XGB_RANK"})
    cal=tit[["signal_date","entry_date","exit_date"]].drop_duplicates().sort_values("signal_date").reset_index(drop=True)
    sc=mod.stage19.score_matrix(p,cal,st["candidate_tickers"])
    score=pd.DataFrame(sc,index=pd.DatetimeIndex(cal.signal_date),columns=st["candidate_tickers"]).stack(dropna=False).rename("FINAL_SCORE").reset_index()
    score.columns=["signal_date","ticker","FINAL_SCORE"]

    tit=tit[tit.signal_date<=cutoff].copy().sort_values(["signal_date","ticker"])
    pred=pred[pred.signal_date<=cutoff].copy().sort_values(["signal_date","ticker"])
    score=score[score.signal_date<=cutoff].copy().sort_values(["signal_date","ticker"])
    panel=panel[panel.signal_date<=cutoff].copy().sort_values(["signal_date","ticker"])
    from etf_trader.ma3.producer import FEATURES_42
    keep=["signal_date","ticker"]+[c for c in ["exit_date_21","exit_date_42","exit_date_63","target_rank_21","target_rank_42","target_rank_63"] if c in panel]
    keep += [c for c in FEATURES_42 if c in panel and c not in keep]
    panel=panel[keep]

    tit.to_parquet(out/"TIT.parquet",index=False);pred.to_parquet(out/"PRED.parquet",index=False)
    score.to_parquet(out/"SCORE.parquet",index=False);panel.to_parquet(out/"PANEL.parquet",index=False)
    fa=pd.read_csv(st["base"]/"ENSEMBLE_FIT_AUDIT.csv");fa.to_csv(out/"FIT_AUDIT.csv",index=False)
    meta={"status":"LOOKAHEAD_BYTE_PRESERVED_VARIANT_COMPLETE","mode":a.mode,"cutoff":str(cutoff.date()),
          "historical_prefix_sha256":prefix_sha(use,cutoff),"panel_rows":len(panel),"tit_rows":len(tit),"pred_rows":len(pred),
          "panel_feature_hash":frame_hash(panel,["signal_date","ticker"]+[c for c in FEATURES_42 if c in panel]),
          "tit_hash":frame_hash(tit,["signal_date","ticker","TIT_R"]),
          "pred_hash":frame_hash(pred,["signal_date","ticker","ET_TAIL","XGB_TAIL","TAIL_HYBRID"]),
          "score_hash":frame_hash(score,["signal_date","ticker","FINAL_SCORE"])}
    (out/"META.json").write_text(json.dumps(meta,indent=2)+"\n");print(json.dumps(meta,indent=2))
if __name__=="__main__":main()
