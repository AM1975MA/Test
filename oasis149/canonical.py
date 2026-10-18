#!/usr/bin/env python3
"""Only original 149 tickers, no rank/performance-based ETF membership choice."""
from __future__ import annotations
import argparse,hashlib,json
from pathlib import Path
from collections import Counter
import numpy as np
import pandas as pd
from oasis.observers import prepare,market_states
from oasis.daily_backtest import simulate as vanilla_simulate
ROOT=Path(__file__).resolve().parents[1]
SRC=ROOT/"evidence_v1/data/original149"
START=pd.Timestamp("2017-02-01")
END=pd.Timestamp("2026-07-01")
def sha(path):
    h=hashlib.sha256()
    with Path(path).open("rb") as file:
        for z in iter(lambda:file.read(1<<20),b""):h.update(z)
    return h.hexdigest()
def load_149():
    roster=pd.read_csv(SRC/"universe.csv")
    manifest=json.loads((SRC/"manifest.json").read_text())
    assert len(roster)==149 and roster.ticker.nunique()==149
    assert manifest["tickers"]==149 and manifest["status"]=="UNIFORM_YAHOO_FRESH_RAW"
    assert len(manifest["file_sha256"])==149
    assert set(roster.ticker)==set(manifest["file_sha256"])
    O={};C={};V={};rows=[]
    for record in roster.itertuples(index=False):
        ticker=record.ticker
        path=SRC/(ticker+".csv")
        if sha(path)!=manifest["file_sha256"][ticker]:
            raise AssertionError("Source SHA mismatch "+ticker)
        data=pd.read_csv(path,parse_dates=["date"])
        if data.date.duplicated().any() or data.date.isna().any():
            raise AssertionError("Duplicate/invalid dates "+ticker)
        data=data.set_index("date").sort_index()
        for k in ("Open","High","Low","Close","Volume"):
            if k not in data:raise AssertionError("Missing "+k)
        # Do not reject genuine crashes or large daily swings by a return filter.
        px=data[["Open","High","Low","Close"]].astype(float)
        vv=data.Volume.astype(float)
        eligible=(np.isfinite(px.to_numpy()).all(axis=1)&
            (px.to_numpy()>0).all(axis=1)&
            np.isfinite(vv.to_numpy())&(vv.to_numpy()>=0))
        mask=(data.index>=START)&(data.index<=END)
        rows.append(dict(ticker=ticker,macro_category=record.macro_category,
            source_sha256=manifest["file_sha256"][ticker],
            valid_study_sessions=int(np.sum(eligible&mask)),
            zero_vol_study=int(np.sum(mask & (vv.to_numpy()==0))),
            invalid_ohlc_study=int(np.sum(mask & ~eligible)),
            pre2017_observations=int(np.sum((data.index<START)&eligible))))
        O[ticker]=data.Open
        C[ticker]=data.Close
        V[ticker]=data.Volume
    O=pd.concat(O,axis=1).reindex(columns=roster.ticker.tolist()).astype(float)
    C=pd.concat(C,axis=1).reindex(columns=roster.ticker.tolist()).astype(float)
    V=pd.concat(V,axis=1).reindex(columns=roster.ticker.tolist()).astype(float)
    # Universe membership fixed by original149 list; no fallback or replacement.
    valid=(O.notna().sum(axis=1)==149)&(C.notna().sum(axis=1)==149)
    days=O.index[valid & (O.index>=START)&(O.index<=END)]
    previous=O.index[valid & (O.index<START)]
    if not len(previous):raise AssertionError("No legitimate previous close")
    if len(days)!=2366:
        raise AssertionError("Unexpected 149 session calendar "+str(len(days)))
    # At the entry opening, only the previous completed common market close
    # may be used to generate the signal (strict clock check).
    all_dates=O.index[valid]
    ix=pd.Index(all_dates).get_indexer(days)
    signals=[all_dates[j-1] for j in ix]
    if any(not (s<d) for s,d in zip(signals,days)):
        raise AssertionError("Current-day close used to decide opening order")
    assert len(set(roster.macro_category))==6
    return roster,O,C,V,pd.DatetimeIndex(days),pd.DatetimeIndex(signals),pd.DataFrame(rows)
def assemble(out:Path):
    out.mkdir(parents=True,exist_ok=False)
    roster,O,C,V,days,signals,quality=load_149()
    observed=prepare(C)
    states=market_states(observed)
    p0=vanilla_simulate("P0_MONTHLY_GREEDY",observed,states,O,list(days),list(signals))
    p3=vanilla_simulate("P3_OASIS_CRISIS_ACTIVE",observed,states,O,list(days),list(signals))
    p0.to_csv(out/"P0_149_REFERENCE.csv",index=False)
    p3.to_csv(out/"P3_149_SHADOW.csv",index=False)
    quality.to_csv(out/"ALL_149_DATA_QUALITY.csv",index=False)
    pd.DataFrame({"day":days,"signal_date":signals}).to_csv(out/"CALENDAR.csv",index=False)
    ref={p:{"cagr":float((f.wealth.iloc[-1]/f.wealth.iloc[0])**
                     (365.25/(f.day.iloc[-1]-f.day.iloc[0]).days)-1),
         "maxdd":float(np.min(f.wealth/np.maximum.accumulate(f.wealth)-1)),
         "name_switches":int(f.name_switch.sum())}
         for p,f in (("P0",p0),("P3",p3))}
    manifest=dict(status="OASIS_CANONICAL_ORIGINAL149_VERIFIED",
       source="evidence_v1/data/original149/universe.csv",
       member_count=149,
       unique_names=149,
       period=[str(days[0].date()),str(days[-1].date())],
       n_shared_days=len(days),
       six_categories=roster.macro_category.value_counts().to_dict(),
       asof_next_open=True,
       full_original_roster_used_without_ranking=True,
       roster_sha256=sha(SRC/"universe.csv"),
       manifest_sha256=sha(SRC/"manifest.json"),
       historical_universe_survivorship_bias=True,
       quality_zero_volume_total=int(quality.zero_vol_study.sum()),
       quality_invalid_ohlc_total=int(quality.invalid_ohlc_study.sum()),
       P0_P3_source_only_reference=ref)
    (out/"MANIFEST_149.json").write_text(json.dumps(manifest,indent=2)+"\n")
    print("OASIS149_CANONICAL_RESULT "+json.dumps(manifest),flush=True)
if __name__=="__main__":
    a=argparse.ArgumentParser();a.add_argument("--out",required=True)
    args=a.parse_args()
    assemble(Path(args.out))
