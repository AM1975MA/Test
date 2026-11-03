#!/usr/bin/env python3
"""Independently compare refreshed Yahoo adjusted-Open 21D O2O returns with
the source-frozen OLC32 rows for four *existing* fund tickers on exact dates.

NOT evidence of point-in-time issuer metadata, tradeable execution or fresh
holdout: it is a quote-vintage reconciliation guard against vendor drift.
"""
from __future__ import annotations
from pathlib import Path
import numpy as np
import pandas as pd
from run_candidate_oracle import quote_series

ROOT = Path(__file__).resolve().parent
SOURCE = ROOT / "source_controls_vintage_2021_24.csv"
OUT = ROOT / "results"
OUT.mkdir(exist_ok=True)

def main():
    rows=pd.read_csv(SOURCE)
    results=[]
    for (market,ticker), c in rows.groupby(["market","ticker"]):
        prices=quote_series(ticker)
        for r in c.itertuples(index=False):
            entry=pd.Timestamp(r.entry_date); exit_=pd.Timestamp(r.exit_date)
            if entry not in prices.index or exit_ not in prices.index:
                results.append({"market":market,"ticker":ticker,"signal_date":r.signal_date,
                                "status":"missing_open","source_logbp":r.r_o2o_bp})
                continue
            y=1e4*np.log(float(prices.loc[exit_])/float(prices.loc[entry]))
            diff=y-float(r.r_o2o_bp)
            results.append({"market":market,"ticker":ticker,"signal_date":r.signal_date,
                            "status":"matched","source_logbp":float(r.r_o2o_bp),
                            "new_vendor_logbp":y,"diff_new_minus_source_bp":diff,
                            "abs_diff_bp":abs(diff)})
    matched=pd.DataFrame(results)
    matched.to_csv(OUT/"control_quote_vintage_monthly.csv",index=False)
    v=matched[matched.status=="matched"]
    summ=v.groupby(["market","ticker"]).agg(
        n=("signal_date","count"),mean_signed_diff_bp=("diff_new_minus_source_bp","mean"),
        mean_abs_diff_bp=("abs_diff_bp","mean"),
        median_abs_diff_bp=("abs_diff_bp","median"),
        q95_abs_diff_bp=("abs_diff_bp",lambda a:float(np.quantile(a,.95))),
        max_abs_diff_bp=("abs_diff_bp","max"),
        gt_50_bp=("abs_diff_bp",lambda a:int((a>50).sum())),
        gt_100_bp=("abs_diff_bp",lambda a:int((a>100).sum()))
    ).reset_index()
    summ.to_csv(OUT/"control_quote_vintage_summary.csv",index=False)
    print(summ.to_string(index=False,float_format=lambda x:f"{x:.3f}"))
    if len(matched)!=192 or len(v)!=192:
        raise RuntimeError("Source vintage control calendar missing/invalid")
    # Alert only: any historical adjusted-quote discrepancy materially above
    # one ETF's ordinary corporate-action drift requires further review.
    if (summ.q95_abs_diff_bp>50).any():
        (OUT/"QUOTE_SOURCE_ALERT.txt").write_text(
            "ALERT: significant quote-source drift; do NOT promote E1 as economic simulation.\n")
        print("WARNING: quote source drift above q95=50bp; further QC required")
if __name__=="__main__": main()
