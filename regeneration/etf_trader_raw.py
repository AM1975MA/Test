#!/usr/bin/env python3
from pathlib import Path
import json, hashlib, pandas as pd, yfinance as yf

CATS={
"C01_US_BROAD_STYLE":['DIA','IJR','SCHD','QQQ','QUAL','RSP','DGRO','IJH','IWF','HDV','MDY','SCHB','IWM','MTUM','SCHX','SPY','IVV','VTI','VO','VB','VUG','VTV','IWD','IWN','SPLV'],
"C02_US_SECTOR_THEME":['PPA','SMH','SOXX','IGV','IHI','KBE','HACK','IYT','KRE','IBB','ICLN','ITA','FDN','TAN','XBI','XLK','XLF','XLE','XLV','XLI','XLY','XLP','XLU','XLB','XRT'],
"C03_DEVELOPED_GLOBAL":['ACWI','EWL','EWP','EWA','EWN','IEFA','EFA','EWH','EWQ','EWC','EWD','EWJ','EWG','EWI','EWU','VEA','VEU','VGK','EWK','EWO','EIRL','EIS','EPOL','ENZL','EPP'],
"C04_EMERGING":['EWS','EWY','FXI','ASHR','INDA','VWO','EWT','IEMG','KWEB','EEM','MCHI','TUR','AAXJ','EWZ','EZA','EIDO','EWM','THD','EPHE','SCHE','DEM','DGS','EPI','ARGT'],
"C05_BONDS_CASH_CREDIT":['AGG','BIL','EMB','IEF','IEI','LQD','BNDX','HYG','MUB','BND','JNK','SCHP','EDV','SHY','TLT','TIP','SHV','VGSH','VGIT','VGLT','VCIT','VCSH','MBB','BKLN','ANGL'],
"C06_REAL_ASSETS":['COMT','GLD','SLV','GSG','IYR','PPLT','CPER','DBB','VNQ','DBC','GDX','PALL','BNO','DBA','GDXJ','IAU','USO','UNG','DBO','USL','RWO','RWX','WOOD','CORN','URA']}
OUT=Path("etf_trader_raw"); OUT.mkdir(exist_ok=True) # push-trigger 20260918-source-transport
univ=[(t,c) for c,xs in CATS.items() for t in xs]
pd.DataFrame(univ,columns=["ticker","macro_category"]).to_csv(OUT/"universe.csv",index=False)
hashes={}; coverage=[]
for i,(t,c) in enumerate(univ,1):
    d=yf.download(t,start="2004-01-01",end="2026-07-02",auto_adjust=False,actions=False,progress=False,threads=False)
    if isinstance(d.columns,pd.MultiIndex): d.columns=d.columns.get_level_values(0)
    d=d.reset_index()
    need=["Date","Open","High","Low","Close","Adj Close","Volume"]
    if d.empty or any(x not in d for x in need): raise RuntimeError(f"missing {t}")
    f=d["Adj Close"]/d["Close"]
    q=pd.DataFrame({"date":pd.to_datetime(d["Date"]).dt.strftime("%Y-%m-%d"),
      "Open":d["Open"]*f,"High":d["High"]*f,"Low":d["Low"]*f,"Close":d["Adj Close"],"Volume":d["Volume"]})
    q=q.dropna()
    p=OUT/f"{t}.csv"; q.to_csv(p,index=False,float_format="%.17g")
    hashes[t]=hashlib.sha256(p.read_bytes()).hexdigest()
    coverage.append({"ticker":t,"rows":len(q),"first":q.date.iloc[0],"last":q.date.iloc[-1]})
    print(i,t,len(q),flush=True)
manifest={"snapshot":"ETF_TRADER_RAW_LONG_REGEN_20260918","provider":"Yahoo Finance via yfinance","requested_start":"2004-01-01","last_included":"2026-07-01","tickers":len(univ),"excluded_historical_ticker":"PIN","price_semantics":"same-row Adj Close/raw Close adjustment for OHLC; raw Volume","backfill":False,"derived_strategy_artifacts_consumed":False,"file_sha256":hashes}
(OUT/"manifest.json").write_text(json.dumps(manifest,indent=2))
pd.DataFrame(coverage).to_csv(OUT/"coverage.csv",index=False)
