#!/usr/bin/env python3
from __future__ import annotations

import ast, hashlib, json, time
from pathlib import Path
import numpy as np
import pandas as pd
import yfinance as yf

START="2004-01-01"
END_EXCLUSIVE="2026-08-01"
PRE2017_CUTOFF=pd.Timestamp("2017-01-31")
LAST_REQUIRED=pd.Timestamp("2026-07-31")
MIN_PRE2017_ROWS=1260
MAX_ABS_ADJ_DAILY_RETURN=0.25

# MA3 source architecture: 7 dynamic clusters * min 8 members + defensive sleeve.
# 12 in each of the five non-defensive macro categories = 60 dynamic names;
# 10 defensive names => 70 total, preserving the original clustering constants.
QUOTAS={
 "C01_US_BROAD_STYLE":12,
 "C02_US_SECTOR_THEME":12,
 "C03_DEVELOPED_GLOBAL":12,
 "C04_EMERGING":12,
 "C05_BONDS_CASH_CREDIT":10,
 "C06_REAL_ASSETS":12,
}

CANDIDATES={
 "C01_US_BROAD_STYLE":["VOO","VIG","VYM","SCHG","IUSG","IUSV","USMV","SPHQ","NOBL","SDY","PRF","RWL","VV","MGK","VOE","VOT","VBK","VBR","IJS","IJK","SLYV","SLYG","SCHV","SCHM","SPYG","SPYV","VIOO","VIOV","VIOG","FNDA","QVAL"],
 "C02_US_SECTOR_THEME":["VGT","VFH","VHT","VDC","VCR","VPU","VAW","VOX","XOP","XME","XHB","XSD","KIE","PSI","PBW","QCLN","SKYY","ROBO","CIBR","XAR","PTH","PJP","PBE"],
 "C03_DEVELOPED_GLOBAL":["VPL","SCHF","SPDW","EFV","EFG","SCZ","HEDJ","DXJ","DBEF","EFAV","IDLV","DTH","PID","DWX","IQDF","FNDF","GWX","VSS","SCHC","IDMO"],
 "C04_EMERGING":["FM","EEMS","EWX","EELV","PIE","PXH","FNDE","XSOE","SPEM","EEB","BKF","ILF","EWW","ECH","EPU","GXG","VNM","AFK","NGE","EGPT","EMFM","UAE","QAT","KSA"],
 "C05_BONDS_CASH_CREDIT":["BSV","BIV","BLV","GOVT","SCHR","SCHO","SCHZ","IGSB","IGIB","USIG","FLOT","FLRN","PFF","PGX","CMF","SUB","SHM","TFI","MINT","ICSH","VTIP","STIP","LTPZ","HYD","HYMB"],
 "C06_REAL_ASSETS":["SCHH","USRT","REM","REZ","VNQI","GNR","PICK","COPX","SIL","SILJ","PHO","FIW","CGW","IGF","RJI","DBE","RJA","RJN","PDBC","TOLZ","XLRE","FREL","KBWY"],
}

def sha256_bytes(b:bytes)->str:return hashlib.sha256(b).hexdigest()
def sha256(path:Path)->str:return sha256_bytes(path.read_bytes())

def original_149()->set[str]:
    src=Path("regeneration/etf_trader_raw.py").read_text(encoding="utf-8")
    tree=ast.parse(src);cats=None
    for node in tree.body:
        if isinstance(node,ast.Assign):
            for target in node.targets:
                if isinstance(target,ast.Name) and target.id=="CATS":cats=ast.literal_eval(node.value)
    if cats is None:raise RuntimeError("cannot recover canonical CATS")
    return {str(t).upper() for xs in cats.values() for t in xs}

def download_one(ticker:str):
    d=None;last_error=None
    for attempt in range(5):
        try:
            d=yf.download(ticker,start=START,end=END_EXCLUSIVE,auto_adjust=False,actions=False,progress=False,threads=False,timeout=45)
            if d is not None and not d.empty:break
            last_error="empty"
        except Exception as e:last_error=f"download_error:{type(e).__name__}:{e}"
        time.sleep(min(2**attempt,8))
    if d is None or d.empty:return None,last_error or "empty"
    if isinstance(d.columns,pd.MultiIndex):d.columns=d.columns.get_level_values(0)
    d=d.reset_index();need=["Date","Open","High","Low","Close","Adj Close","Volume"]
    if any(c not in d.columns for c in need):return None,"missing_columns"
    raw_close=pd.to_numeric(d["Close"],errors="coerce");adj=pd.to_numeric(d["Adj Close"],errors="coerce");f=adj/raw_close.replace(0,np.nan)
    q=pd.DataFrame({"date":pd.to_datetime(d["Date"]).dt.tz_localize(None),"Open":pd.to_numeric(d["Open"],errors="coerce")*f,"High":pd.to_numeric(d["High"],errors="coerce")*f,"Low":pd.to_numeric(d["Low"],errors="coerce")*f,"Close":adj,"Volume":pd.to_numeric(d["Volume"],errors="coerce")}).dropna().sort_values("date").drop_duplicates("date",keep="last")
    if q.empty:return None,"no_valid_rows"
    if (q[["Open","High","Low","Close"]]<=0).any().any() or (q["Volume"]<0).any():return None,"invalid_values"
    bad=(q["Low"]>q[["Open","Close"]].min(axis=1)+1e-8)|(q["High"]<q[["Open","Close"]].max(axis=1)-1e-8)
    if bad.any():return None,f"ohlc_incoherent:{int(bad.sum())}"
    q=q[q.date<=LAST_REQUIRED].copy();pre=q[q.date<=PRE2017_CUTOFF]
    if len(pre)<MIN_PRE2017_ROWS:return None,f"insufficient_pre2017_rows:{len(pre)}"
    if q.date.max()<LAST_REQUIRED:return None,f"ends_early:{q.date.max().date()}"
    mx=float(q.Close.pct_change(fill_method=None).abs().max(skipna=True))
    if not np.isfinite(mx) or mx>MAX_ABS_ADJ_DAILY_RETURN:return None,f"extreme_adjusted_daily_return:{mx:.6f}"
    return q,None

def main()->int:
    out=Path("holdout70/output");raw=out/"raw_ticker_csv";raw.mkdir(parents=True,exist_ok=True)
    original=original_149();candidate_flat=[t for xs in CANDIDATES.values() for t in xs]
    ov=sorted(set(candidate_flat)&original)
    if ov:raise RuntimeError(f"candidate pool overlaps original universe: {ov}")
    selected=[];rejected=[];data={}
    for cat,pool in CANDIDATES.items():
        need=QUOTAS[cat];chosen=0
        for ticker in pool:
            q,reason=download_one(ticker)
            if q is None:
                rejected.append({"ticker":ticker,"macro_category":cat,"reason":reason});print("REJECT",cat,ticker,reason,flush=True);continue
            rec={"ticker":ticker,"macro_category":cat,"rows":int(len(q)),"first":str(q.date.min().date()),"last":str(q.date.max().date()),"pre2017_rows":int((q.date<=PRE2017_CUTOFF).sum()),"max_abs_adj_daily_return":float(q.Close.pct_change(fill_method=None).abs().max())}
            selected.append(rec);data[ticker]=q;chosen+=1;print("SELECT",cat,ticker,chosen,"/",need,flush=True)
            if chosen>=need:break
        if chosen!=need:raise RuntimeError(f"quota not met for {cat}: selected {chosen}, required {need}")
    if len(selected)!=70:raise RuntimeError(f"expected 70 selected ETFs, got {len(selected)}")
    tickers=[r["ticker"] for r in selected];overlap=sorted(set(tickers)&original)
    if overlap:raise RuntimeError(f"FINAL HOLDOUT OVERLAP WITH ORIGINAL149: {overlap}")
    if len(set(tickers))!=70:raise RuntimeError("duplicate ticker")
    hashes={}
    for r in selected:
        t=r["ticker"];q=data[t].copy();q["date"]=q.date.dt.strftime("%Y-%m-%d");p=raw/f"{t}.csv";q.to_csv(p,index=False,float_format="%.17g");hashes[t]=sha256(p)
    pd.DataFrame(selected)[["ticker","macro_category"]].to_csv(raw/"universe.csv",index=False)
    pd.DataFrame(selected).to_csv(out/"coverage.csv",index=False);pd.DataFrame(rejected).to_csv(out/"rejected.csv",index=False)
    for fld in ["Open","High","Low","Close","Volume"]:
        pd.concat([data[t].set_index("date")[[fld]].rename(columns={fld:t}) for t in tickers],axis=1).sort_index().to_parquet(out/f"{fld.upper()}.parquet")
    spec=json.dumps({"quotas":QUOTAS,"candidates":CANDIDATES},sort_keys=True).encode()
    manifest={"status":"HOLDOUT70_FROZEN_QUALITY_GATED","selection_rule":"first coverage-valid ticker in frozen per-cluster candidate order until quota; no return/performance criterion","provider":"Yahoo Finance via yfinance","requested_start":START,"last_included":str(LAST_REQUIRED.date()),"pre2017_min_rows":MIN_PRE2017_ROWS,"max_abs_adjusted_daily_return":MAX_ABS_ADJ_DAILY_RETURN,"original_universe_count":len(original),"selected_count":len(tickers),"intersection_with_original149":overlap,"quotas":QUOTAS,"candidate_spec_sha256":sha256_bytes(spec),"selected_tickers":tickers,"file_sha256":hashes,"performance_used_for_selection":False,"ma3_architecture_gate":{"n_dynamic":60,"n_defensive":10,"minimum_required_dynamic":56,"minimum_required_defensive":8,"pass":True}}
    (out/"manifest.json").write_text(json.dumps(manifest,indent=2)+"\n",encoding="utf-8")
    print("FINAL_MANIFEST");print(json.dumps({k:v for k,v in manifest.items() if k!="file_sha256"},indent=2));return 0

if __name__=="__main__":raise SystemExit(main())
