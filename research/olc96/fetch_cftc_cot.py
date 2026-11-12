#!/usr/bin/env python3
"""OLC96 read-only raw CFTC COT downloader: never trade futures.
Annual CFTC 'futures only' archives. Preserves report date (NOT a release date).
"""
from __future__ import annotations
import io, zipfile, hashlib, json, csv, re, time, os, sys
from datetime import datetime, timezone
from pathlib import Path
import requests
import pandas as pd
from concurrent.futures import ThreadPoolExecutor, as_completed

OUT=Path("research/olc96/cftc_output")
OUT.mkdir(parents=True, exist_ok=True)
ROOT="https://www.cftc.gov/files/dea/history/"
TYPES={"DISAGG":"fut_disagg_txt_","TFF":"fut_fin_txt_"}
YEARS=range(2018,2027)
def download(typ,year):
    name=f"{TYPES[typ]}{year}.zip"
    url=ROOT+name
    err=""
    for i in range(3):
        try:
            resp=requests.get(url,timeout=120,headers={'User-Agent':'Mozilla/5.0 (research-only; CFTC public dataset)'})
            resp.raise_for_status()
            raw=resp.content
            if not raw.startswith(b"PK"):
                raise ValueError("not a ZIP archive")
            z=zipfile.ZipFile(io.BytesIO(raw))
            names=[x for x in z.namelist() if x.lower().endswith((".csv",".txt")) and not x.startswith("__MACOSX")]
            if not names:raise ValueError("ZIP contains no CSV/TXT")
            name_inner=max(names,key=lambda x:z.getinfo(x).file_size)
            content=z.read(name_inner)
            if b"\x00" in content[:200]:raise ValueError("NUL in input")
            df=None
            for encoding in ("utf-8-sig","cp1252","latin1"):
                try:
                    df=pd.read_csv(io.BytesIO(content),encoding=encoding,low_memory=False)
                    if len(df.columns)<20:raise ValueError("too few columns")
                    break
                except Exception: continue
            if df is None: raise ValueError("could not parse CSV")
            df.columns=[str(x).strip() for x in df.columns]
            cols=df.columns
            selected=[c for c in cols if
                ("date" in c.lower() and "report" in c.lower())
                or "market_and_exchange_names" in c.lower()
                or "contract_market_name" in c.lower()
                or c.lower().startswith(("cftc_","commodity_name"))
                or "open_interest_all" in c.lower()
                or re.search(r"(position|pos)[s_]*_(long|short|spread)",c,re.I)
            ]
            if not any("market_and_exchange_names" in x.lower() for x in selected):raise ValueError("missing market identifier")
            if not any("date" in x.lower() and "report" in x.lower() for x in selected):raise ValueError("missing report date")
            if not any("short" in x.lower() for x in selected):raise ValueError("missing short fields")
            out=df[selected].copy()
            out["report_family"]=typ
            out["archive_year"]=year
            meta={"family":typ,"year":year,"url":url,"archive_file":name,"inner_file":name_inner,
                "archive_sha256":hashlib.sha256(raw).hexdigest(),"inner_sha256":hashlib.sha256(content).hexdigest(),
                "rows":len(out),"columns":len(selected),"headers":selected}
            return out,meta
        except Exception as exc:
            err=f"{type(exc).__name__}: {str(exc)[:300]}"
            time.sleep(2*(i+1))
    return None,{"family":typ,"year":year,"url":url,"status":"ERROR","error":err}

def main():
    tables=[];records=[]
    with ThreadPoolExecutor(max_workers=3) as ex:
        fs={ex.submit(download,t,y):(t,y) for t in TYPES for y in YEARS}
        for fu in as_completed(fs):
            t,y=fs[fu]
            df,meta=fu.result()
            records.append(meta)
            print(f"CFTC {t} {y}: {meta.get('rows', 'ERROR')} {meta.get('error','')}",flush=True)
            if df is not None:tables.append(df)
    records.sort(key=lambda r:(r["family"],r["year"]))
    if not tables:raise RuntimeError("No CFTC annual files obtained")
    all=pd.concat(tables,ignore_index=True)
    all.to_csv(OUT/"cftc_raw_reduced.csv.gz",index=False,compression="gzip")
    namecol=next(x for x in all if "market_and_exchange_names" in x.lower())
    datecol=next(x for x in all if "date" in x.lower() and "report" in x.lower())
    market=all.groupby(["report_family",namecol],dropna=False).agg(
       n_rows=("archive_year","size"), first_archive=("archive_year","min"),last_archive=("archive_year","max")
    ).reset_index().rename(columns={namecol:"market_name"})
    market.sort_values(["report_family","market_name"]).to_csv(OUT/"cftc_contract_universe.csv",index=False)
    cats={t:len([x for x in records if x["family"]==t and x.get("rows",0)>0]) for t in TYPES}
    manifest={"fetched_at_utc":datetime.now(timezone.utc).isoformat(),
        "source":"CFTC historical compressed Futures Only reports",
        "n_rows":len(all),"archive_years":sorted(set(all.archive_year)),
        "families_complete_by_year":cats,"n_markets":len(market),
        "report_date_field":datecol,"name_field":namecol,
        "publication_warning":"Tuesday report date != Friday publication date; releases may be delayed especially 2025 shutdown. Never mark point-in-time valid from report date alone.",
        "results":records}
    (OUT/"manifest.json").write_text(json.dumps(manifest,indent=2,default=str),encoding="utf8")
    with (OUT/"archive_manifest.csv").open("w",newline="",encoding="utf8") as f:
        keys=["family","year","url","archive_sha256","inner_sha256","rows","columns","status","error"]
        writer=csv.DictWriter(f,fieldnames=keys,extrasaction="ignore");writer.writeheader();writer.writerows(records)
    if any(v<8 for v in cats.values()):
        print("PARTIAL CFTC coverage", cats,flush=True)
        return 2
    print(f"CFTC RAW FETCH PASS {len(all)} rows, {len(market)} markets, {cats}",flush=True)
    return 0
if __name__=="__main__":sys.exit(main())
