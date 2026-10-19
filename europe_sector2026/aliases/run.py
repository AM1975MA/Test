#!/usr/bin/env python3
"""Independent exchange-alias Yahoo retrieval, preserving same-ISIN provenance."""
from __future__ import annotations
import argparse, json,hashlib
from pathlib import Path
import pandas as pd
from collections import Counter
from europe_sector2026.download import one,diagnose_and_normalize,sha

ROOT=Path("europe_sector2026")
def run(out):
    out=Path(out);out.mkdir(parents=True,exist_ok=False)
    for p in ("raw_vendor","adj_price"):(out/p).mkdir()
    c=pd.read_csv(Path(__file__).with_name("CATALOG.csv"))
    assert len(c)==8 and c.ticker.is_unique
    first=pd.read_csv(ROOT/"results"/"DOWNLOAD_AUDIT.csv")
    other=pd.read_csv(ROOT/"alternatives"/"results"/"ALTERNATIVES_QUALITY_AND_BASELINE_COMPARISON.csv")
    rows=[]
    for t in c.itertuples(index=False):
        r=dict(ticker=t.ticker,original_ticker=t.original_ticker,
               same_fund_ISIN=t.isin,sector=t.sector,
               alias_class=t.comparison_type)
        try:
            x,m,w=one(t.ticker)
            raw,adj,quality=diagnose_and_normalize(x)
            f=out/"raw_vendor"/(t.ticker+".csv")
            g=out/"adj_price"/(t.ticker+".csv")
            raw.to_csv(f,float_format="%.16g")
            adj.to_csv(g,float_format="%.16g")
            r.update(quality)
            r.update(status="AVAILABLE_EUR" if str(m.get("currency") or "").upper()=="EUR"
                     else "UNVERIFIED_OR_NON_EUR",
                     yahoo_currency=str(m.get("currency") or ""),
                     yahoo_name=str(m.get("shortName") or m.get("longName") or ""),
                     yahoo_venue=str(m.get("exchangeName") or m.get("exchange") or ""),
                     raw_sha256=sha(f),adj_sha256=sha(g))
            old=first[first.ticker==t.original_ticker]
            if old.empty:old=other[other.ticker==t.original_ticker]
            if len(old)==1:
                rr=old.iloc[0]
                n=max(1,int(quality["study_observed_bars"]))
                nold=int(rr["study_observed_bars"]) if pd.notna(rr["study_observed_bars"]) else 0
                r.update(original_available_bars=nold,
                     original_yahoo_zero_fraction=(float(rr["study_zero_volume"])/nold
                        if nold else None),
                     alias_yahoo_zero_fraction=float(quality["study_zero_volume"])/n,
                     change_yahoo_zero_percentage_points=(100*(
                          float(quality["study_zero_volume"])/n-float(rr["study_zero_volume"])/nold)
                          if nold else None))
            print("EU_ALIAS",t.ticker,r["status"],
                  quality["source_first"],quality["source_last"],
                  "zeros",quality["study_zero_volume"],flush=True)
        except Exception as e:
            r.update(status="DOWNLOAD_FAILED",error=type(e).__name__+": "+str(e)[:260])
            print("EU_ALIAS_FAILED",t.ticker,r["error"],flush=True)
        rows.append(r)
    pd.DataFrame(rows).to_csv(out/"ALIAS_AUDIT.csv",index=False)
    summary=dict(n=8,results=dict(Counter(r["status"] for r in rows)),
        zero_volume_warning="Not a quote bid/ask spread verification",
        same_fund_milan_listings_not_independent_instruments=True,
        vintage_survivor_2026=True,
        no_model_portfolio_changes=True)
    (out/"RESULT.json").write_text(json.dumps(summary,indent=2)+"\n")
    (out/"SHA256_MANIFEST.txt").write_text("".join(
        sha(p)+"  "+str(p.relative_to(out))+"\n" for p in sorted(out.rglob("*.csv"))))
    print("ALIAS_FINAL",json.dumps(summary),flush=True)

if __name__=="__main__":
    q=argparse.ArgumentParser();q.add_argument("--out",required=True)
    run(q.parse_args().out)
