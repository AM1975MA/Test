"""Read-only forensic review of >20% close-return flags across 3 frozen sources."""
from pathlib import Path
import argparse,json
import pandas as pd
import numpy as np
from data_quality_audit_v1.raw_census import load

def main():
 p=argparse.ArgumentParser()
 for key in ("r1","r2","r3","out"):p.add_argument("--"+key,required=True)
 args=p.parse_args(); roots=[getattr(args,f"r{i}") for i in (1,2,3)]
 data=[load(Path(x))[0] for x in roots]
 entries=[]
 for i,ds in enumerate(data,1):
  for ticker,x in sorted(ds.items()):
   r=x.Close.pct_change(fill_method=None)
   for loc in np.flatnonzero(r.abs().gt(.20).to_numpy()):
    if loc==0:raise ValueError("No previous bar for observed move")
    today=x.iloc[loc];before=x.iloc[loc-1]
    nextbar=x.iloc[loc+1] if loc+1<len(x) else None
    next_ret=(float(nextbar.Close/today.Close-1) if nextbar is not None else None)
    prev_vol=x.Volume.iloc[max(0,loc-21):loc]
    med_vol=float(prev_vol.median()) if len(prev_vol) else None
    opengap=float(today.Open/before.Close-1)
    intraday=float(today.Close/today.Open-1)
    entries.append(dict(repeat=i,ticker=ticker,date=x.index[loc].date().isoformat(),
     return_close=float(r.iloc[loc]),abs_return=float(abs(r.iloc[loc])),
     previous_close=float(before.Close),open=float(today.Open),high=float(today.High),
     low=float(today.Low),close=float(today.Close),
     volume=float(today.Volume),previous_volume=float(before.Volume),
     prior20_median_volume=med_vol,
     open_gap=opengap,intraday_return=intraday,
     next_close_return=next_ret,
     reversal_next_day=bool(next_ret is not None and np.sign(next_ret)==-np.sign(r.iloc[loc])),
     volume_is_zero=bool(today.Volume==0)))
 df=pd.DataFrame(entries)
 if len(df)!=123:raise ValueError(f"Original 123 alert observations not reproduced: {len(df)}")
 if df.duplicated(["repeat","ticker","date"]).any():raise ValueError("Duplicate events")
 unique=df.groupby(["ticker","date"],sort=True)
 events=[]
 for (ticker,date),group in unique:
  rets=group.set_index("repeat").return_close
  events.append(dict(ticker=ticker,date=date,
     repeats=",".join(map(str,sorted(rets.index.tolist()))),
     repeat_coverage=len(group),
     min_return=float(rets.min()),max_return=float(rets.max()),
     return_spread=float(rets.max()-rets.min()),
     avg_abs_return=float(group.abs_return.mean()),
     close_return_revisions_sign_change=bool(rets.min()*rets.max()<0),
     largest_abs_open_gap=float(group.open_gap.abs().max()),
     largest_abs_intraday_return=float(group.intraday_return.abs().max()),
     next_day_reversal_all=bool(group.reversal_next_day.all()),
     zero_volume_any=bool(group.volume_is_zero.any()),
     minimum_current_volume=float(group.volume.min())))
 unique_df=pd.DataFrame(events)
 out=Path(args.out);out.mkdir(parents=True,exist_ok=False)
 df.to_csv(out/"ALL_123_FLAGS.csv",index=False)
 unique_df.to_csv(out/"UNIQUE_EXTREME_EVENTS.csv",index=False)
 by_ticker=unique_df.groupby("ticker").agg(n_unique_events=("date","count"),
  max_abs_event=("avg_abs_return","max")).sort_values(["n_unique_events","max_abs_event"],ascending=False).reset_index()
 by_ticker.to_csv(out/"BY_TICKER.csv",index=False)
 all_three=unique_df.repeat_coverage.eq(3)
 sumry=dict(status="EXTREME_RETURN_FLAGS_DESCRIPTIVE_COMPLETE",
  snapshots=3,source_run=37121749852,
  observations=len(df),unique_ticker_date_events=len(unique_df),
  events_in_all_three=int(all_three.sum()),
  events_not_in_all_three=int((~all_three).sum()),
  affected_tickers=int(unique_df.ticker.nunique()),
  zero_volume_events=int(unique_df.zero_volume_any.sum()),
  all_repeats_next_day_reversal=int(unique_df.next_day_reversal_all.sum()),
  events_return_sign_changes_between_repeats=int(unique_df.close_return_revisions_sign_change.sum()),
  maximum_absolute_close_return=float(df.abs_return.max()),
  maximum_return_revision_same_event=float(unique_df.return_spread.max()),
  official_corporate_action_verified=False,
  classify_as_error_without_external_truth=False,
  data_corrected=False,models_trained=False,production_adoption=False)
 (out/"RESULT.json").write_text(json.dumps(sumry,indent=2,allow_nan=False)+"\n")
 lines=["# Investigation of the 123 historical >20% return flags","",
   "All original Yahoo snapshots remain unchanged. The thresholds are descriptive; flagged events are not automatically erroneous.","",
   f"- Total flagged ticker×date×snapshot observations: **{len(df)}**.",
   f"- Distinct ticker×date events across snapshots: **{len(unique_df)}**.",
   f"- Events present in all 3 snapshots: **{sumry['events_in_all_three']}**.",
   f"- Distinct affected tickers: **{sumry['affected_tickers']}**.",
   f"- Events with zero reported volume: **{sumry['zero_volume_events']}**.",
   f"- Events with next-day opposite sign in every reported vintage: **{sumry['all_repeats_next_day_reversal']}**.",
   "",
   "## Events sorted by absolute return","",
   "| Ticker | Date | Acquisitions | Return range | Gap max | Next-day reversal in all |",
   "|---|---|---|---:|---:|---|"]
 for e in unique_df.sort_values("avg_abs_return",ascending=False).to_dict("records"):
  lines.append(f"| {e['ticker']} | {e['date']} | {e['repeats']} | {e['min_return']:.2%} to {e['max_return']:.2%} | {e['largest_abs_open_gap']:.2%} | {e['next_day_reversal_all']} |")
 lines += ["","**No split/dividend authenticity verdict:** original adjusted OHLCV CSV does not retain the unadjusted close, split/dividend schedule or official issuer/exchange corroboration. An extreme move can be market-real, amplified by data provider/corporate action handling, or a bad print. Neither immediate reversal nor low volume alone proves which.",
 "","See all 123 per-vintage OHLCV observations, the deduplicated event list and ticker summary CSVs."]
 (out/"REPORT.md").write_text("\n".join(lines)+"\n")
 print("\n".join(lines[:12]),flush=True)

if __name__=="__main__":main()
