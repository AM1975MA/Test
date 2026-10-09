"""Data-only census for frozen Original149 triples; never fit or modify models."""
import argparse, json, hashlib
from pathlib import Path
import numpy as np
import pandas as pd

FIELDS=("Open","High","Low","Close","Volume")
def digest(p):
    h=hashlib.sha256()
    with open(p,"rb") as f:
        for b in iter(lambda:f.read(1024*1024),b""):h.update(b)
    return h.hexdigest()

def load(root):
    meta=pd.read_csv(root/"universe.csv")
    if not {"ticker","macro_category"}.issubset(meta):raise ValueError("Bad universe schema")
    tickers=meta.ticker.astype(str).tolist()
    if len(tickers)!=149 or len(set(tickers))!=149:raise ValueError("Expected distinct Original149")
    data={};stats=[];hashes={}
    for t in tickers:
        f=root/f"{t}.csv"
        x=pd.read_csv(f,parse_dates=["date"],float_precision="round_trip")
        if not set(["date",*FIELDS]).issubset(x):raise ValueError(f"Missing columns {t}")
        if x.date.isna().any() or x.date.duplicated().any() or not x.date.is_monotonic_increasing:
            raise ValueError(f"Invalid dates {t}")
        v=x[list(FIELDS)].apply(pd.to_numeric,errors="coerce")
        invalid=~np.isfinite(v.to_numpy(float))
        if invalid.any() or (v[["Open","High","Low","Close"]] <=0).any().any() or (v.Volume<0).any():
            raise ValueError(f"Nonfinite or impossible raw OHLCV {t}")
        incoherent=((v.Low>v[["Open","Close"]].min(axis=1)+1e-8) |
                    (v.High<v[["Open","Close"]].max(axis=1)-1e-8) |
                    (v.High<v.Low))
        if incoherent.any():raise ValueError(f"Incoherent OHLC {t}")
        x=x.set_index("date")[list(FIELDS)]
        x=x.astype(float)
        data[t]=x;hashes[t]=digest(f)
        r=x.Close.pct_change(fill_method=None)
        stats.append(dict(ticker=t,rows=len(x),first=str(x.index.min().date()),
          last=str(x.index.max().date()),zero_volume=int(x.Volume.eq(0).sum()),
          zero_daily_close_return=int(r.eq(0).sum()),
          abs_return_gt20pct=int(r.abs().gt(.2).sum()),
          abs_return_gt50pct=int(r.abs().gt(.5).sum()),
          weekdays_nontrading=int((x.index.dayofweek>=5).sum()),
          stale_close_5bars=int((x.Close.diff().eq(0).rolling(5,min_periods=5).sum()==5).sum()),
          max_abs_return=float(r.abs().max()) if r.notna().any() else None))
    return data,stats,hashes

def pair(a,b):
    rows=[];changes=[]
    for t in sorted(a):
        x=a[t];y=b[t]
        idx=x.index.intersection(y.index)
        if len(idx)!=len(x) or len(idx)!=len(y):
            raise ValueError(f"Different calendar on {t}: {len(x)} vs {len(y)} and {len(idx)} common")
        dx=x.loc[idx];dy=y.loc[idx]
        diff=(dx!=dy)
        for fld in FIELDS:
            d=dx[fld]-dy[fld]
            ar=d.abs()/(dx[fld].abs().clip(lower=1e-12))
            if diff[fld].any():
                changes.append(dict(ticker=t,field=fld,cells=int(diff[fld].sum()),
                    max_abs=float(d.abs().max()),max_relative=float(ar.max()),
                    first=str(idx[diff[fld]].min().date()),last=str(idx[diff[fld]].max().date())))
        ra=dx.Close.pct_change(fill_method=None);rb=dy.Close.pct_change(fill_method=None)
        dd=(ra-rb).abs()
        rows.append(dict(ticker=t,rows=len(idx),changed_price_bars=int(diff[list(FIELDS[:4])].any(axis=1).sum()),
          changed_volume_bars=int(diff.Volume.sum()),
          changed_daily_close_returns=int((dd>0).sum()),
          max_abs_daily_close_return_diff=float(dd.max()),
          max_relative_ohlc=float(((dx[list(FIELDS[:4])]-dy[list(FIELDS[:4])]).abs() /
             dx[list(FIELDS[:4])].abs().clip(lower=1e-12)).max().max())))
    return rows,changes

def audit(args):
    roots=[Path(x) for x in (args.r1,args.r2,args.r3)]
    loaded=[load(r) for r in roots]
    out=Path(args.out);out.mkdir(parents=True,exist_ok=False)
    allstats=[];allhashes={}
    for i,(_,stat,sha) in enumerate(loaded,1):
        allstats.extend([dict(repeat=i,**s) for s in stat]);allhashes[str(i)]=sha
    pd.DataFrame(allstats).to_csv(out/"RAW_PER_TICKER.csv",index=False)
    pairsummary={}
    for i,j in ((1,2),(1,3),(2,3)):
        rows,changes=pair(loaded[i-1][0],loaded[j-1][0])
        pd.DataFrame(rows).assign(pair=f"{i}-{j}").to_csv(out/f"RAW_PAIR_{i}_{j}_TICKER.csv",index=False)
        pd.DataFrame(changes).assign(pair=f"{i}-{j}").to_csv(out/f"RAW_PAIR_{i}_{j}_FIELD_CHANGES.csv",index=False)
        pairsummary[f"{i}-{j}"]=dict(changed_tickers=sum(r["changed_price_bars"]>0 for r in rows),
          changed_volume_tickers=sum(r["changed_volume_bars"]>0 for r in rows),
          max_return_diff=max(r["max_abs_daily_close_return_diff"] for r in rows),
          changed_ohlc_fields=len(changes))
    report=dict(status="ORIGINAL149_RAW_TRIPLE_CENSUS_COMPLETE",snapshots=3,
      universe=149,source_run=37121749852,source_hashes=allhashes,
      pairwise=pairsummary,external_corporate_actions_truth_certified=False,
      production_adoption=False,models_trained=False,cagr_computed=False,
      require_feature_census=True,complete_data_gate_pass=False)
    (out/"RESULT.json").write_text(json.dumps(report,indent=2,allow_nan=False)+"\n")
    by=pd.DataFrame(allstats)
    (out/"REPORT.md").write_text("# Original149 frozen raw market-input census\n\n"
       "No model training or trading replay. Structural quality does not certify upstream Yahoo adjusted-price correctness.\n\n"
       f"Total ticker-file observations: {len(by)}; zero-volume bars: {int(by.zero_volume.sum())}; "
       f"weekend dates: {int(by.weekdays_nontrading.sum())}; "
       f"single-session abs close return >20%: {int(by.abs_return_gt20pct.sum())}; "
       f">50%: {int(by.abs_return_gt50pct.sum())}.\n\n"
       "| Pair | Altered OHLC tickers | Altered Volume tickers | Maximum daily return difference |\n"
       "|---|---:|---:|---:|\n"+
       "".join(f"| {k} | {v['changed_tickers']} | {v['changed_volume_tickers']} | {v['max_return_diff']:.9g} |\n" for k,v in pairsummary.items())+
       "\nRaw changes are flagged, never silently overwritten. "
       "Original bar-level and corporate-action provider truth remain unverified. Full feature-input census is a separate required step.\n")
    print((out/"REPORT.md").read_text())

if __name__=="__main__":
    p=argparse.ArgumentParser()
    for a in ("r1","r2","r3","out"):p.add_argument("--"+a,required=True)
    audit(p.parse_args())
