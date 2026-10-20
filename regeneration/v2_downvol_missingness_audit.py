#!/usr/bin/env python3
"""Audit regime-dependent causal downside-volatility missingness on frozen V2 OHLCV.

Run on the exact source-only 149-ETF dataset downloaded from GitHub Actions
39482809691; no labels, strategy decisions or future returns are used.
"""
import argparse
from pathlib import Path
import numpy as np
import pandas as pd

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--raw",default="etf_trader_raw")
    ap.add_argument("--out",default="runs/v2_downvol_missingness")
    ap.add_argument("--first-year",type=int,default=2012)
    ap.add_argument("--last-year",type=int,default=2025)
    args=ap.parse_args()
    root=Path(args.raw)
    mats=[]
    for path in sorted(root.glob("*.csv")):
        if path.stem.lower() in ("universe","membership"):continue
        try:
            m=pd.read_csv(path,usecols=["date","Close"],parse_dates=["date"]).set_index("date")
        except (ValueError,KeyError):continue
        mats.append(m.rename(columns={"Close":path.stem}))
    if len(mats)!=149:raise RuntimeError(f"Expected exact 149 ETF CSV inputs, got {len(mats)}")
    close=pd.concat(mats,axis=1).sort_index()
    close=close.where(close>0)
    lr=np.log(close).diff()
    eligible=close.notna()&(close.rolling(252,min_periods=252).count()>=252)
    dates=pd.DatetimeIndex(pd.Series(close.index,index=close.index).groupby(close.index.to_period("M")).max().values)
    rows=[]
    for h in (21,63,126):
        minneg=max(10,h//2)
        # Matches source_only.kernel.rolling_downvol() sample-eligibility condition.
        downvol=lr.where(lr<0).rolling(h,min_periods=minneg).std(ddof=0)
        negative_counts=(lr<0).rolling(h,min_periods=h).sum()
        for date in dates:
            if not args.first_year<=date.year<=args.last_year:continue
            valid=eligible.loc[date]
            n=int(valid.sum())
            if n==0:continue
            x=downvol.loc[date,valid]
            negatives=negative_counts.loc[date,valid]
            rows.append({"year":int(date.year),"date":str(date.date()),"horizon":h,
                         "eligible_tickers":n,"required_negative_days":minneg,
                         "missing_fraction":float(x.isna().mean()),
                         "low_negative_days_fraction":float((negatives<minneg).mean()),
                         "mean_negative_days_fraction":float((negatives/h).mean())})
    out=Path(args.out);out.mkdir(parents=True,exist_ok=True)
    df=pd.DataFrame(rows)
    if df.empty:raise RuntimeError("No eligible observations")
    df.to_csv(out/"DOWNVOL_CAUSAL_MISSINGNESS_BY_MONTH.csv",index=False)
    df.groupby(["year","horizon"],as_index=False)[["missing_fraction","low_negative_days_fraction",
        "mean_negative_days_fraction"]].mean().to_csv(out/"DOWNVOL_ANNUAL_SUMMARY.csv",index=False)
    print(df.groupby("horizon")[["missing_fraction","mean_negative_days_fraction"]].mean().round(4).to_string())

if __name__=="__main__":main()
