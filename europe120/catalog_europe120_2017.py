#!/usr/bin/env python3
from __future__ import annotations

import json, time
from pathlib import Path
import pandas as pd
import download_europe120 as d

# Same discovery expansion used by the selection wrapper.
EXTRA = {
    "C01_US_BROAD_STYLE": [
        "iShares Europe ETF", "Vanguard Europe ETF", "SPDR Europe ETF", "Xtrackers Europe ETF",
        "Amundi Europe ETF", "WisdomTree Europe ETF", "First Trust Europe ETF", "Europe hedged equity ETF",
        "Europe value ETF", "Europe minimum volatility ETF", "Europe dividend ETF", "Eurozone equity ETF",
        "WisdomTree Europe Hedged Equity Fund", "First Trust Europe AlphaDEX Fund",
        "First Trust STOXX European Select Dividend Index Fund"
    ],
    "C02_US_SECTOR_THEME": [
        "iShares Europe sector ETF", "SPDR Europe sector ETF", "Xtrackers Europe sector ETF",
        "Amundi Europe sector ETF", "Lyxor Europe sector ETF", "Europe financials ETF",
        "Europe consumer ETF", "Europe industrials ETF", "Europe healthcare ETF", "Europe technology ETF",
        "EXV1.DE", "EXV2.DE", "EXV3.DE", "EXV4.DE", "EXV5.DE", "EXV6.DE", "EXV7.DE", "EXV8.DE", "EXV9.DE",
        "EXH1.DE", "EXH2.DE", "EXH3.DE", "EXH4.DE", "EXH5.DE", "EXH6.DE", "EXH7.DE", "EXH8.DE", "EXH9.DE"
    ],
    "C03_DEVELOPED_GLOBAL": [
        "iShares Germany ETF", "iShares France ETF", "iShares Italy ETF", "iShares Spain ETF",
        "iShares Netherlands ETF", "iShares Belgium ETF", "iShares Austria ETF", "iShares Ireland ETF",
        "iShares Poland ETF", "iShares Sweden ETF", "iShares Denmark ETF", "iShares Greece ETF",
        "PGAL", "EWK.MX", "HEWG", "DBGR"
    ],
    "C04_EMERGING": [
        "iShares Europe small cap ETF", "SPDR Europe small cap ETF", "Xtrackers Europe small cap ETF",
        "Europe size factor ETF", "Europe value factor ETF", "Europe momentum factor ETF",
        "Europe quality factor ETF", "Europe low volatility ETF", "Europe equal weight ETF", "Europe dividend factor ETF",
        "DFE", "EUDG", "FEUZ", "EUSC", "HFXE"
    ],
    "C05_BONDS_CASH_CREDIT": [
        "iShares Euro government bond ETF", "iShares Euro corporate bond ETF", "Xtrackers Euro bond ETF",
        "Amundi Euro bond ETF", "SPDR Euro bond ETF", "Vanguard Euro bond ETF",
        "Euro investment grade ETF", "Euro high yield ETF", "Euro inflation bond ETF", "Euro short term bond ETF"
    ],
    "C06_REAL_ASSETS": [
        "iShares Europe property ETF", "SPDR Europe real estate ETF", "Xtrackers Europe real estate ETF",
        "Europe infrastructure ETF", "Europe utilities ETF", "Europe resources ETF", "Europe materials ETF",
        "Europe oil gas ETF", "Europe construction ETF", "Eurozone real estate ETF"
    ],
}

d.CLUSTERS["C02_US_SECTOR_THEME"]["exclude"] = ["bond", "real estate", "property"]
d.CLUSTERS["C02_US_SECTOR_THEME"]["any"] = [
    "bank", "insurance", "technology", "health", "industrial", "utilit", "telecom",
    "auto", "chemical", "construction", "oil", "gas", "energy", "basic resources",
    "material", "financial", "food", "beverage", "media", "retail", "travel",
    "leisure", "consumer"
]
for cat, qs in EXTRA.items():
    d.CLUSTERS[cat]["queries"] = list(dict.fromkeys(d.CLUSTERS[cat]["queries"] + qs))

# Exact-symbol fallbacks are discovery-only and still have to pass text and raw coverage checks.
DIRECT = {
    "PGAL": ("PGAL", "Global X MSCI Portugal ETF"),
    "EWK.MX": ("EWK.MX", "iShares MSCI Belgium ETF"),
    "HEWG": ("HEWG", "iShares Currency Hedged MSCI Germany ETF"),
    "DBGR": ("DBGR", "Xtrackers MSCI Germany Hedged Equity ETF"),
    "DFE": ("DFE", "WisdomTree Europe SmallCap Dividend Fund"),
    "EUDG": ("EUDG", "WisdomTree Europe Quality Dividend Growth Fund"),
    "FEUZ": ("FEUZ", "First Trust Eurozone AlphaDEX ETF"),
    "EUSC": ("EUSC", "WisdomTree Europe Hedged SmallCap Equity Fund"),
    "HFXE": ("HFXE", "IQ 50 Percent Hedged FTSE Europe ETF"),
}
orig_search = d.search_candidates

def search(q):
    if q in DIRECT:
        sym, name = DIRECT[q]
        return [{"symbol": sym, "name": name, "exchange": "DIRECT", "query": q}]
    return orig_search(q)

d.search_candidates = search

out = Path("europe120/catalog")
out.mkdir(parents=True, exist_ok=True)
original = d.original_149()
rows = []
summary = {}
used_global = set()

for cat, spec in d.CLUSTERS.items():
    pool, seen = [], set()
    qrank = {q:i for i,q in enumerate(spec["queries"])}
    for query in spec["queries"]:
        for r in d.search_candidates(query):
            sym = r["symbol"]
            if sym in seen or sym in original:
                continue
            seen.add(sym)
            if d.text_ok(spec, r["name"]):
                pool.append(r)
        time.sleep(0.10)
    pool.sort(key=lambda r:(qrank.get(r["query"],999), r["symbol"]))
    valid = 0
    for r in pool:
        sym = r["symbol"]
        if sym in used_global:
            continue
        q, reason = d.download_one(sym)
        rec = {"ticker":sym,"macro_category":cat,"name":r["name"],"query":r["query"],"valid":q is not None,"reason":reason or "ok"}
        if q is not None:
            rec.update({"rows":len(q),"first":str(q.date.min().date()),"last":str(q.date.max().date()),"pre2017_rows":int((q.date<=d.PRE2017_CUTOFF).sum())})
            valid += 1
            used_global.add(sym)
        rows.append(rec)
    summary[cat] = {"pool":len(pool),"valid":valid}
    print("CATALOG", cat, "POOL", len(pool), "VALID", valid, flush=True)

pd.DataFrame(rows).to_csv(out/"catalog.csv",index=False)
(out/"summary.json").write_text(json.dumps(summary,indent=2)+"\n")
print(json.dumps(summary,indent=2),flush=True)
