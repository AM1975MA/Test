#!/usr/bin/env python3
"""Read-only health probes for free European ETF history sources in Oct 2026.

No CAPTCHA solving, no paid logins, no persistent vendor price redistribution.
Records only HTTP metadata, response shapes, record counts and date span.
"""
from __future__ import annotations
import json,io,ssl,urllib.request,urllib.parse,urllib.error,xml.etree.ElementTree as ET
from pathlib import Path
from datetime import datetime,timezone
import csv

CASES=[
 ("stooq","EXV4.DE","https://stooq.com/q/d/l/?"+urllib.parse.urlencode(
       {"s":"exv4.de","f":"20170101","t":"20260701","i":"d"})),
 ("stooq","DXSE.DE","https://stooq.com/q/d/l/?"+urllib.parse.urlencode(
       {"s":"dxse.de","f":"20170101","t":"20260701","i":"d"})),
 ("stooq","EXH4.DE","https://stooq.com/q/d/l/?"+urllib.parse.urlencode(
       {"s":"exh4.de","f":"20170101","t":"20260701","i":"d"})),
 ("stooq","5ESG.DE","https://stooq.com/q/d/l/?"+urllib.parse.urlencode(
       {"s":"5esg.de","f":"20240101","t":"20260701","i":"d"})),
]
for date in ("2017-08-01","2020-07-01","2023-07-03","2026-10-16"):
    CASES.append(("xetra-pds",date,
       "https://deutsche-boerse-xetra-pds.s3.eu-central-1.amazonaws.com/?"+
       urllib.parse.urlencode({"list-type":"2","prefix":date+"/","max-keys":"2"})))
CASES.append(("euronext","IE00B4WXJJ64-XAMS",
       "https://live.euronext.com/en/popout-page/getHistoricalPrice/IE00B4WXJJ64-XAMS"))
CASES.append(("ishares","IMEU",
       "https://www.ishares.com/it/investitori-professionali/it/prodotti/251860/ishares-msci-europe-ucits-etf-inc-fund"))
CASES.append(("vienna","etfs",
       "https://www.wienerborse.at/en/market-data/exchange-traded-funds/"))

def request(url):
    req=urllib.request.Request(url,headers={
       "User-Agent":"Mozilla/5.0 (compatible; AcademicETFResearch/1.0)",
       "Accept":"text/csv,text/plain,application/xml,text/html,*/*"})
    try:
        with urllib.request.urlopen(req,timeout=15) as resp:
            b=resp.read(1024*512)
            return {"http":int(resp.status),
                    "final_url_host":urllib.parse.urlsplit(resp.url).hostname,
                    "content_type":str(resp.headers.get("Content-Type",""))[:70],
                    "sample_length_bytes":len(b)},b
    except urllib.error.HTTPError as e:
        b=e.read(2000)
        return {"http":e.code,
                 "content_type":str(e.headers.get("Content-Type",""))[:70]},b
    except Exception as e:
        return {"http":None,"error":type(e).__name__+": "+str(e)[:180]},b""

def analyze_stooq(b):
    t=b.decode("utf-8","replace")
    first=t[:1000].lower()
    if "date,open,high,low,close" in first:
        rows=list(csv.DictReader(io.StringIO(t)))
        if not rows:return {"shape":"CSV_HEADER_NO_ROWS"}
        dates=[z.get("Date") or z.get("date") for z in rows]
        return {"shape":"DAILY_OHLCV_CSV",
                "rows_in_probe":len(rows),"first_date":min(dates),
                "last_date":max(dates),
                "volume_field":("Volume" in rows[0])}
    if "captcha" in first or "apikey" in first or "access denied" in first or "please enable" in first or "<html" in first:
        return {"shape":"ACCESS_GATE_OR_HTML","mentions_captcha":("captcha" in t.lower()),
                "mentions_api_key":("apikey" in t.lower()),
                "mentions_access_denied":("access denied" in t.lower())}
    return {"shape":"UNRECOGNIZED_SMALL_RESPONSE","first_120_characters":t[:120].replace("\n"," ")}

def analyze_s3(b):
    try:
        root=ET.fromstring(b)
        ns={"s":"http://s3.amazonaws.com/doc/2006-03-01/"}
        files=root.findall("s:Contents",ns)
        keys=[q.findtext("s:Key",default="",namespaces=ns) for q in files]
        return {"shape":"S3_XML_LIST","returned_keys":keys,
                "key_count_response":int(root.findtext("s:KeyCount","0",ns)),
                "is_truncated":root.findtext("s:IsTruncated","",ns)}
    except Exception:
        return {"shape":"S3_RESPONSE_NOT_XML"}

def main():
    p=Path("_FREE_MARKETDATA_PROBE")
    p.mkdir(exist_ok=False)
    results=[]
    for provider,name,url in CASES:
        meta,data=request(url)
        datum=dict(provider=provider,scope=name,**meta)
        if provider=="stooq":datum.update(analyze_stooq(data))
        if provider=="xetra-pds":datum.update(analyze_s3(data))
        if provider in ("euronext","ishares","vienna"):
            t=data[:4096].decode("utf-8","replace").lower()
            datum["page_html_detected"]="<html" in t or "<!doctype html" in t
            datum["is_direct_OHLCV_CSV"]=t.startswith("date,open,high,low,close")
        print("FREE_ETF_SOURCE_PROBE",json.dumps(datum),flush=True)
        results.append(datum)
    summary={"retrieved_utc":datetime.now(timezone.utc).isoformat(),
       "no_authentication_or_paid_account":True,
       "no_vendor_historical_OHLCV_data_redistributed":True,
       "not_a_license_to_use_provider_data_commercially":True,
       "sample_only_cannot_extrapolate_full_EU_coverage":True,
       "probes":results}
    (p/"RESULT.json").write_text(json.dumps(summary,indent=2,ensure_ascii=False)+"\n")
    assert len(results)==len(CASES)

if __name__=="__main__":main()
