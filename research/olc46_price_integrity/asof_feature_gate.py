#!/usr/bin/env python3
"""OLC46-D2 prequential eligibility: can expanded ETF/ETC enter native features?

Read-only source-frozen monthly calendar, 2017+ observed quotes, lookbacks
ending STRICTLY before the corresponding signal date. Records missing OHLC
rather than imputation. No future returns/target in eligibility logic.
"""
from pathlib import Path
import hashlib,json,datetime
import numpy as np,pandas as pd,yfinance as yf
ROOT=Path(__file__).resolve().parent
OUT=ROOT/"results"
CAL=pd.read_csv(ROOT/"OLC32_FROZEN_2021_2024_CALENDAR.csv",parse_dates=["signal_date","entry_date","exit_date"])
UNIVERSE={
"EU":["G2X.DE","USPY.DE","WTIC.DE","2B76.DE","PHAG.MI","NGAS.MI","CMOD.MI"],
"USA":["BOTZ","LIT","PAVE"],
}
MASKED={"PHAG.MI","NGAS.MI","CMOD.MI"}
LOOKBACKS=(63,126,252)
def get(ticker):
    if ticker in MASKED:
        p=OUT/(ticker.replace(".","_")+"_quality_masked.csv.gz")
        if not p.exists():raise FileNotFoundError(p)
        x=pd.read_csv(p,parse_dates=["date"]).set_index("date")
    else:
        x=yf.Ticker(ticker).history(start="2017-01-01",end="2026-07-05",
            interval="1d",auto_adjust=False,repair=False,actions=False)
        if x is None or x.empty:raise ValueError("missing Yahoo quote")
        if isinstance(x.columns,pd.MultiIndex):x.columns=x.columns.get_level_values(0)
        x.columns=[v.lower().replace(" ","_") for v in x.columns]
        idx=pd.DatetimeIndex(x.index)
        if idx.tz is not None:idx=idx.tz_localize(None)
        x.index=idx.normalize()
        x.index.name="date"
        hl_ok=(x.high>=x[["open","close"]].max(axis=1)) & (x.low<=x[["open","close"]].min(axis=1)) & (x.high>=x.low)
        x["high"]=x.high.where(hl_ok)
        x["low"]=x.low.where(hl_ok)
    x.index=pd.DatetimeIndex(x.index).normalize()
    if x.index.has_duplicates:raise ValueError("duplicate date")
    x=x.sort_index()
    for c in ["open","high","low","close"]:x[c]=pd.to_numeric(x[c],errors="coerce")
    return x
def main():
    records=[];summary=[]
    for market,tickers in UNIVERSE.items():
      for ticker in tickers:
        try:
            q=get(ticker)
            bad_O_C=(~np.isfinite(q.open))|(~np.isfinite(q.close))|(q.open<=0)|(q.close<=0)
            missing_H_L=(~np.isfinite(q.high))|(~np.isfinite(q.low))
            history_good=int((~bad_O_C).sum())
            summary.append({"market":market,"ticker":ticker,"status":"loaded",
                   "n_dates":len(q),"n_open_close_good":history_good,
                   "n_high_low_missing_or_invalid":int(missing_H_L.sum()),
                   "first":str(q.index.min().date()),"last":str(q.index.max().date())})
            for row in CAL.loc[CAL.market==market].itertuples(index=False):
                # Historical information cutoff strictly before signal.
                h=q.loc[q.index<row.signal_date]
                obs=h.loc[(h.open>0)&(h.close>0)&np.isfinite(h.open)&np.isfinite(h.close)]
                recent=obs.tail(252)
                rec={"market":market,"ticker":ticker,"signal_date":str(row.signal_date.date()),
                    "entry_date":str(row.entry_date.date()),"exit_date":str(row.exit_date.date()),
                    "n_original_opens_before_signal":len(obs),
                    "warmup_500_eligible":len(obs)>=500,
                    "open_close_252_eligible":len(recent)>=252,
                    "last_observed_before_signal":str(obs.index.max().date()) if len(obs) else "",
                    "latest_quote_age_calendar_days":int((row.signal_date-obs.index.max()).days) if len(obs) else -1}
                for n in LOOKBACKS:
                    last=obs.tail(n)
                    rec[f"oc_{n}"]=len(last)==n
                    rec[f"hl_missing_{n}"]=int(((~np.isfinite(last.high))|(~np.isfinite(last.low))).sum()) if len(last)==n else -1
                    rec[f"fully_valid_ohlc_{n}"]=len(last)==n and rec[f"hl_missing_{n}"]==0
                # The monthly gating must NOT consider the target return,
                # which matures later, or future bar-quality flags.
                records.append(rec)
        except Exception as e:
            summary.append({"market":market,"ticker":ticker,"status":"ERROR","error":repr(e)})
    pd.DataFrame(summary).to_csv(OUT/"candidate_coverage_summary.csv",index=False)
    m=pd.DataFrame(records)
    m.to_csv(OUT/"feature_eligibility_asof_2021_2024.csv",index=False)
    if len(m)!=10*48:raise RuntimeError("candidate/month matrix not complete")
    if not m.warmup_500_eligible.all():raise RuntimeError("at least one 2021-24 ticker fails 500-day lookback")
    chk=m.groupby(["market","ticker"]).agg(
       months=("signal_date","count"),
       eligible_63_oc=("oc_63","sum"),eligible_126_oc=("oc_126","sum"),
       eligible_252_oc=("oc_252","sum"),
       eligible_252_full_ohlc=("fully_valid_ohlc_252","sum"),
       median_bad_hl_252=("hl_missing_252","median"),
       max_age_days=("latest_quote_age_calendar_days","max"),
    ).reset_index()
    chk.to_csv(OUT/"asof_feature_eligibility_summary.csv",index=False)
    print(chk.to_string(index=False),flush=True)
    (OUT/"native_readiness_manifest.json").write_text(json.dumps({
       "basis":"OLC32 2021-24 exact 48 date calendar; previous quotes only",
       "trained_natively":False,"complete_olc19_pipeline_rerun":False,
       "candidate_count":10,
       "quote_hl_quality":"invalid H/L intentionally NaN; do not backfill",
       "source_baseline_sha256":hashlib.sha256((ROOT/"OLC32_FROZEN_2021_2024_CALENDAR.csv").read_bytes()).hexdigest(),
       "restriction":"O/C feature eligibility is NOT 42-feature input parity, model training certification, or instrument-day execution eligibility",
       "date_generated_utc":datetime.datetime.now(datetime.timezone.utc).isoformat(),
    },indent=2))
    if (pd.DataFrame(summary).status=="ERROR").any():raise RuntimeError("some candidate histories failed")
if __name__=="__main__":main()
