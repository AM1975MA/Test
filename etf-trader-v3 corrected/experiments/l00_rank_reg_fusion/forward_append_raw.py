#!/usr/bin/env python3
"""Append-only V3 locked raw snapshot extension from an independent source download.

The entire original 149-ticker adjusted OHLCV history stays numerically identical.
A Yahoo-adjusted close series fetched over an anchor overlap is scaled to match
the frozen original 2026-07-01 adjusted-close anchor; post-snapshot rows only
are appended. Differences are investigated and REJECTED; no history backfill.
"""
from __future__ import annotations
import argparse,hashlib,json,time
from datetime import datetime,timezone
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor,as_completed
import numpy as np,pandas as pd,yfinance as yf

ANCHOR=pd.Timestamp("2026-07-01")
LAST_EXPECTED=pd.Timestamp("2026-10-23")
def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()
def fetch(t,old):
    problem=None
    for attempt in range(3):
        try:
            x=yf.download(t,start="2026-06-19",end="2026-10-25",
                          auto_adjust=False,actions=False,progress=False,threads=False)
            if isinstance(x.columns,pd.MultiIndex):
                x.columns=x.columns.get_level_values(0)
            if x.empty or "Adj Close" not in x or ANCHOR not in x.index:
                raise RuntimeError("Yahoo returned empty / no adjusted close / no original anchor")
            x=x.sort_index()
            last=x.index[-1]
            if last<LAST_EXPECTED:raise RuntimeError(f"stale last close {last.date()}")
            adjusted=x["Adj Close"]/x["Close"]
            prices=pd.DataFrame({"date":x.index,
                 "Open":x["Open"]*adjusted,"High":x["High"]*adjusted,
                 "Low":x["Low"]*adjusted,"Close":x["Adj Close"],
                 "Volume":x["Volume"]}).dropna()
            oldanchor=old.loc[old.date.eq(ANCHOR)]
            assert len(oldanchor)==1
            yanchor=prices.loc[prices.date.eq(ANCHOR)]
            assert len(yanchor)==1
            scale=float(oldanchor.Close.iloc[0]/yanchor.Close.iloc[0])
            prices[["Open","High","Low","Close"]]*=scale
            overlap=old.merge(prices,on="date",suffixes=("_frozen","_new"))
            overlap=overlap.loc[overlap.date.between(pd.Timestamp("2026-06-19"),ANCHOR)]
            assert len(overlap)>=7,(t,len(overlap))
            # Provider price history should differ only by rescaling for
            # later corporate actions. This validates the anchor across dates.
            oldclose=overlap.Close_frozen.to_numpy(float)
            newclose=overlap.Close_new.to_numpy(float)
            drift=np.max(np.abs(newclose/oldclose-1))
            if drift>0.004:
                raise RuntimeError(f"Historical adjustment changed nonuniformly at anchor: {drift:.4%}")
            part=prices[prices.date>ANCHOR].copy()
            part=part.sort_values("date")
            assert len(part)>=70,(t,len(part))
            assert not (part.date<=ANCHOR).any()
            numeric=part[["Open","High","Low","Close","Volume"]].to_numpy(float)
            assert np.isfinite(numeric).all() and (numeric[:,:4]>0).all()
            assert (numeric[:,4]>=0).all()
            lo=np.minimum(part.Open,part.Close)
            hi=np.maximum(part.Open,part.Close)
            assert (part.Low<=lo+1e-7*np.maximum(1,lo)).all()
            assert (part.High>=hi-1e-7*np.maximum(1,hi)).all()
            return part,dict(ticker=t,rows_appended=len(part),
                last_new_day=str(last.date()),scale_to_original=scale,
                overlap_days=len(overlap),max_adjustment_drift_fraction=float(drift),
                frozen_rows=len(old),frozen_last=str(old.date.iloc[-1].date()))
        except Exception as ex:
            problem=repr(ex)
            time.sleep((attempt+1)*1.2)
    raise RuntimeError(f"Provider failed for {t}: {problem}")

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--old",required=True)
    ap.add_argument("--out",required=True)
    args=ap.parse_args()
    old=Path(args.old);dest=Path(args.out);dest.mkdir(parents=True,exist_ok=True)
    m=json.loads((old/"manifest.json").read_text())
    assert m["tickers"]==149
    names=pd.read_csv(old/"universe.csv").ticker.astype(str).tolist()
    assert len(names)==len(set(names))==149
    oldframes={}
    originalhash={}
    for t in names:
        path=old/(t+".csv")
        originalhash[t]=sha(path)
        oldframes[t]=pd.read_csv(path,parse_dates=["date"],float_precision="round_trip")
        assert oldframes[t].date.iloc[-1]==ANCHOR,t
    results={}
    # Concurrent access cap prevents Yahoo throttling during full-universe
    # continuation. One Yahoo failure makes the test invalid rather than
    # silently dropping the ETF or shrinking the frozen universe.
    with ThreadPoolExecutor(max_workers=4) as pool:
        jobs={pool.submit(fetch,t,oldframes[t]):t for t in names}
        for task in as_completed(jobs):
            t=jobs[task]
            try:
                new,record=task.result()
                whole=pd.concat([oldframes[t],new],ignore_index=True)
                assert len(whole)==len(oldframes[t])+len(new)
                assert whole.date.is_unique and whole.date.is_monotonic_increasing
                columns=["date","Open","High","Low","Close","Volume"]
                # Freeze historical values bit for bit in memory.
                np.testing.assert_array_equal(whole.iloc[:len(oldframes[t])][columns[1:]].to_numpy(float),
                    oldframes[t][columns[1:]].to_numpy(float))
                whole["date"]=whole.date.dt.strftime("%Y-%m-%d")
                whole.to_csv(dest/(t+".csv"),index=False,float_format="%.17g")
                verify=pd.read_csv(dest/(t+".csv"),float_precision="round_trip")
                np.testing.assert_array_equal(verify.iloc[:len(oldframes[t])][columns[1:]].to_numpy(float),
                    oldframes[t][columns[1:]].to_numpy(float),
                    err_msg="Original OHLCV historic value changed after write")
                record["original_sha256"]=originalhash[t]
                record["new_sha256"]=sha(dest/(t+".csv"))
                results[t]=record
                print("APPENDED",t,record["rows_appended"],record["last_new_day"],flush=True)
            except Exception as exc:
                print("REJECT_TICKER",t,repr(exc),flush=True)
                raise
    assert len(results)==149
    # All old input filenames and provenance manifest remain untouched in
    # original folder. Copies in extension folder are new research files.
    (dest/"universe.csv").write_bytes((old/"universe.csv").read_bytes())
    (dest/"original_manifest.json").write_bytes((old/"manifest.json").read_bytes())
    with (dest/"PROVENANCE.json").open("w") as f:
        json.dump(dict(extension_date_utc=datetime.now(timezone.utc).isoformat(),
            original_snapshot_id=m.get("snapshot"),original_raw_run=39482809691,
            anchor="2026-07-01",last_requested="2026-10-23",
            supplier="Yahoo Finance / yfinance 0.2.66",original_tickers=149,
            original_historic_prefix_unchanged=True,post_anchor_only=True,
            validation_limit_max_historical_drift=0.004,
            basket_file_sha256="36a45916b5d8191f3ccd206f39bf3fd3f1ed4bcaffd474e352b69c598f2b6a5e",
            rows=results),f,indent=2)
    print("FROZEN_RAW_EXTENSION_PASS",len(results),"last",sorted(
        set(r["last_new_day"] for r in results.values())),flush=True)
if __name__=="__main__":main()
