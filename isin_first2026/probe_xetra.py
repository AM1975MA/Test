#!/usr/bin/env python3
"""Read only, public official Xetra ISIN/mnemonic reference; metadata-only probe."""
import urllib.request,hashlib,csv,io,json
from pathlib import Path
url="https://www.cashmarket.deutsche-boerse.com/resource/blob/1528/a31c10e3183f4c5dd721f9c7f9eaaaea/data/t7-xetr-allTradableInstruments.csv"
root=Path("_XETRA_PROBE");root.mkdir(exist_ok=False)
out={"source":url}
try:
    with urllib.request.urlopen(urllib.request.Request(url,headers={"User-Agent":"Mozilla/5.0","Accept":"text/csv,*/*"}),timeout=30) as response:
        body=response.read(15_000_000)
        out.update({"http":response.status,"bytes":len(body),"sha256":hashlib.sha256(body).hexdigest(),"content_type":response.headers.get("Content-Type")})
    raw=body.decode("utf-8-sig",errors="replace")
    rows=raw.splitlines()
    out.update({"head_lines":[x[:1500] for x in rows[:5]],"total_lines":len(rows)})
    header_i=next((i for i,x in enumerate(rows[:12]) if "ISIN" in x and ("Mnemonic" in x or "mnemonic" in x.lower())),None)
    if header_i is not None:
        records=list(csv.DictReader(io.StringIO("\n".join(rows[header_i:])),delimiter=";"))
        out["headers"]=list(records[0]) if records else []
        out["record_count"]=len(records)
        for sym in ("EXV1","EXH4","DXSE","SPYK","IMEU","EXS1"):
            a=[r for r in records if any(k.strip().lower() in ("mnemonic","ticker","symbol","product id","wkn") and str(v).strip().upper()==sym for k,v in r.items())]
            out["sample_"+sym]=a[:2]
except Exception as exc:
    out["error"]=type(exc).__name__+": "+str(exc)[:500]
(root/"RESULT.json").write_text(json.dumps(out,indent=2,ensure_ascii=False)+"\n")
print("XETRA_REFERENCE_PROBE",json.dumps(out,ensure_ascii=False),flush=True)
