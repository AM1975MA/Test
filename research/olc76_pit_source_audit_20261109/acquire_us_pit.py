#!/usr/bin/env python3
"""Research-only PIT holdings acquisition for US SEC N-PORT funds. Attribution: theMulden.com, CC BY 4.0."""
import argparse, gzip, io, json, hashlib, time
from pathlib import Path
import numpy as np
import pandas as pd
import requests

def one(ticker, out, session):
    url=f"https://themulden.com/pit/{ticker}.csv.gz"
    try:
        r=session.get(url,headers={"User-Agent":"OLC76Research/1.0 public ETF coverage test"},timeout=20)
        if r.status_code!=200:return None,{"ticker":ticker,"url":url,"status":r.status_code}
        if len(r.content)>5_000_000 or r.content[:2]!=b"\x1f\x8b":return None,{"ticker":ticker,"error":"not_gzip_or_large"}
        df=pd.read_csv(io.BytesIO(gzip.decompress(r.content)),dtype={"isin":"string","cusip":"string","isCashCollateral":"string"})
        req={"asOf","filedDate","pctOfNetAssets","isin","cusip","assetCat","isCashCollateral"}
        if not req.issubset(df.columns):return None,{"ticker":ticker,"error":"schema","columns":df.columns.tolist()}
        (out/f"{ticker}.csv.gz").write_bytes(r.content)
        return df,{"ticker":ticker,"status":200,"rows":len(df),"bytes":len(r.content),"sha256":hashlib.sha256(r.content).hexdigest(),"url":url}
    except Exception as e:
        return None,{"ticker":ticker,"error":str(e)[:250]}

def snap(df,signal):
    if df is None:return None,"download_failed"
    x=df.copy();x["asOf"]=pd.to_datetime(x["asOf"],errors="coerce");x["filedDate"]=pd.to_datetime(x["filedDate"],errors="coerce")
    at=pd.Timestamp(signal);x=x[(x.filedDate<=at)&(x.asOf<=x.filedDate)&(x.asOf<=at)]
    if x.empty:return None,"no_pre_signal_filing"
    d=x.asOf.max();x=x[x.asOf==d];p=x.filedDate.max();x=x[x.filedDate==p].copy()
    age=(at-d).days
    if age>120:return None,f"stale_{age}_days"
    x["v"]=pd.to_numeric(x.pctOfNetAssets,errors="coerce")
    x=x[(x.v>0)&(x.isCashCollateral.fillna("N").str.upper()!="Y")].copy()
    gross=x.v.sum()
    if not 80<=gross<=150:return None,f"bad_coverage_{gross:.1f}"
    x=x[x.assetCat.fillna("").str.upper()=="EC"].copy()
    if x.v.sum()/gross<0.90:return None,"not_primarily_equity"
    sid=x["isin"].fillna("").astype(str).str.strip()
    missing=sid.isin(["","-","nan"])
    sid.loc[missing]="CUSIP:"+x.loc[missing,"cusip"].fillna("").astype(str).str.strip()
    if sid.eq("CUSIP:").any():return None,"missing_id"
    x["sid"]=sid
    w=x.groupby("sid").v.sum();w=w/w.sum()
    return {"asOf":str(d.date()),"filedDate":str(p.date()),"age_days":age,"n":len(w),"effective_n":float(1/sum(w.values**2)),"weights":w.to_dict()},None

def main():
    p=argparse.ArgumentParser();p.add_argument("--events",required=True);p.add_argument("--out",required=True)
    a=p.parse_args();out=Path(a.out);out.mkdir(parents=True,exist_ok=True)
    events=json.loads(Path(a.events).read_text())
    good=[e for e in events if e["market"]=="USA" and e.get("both_sec_fund_candidates",True)]
    commodity={"DBO","UNG","GLD","IAU","PALL","PPLT"}
    tickers=sorted(set(t for e in good for t in [e["ticker1"],e["ticker2"]]))
    assert len(good)==18 and not set(tickers)&commodity
    data={};logs=[]
    with requests.Session() as ses:
        for t in tickers:
            d,l=one(t,out,ses);logs.append(l)
            if d is not None:data[t]=d
            time.sleep(.5)
    rows=[]
    for e in good:
        a1,err1=snap(data.get(e["ticker1"]),e["signal_date"])
        a2,err2=snap(data.get(e["ticker2"]),e["signal_date"])
        item={k:e[k] for k in ["signal_date","ticker1","ticker2","future_log_return_spread"]}
        item.update(status="covered" if a1 and a2 else "missing",reason1=err1,reason2=err2)
        if a1 and a2:
            overlap=sum(min(v,a2["weights"].get(k,0.0)) for k,v in a1["weights"].items())
            item.update(overlap=float(overlap),t1_asOf=a1["asOf"],t2_asOf=a2["asOf"],t1_filed=a1["filedDate"],t2_filed=a2["filedDate"],t1_age=a1["age_days"],t2_age=a2["age_days"])
        rows.append(item)
    n=sum(r["status"]=="covered" for r in rows)
    summary={"candidate_events":18,"funds_requested":len(tickers),"funds_downloaded":len(data),"events_with_two_PIT_books":n,"us_event_coverage":n/30,"all_event_coverage":n/60,"research_gate_pass":False,"model_run":False,"source":"theMulden.com CC BY 4.0; SEC N-PORT derived; verify series identifiers independently"}
    (out/"fetch_log.json").write_text(json.dumps(logs,indent=2))
    (out/"pairs.json").write_text(json.dumps(rows,indent=2))
    (out/"summary.json").write_text(json.dumps(summary,indent=2))
    print(json.dumps(summary,indent=2))
if __name__=="__main__":main()
