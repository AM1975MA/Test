#!/usr/bin/env python3
from __future__ import annotations
import argparse, importlib.util, json, os, shutil, sys
from pathlib import Path
import pandas as pd

def load_compare(path: Path):
    sp=importlib.util.spec_from_file_location("q4_full_compare", path)
    m=importlib.util.module_from_spec(sp); sp.loader.exec_module(m); return m

def build_quant_tit(mod, titanium_raw: Path, out: Path, decimals: int):
    from etf_trader.source_only import kernel as k
    from etf_trader.source_only.features import build as build_extra_features
    from etf_trader.source_only.models import fit_predict, variants
    from etf_trader.source_only.raw_io import load_ticker_csv_folder
    out.mkdir(parents=True, exist_ok=True)
    mats,cats,_=load_ticker_csv_folder(titanium_raw)
    cols=list(mats["Close"].columns)
    k.ALL_TICKERS=sorted(cols)
    k.TICKER_CATEGORY=cats
    k.CATEGORY_TICKERS={c:sorted([t for t in cols if cats[t]==c]) for c in sorted(set(cats.values()))}
    dates=k.month_end_dates(mats["Close"].index)
    if len(dates) and dates[-1]==mats["Close"].index[-1]:
        dates=dates[:-1]
    _,compact,tail,_=k.build_features(mats)
    compact=compact[compact.signal_date.isin(dates)].copy()
    tail=tail[tail.signal_date.isin(dates)].copy()
    compact=k.add_labels(compact,mats["Open"],dates)
    tail=k.add_labels(tail,mats["Open"],dates)
    compact.loc[:,k.F2D_FEATURES]=compact[k.F2D_FEATURES].round(decimals)
    tail_no_labels=tail.drop(columns=[c for c in tail if c.startswith(("fwd_","target_","exit_")) or c in ["entry_date","y_tailmix"]])
    macro,mfeatures=k.build_macro_panel(tail_no_labels,tail)
    extra=build_extra_features(mats,cats,dates)
    pred=fit_predict(k,compact,tail,macro,mfeatures,extra,out/"annual_models")
    pred=pred[(pred.signal_date>="2017-01-31")&(pred.signal_date<="2026-06-30")].copy()
    baseline=variants(pred)["baseline"].rename(columns={"score":"TIT_R"})
    calendar=pred[["signal_date","ticker","entry_date","exit_date"]].drop_duplicates(["signal_date","ticker"])
    panel=baseline.merge(calendar,on=["signal_date","ticker"],how="inner",validate="one_to_one")
    panel=panel[["signal_date","entry_date","exit_date","ticker","TIT_R"]].sort_values(["signal_date","ticker"])
    p=out/"TIT_R_SOURCE_ONLY.csv"; panel.to_csv(p,index=False)
    return panel,p

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--raw",required=True)
    ap.add_argument("--compare-script",required=True)
    ap.add_argument("--out",required=True)
    ap.add_argument("--decimals",type=int,default=4)
    a=ap.parse_args()
    raw=Path(a.raw).resolve(); out=Path(a.out).resolve()
    if out.exists(): shutil.rmtree(out)
    out.mkdir(parents=True)
    os.environ["FROZEN_149_ROOT"]=str(raw.parent)
    os.environ["FROZEN_HOLDOUT70_ROOT"]=str(raw.parent)
    mod=load_compare(Path(a.compare_script).resolve())
    mod.FROZEN149=raw; mod.FROZEN70=raw; mod.OUT=out/"work"
    candidate,titanium_raw,candidate_tickers=mod.prepare_candidate_and_titanium_raw("original149_q4",raw)
    base=mod.OUT/"original149_q4"
    tit_out=base/"titanium_q4"
    tit_full,tit_full_path=build_quant_tit(mod,titanium_raw,tit_out,a.decimals)
    tit=tit_full[tit_full.ticker.astype(str).isin(candidate_tickers)].copy()
    if tit.ticker.nunique()!=len(candidate_tickers):
        raise RuntimeError("Titanium candidate coverage incomplete")
    tit_path=base/"TIT_R_CANDIDATES_ONLY.csv"; tit.to_csv(tit_path,index=False)
    ma3_out=base/"ma3_panel"
    mod.run([sys.executable,str(mod.ETF/"scripts"/"build_ma3_panel_source_only.py"),"--data",str(candidate),"--cluster-data",str(candidate),"--output",str(ma3_out)])
    panel=pd.read_pickle(ma3_out/"RAW_FEATURE_PANEL.pkl")
    fit=mod.fit_ensemble_producer(panel,tit,candidate_tickers,n_jobs=2)
    if not bool(fit.fit_audit["maturity_ok"].all()):
        raise RuntimeError("hybrid maturity audit failed")
    pred_path=base/"ENSEMBLE_TAIL_OOS.csv"; fit.predictions.to_csv(pred_path,index=False)
    fit.fit_audit.to_csv(base/"ENSEMBLE_FIT_AUDIT.csv",index=False)
    state={
      "base":base,"candidate_raw":candidate,"titanium_raw":titanium_raw,
      "candidate_tickers":candidate_tickers,"tit":tit,"tit_full_path":tit_full_path,
      "tit_candidate_path":tit_path,"pred":fit.predictions,"pred_path":pred_path,
      "ma3_panel_path":ma3_out/"RAW_FEATURE_PANEL.pkl"
    }
    result=mod.replay_full_universe(state)
    result["quantization"]={"F2D_features":125,"decimals":a.decimals}
    (out/"RESULT_Q4.json").write_text(json.dumps(result,indent=2)+"\n")
    shutil.copyfile(base/"DAILY_LEADERS.csv",out/"DAILY_LEADERS_Q4.csv")
    print(json.dumps(result,indent=2))
if __name__=="__main__":
    main()
