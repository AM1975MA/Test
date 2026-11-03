#!/usr/bin/env python3
"""E1: incremental *ex-post opportunity*, NEVER a trading-system backtest.

The historical baseline is a frozen OLC32 2021-2024 next-open-to-next-open
oracle snapshot. New ETF prices are independently downloaded from Yahoo via
yfinance; quote source, venue, lookback and exact calendar are audited.
Do NOT use these exploratory comparisons as live investment claims.
"""
from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
import hashlib
import json
import sys
import traceback

import numpy as np
import pandas as pd
import yfinance as yf

ROOT = Path(__file__).resolve().parent
OUT = ROOT / "results"
OUT.mkdir(parents=True, exist_ok=True)
BASE = ROOT / "baseline_oracle_2021_2024.csv"
# Only two EU listings were confirmed at the *venue* level before this run.
# The other EU suffixes are exploratory probes; verify identity before using.
CANDIDATES = [
    ("EU", "G2X.DE", "IE00BQQP9F84", "gold_miners_equity", "issuer_verified"),
    ("EU", "USPY.DE", "IE00BYPLS672", "cybersecurity", "web_verified"),
    ("EU", "CMOD.DE", "IE00BD6FTQ80", "diversified_commodity", "venue_unverified"),
    ("EU", "WCOA.DE", "IE00BYMLZY74", "diversified_commodity", "venue_unverified"),
    ("EU", "2B76.DE", "IE00BYZK4552", "automation_robotics", "venue_unverified"),
    ("USA", "BOTZ", "", "robotics", "web_verified"),
    ("USA", "LIT", "", "lithium_batteries", "web_verified"),
    ("USA", "PAVE", "", "infrastructure", "web_verified"),
]
MIN_PRIOR_OBSERVED = 500
START = "2018-01-01"
END_EXCLUSIVE = "2025-04-01"

def quote_series(ticker: str) -> pd.Series:
    hist = yf.download(
        ticker, start=START, end=END_EXCLUSIVE,
        interval="1d", auto_adjust=True, progress=False, threads=False,
    )
    if hist is None or hist.empty:
        raise ValueError("no historical rows")
    # yfinance may return a MultiIndex column even for one symbol.
    if isinstance(hist.columns, pd.MultiIndex):
        s = hist["Open"]
        if isinstance(s, pd.DataFrame):
            s = s.iloc[:, 0]
    else:
        s = hist["Open"]
    idx = pd.DatetimeIndex(s.index)
    if idx.tz is not None:
        idx = idx.tz_localize(None)
    s = pd.Series(pd.to_numeric(s.to_numpy(), errors="coerce"),
                  index=idx.normalize(), name=ticker)
    s = s[(np.isfinite(s)) & (s > 0)]
    if s.index.has_duplicates:
        raise ValueError("duplicate daily price dates")
    if len(s) < MIN_PRIOR_OBSERVED:
        raise ValueError("too few observed quote dates in complete history")
    return s.sort_index()

def main() -> None:
    baseline = pd.read_csv(BASE)
    assert len(baseline) == 96, "Expected 48 months x 2 regions"
    assert baseline.groupby("market").size().to_dict() == {"EU": 48, "USA": 48}
    assert all(baseline.entry_date < baseline.exit_date)
    records, qa = [], []
    for market, ticker, isin, theme, venue in CANDIDATES:
        try:
            prices = quote_series(ticker)
            entries = []
            for row in baseline[baseline.market == market].itertuples(index=False):
                # This 500-session threshold is only a coarse feature warm-up
                # screen; no pooled ML training/issuer PIT is certified here.
                prior_count = int((prices.index < pd.Timestamp(row.signal_date)).sum())
                entry = pd.Timestamp(row.entry_date)
                exit_ = pd.Timestamp(row.exit_date)
                ready = prior_count >= MIN_PRIOR_OBSERVED
                exact_dates = (entry in prices.index) and (exit_ in prices.index)
                if not (ready and exact_dates):
                    continue
                p0 = float(prices.loc[entry])
                p1 = float(prices.loc[exit_])
                r = 10000.0 * float(np.log(p1/p0))
                if not np.isfinite(r):
                    continue
                entries.append({
                    "market": market, "ticker": ticker, "isin": isin, "theme": theme,
                    "venue_status": venue, "signal_date": row.signal_date,
                    "entry_date": row.entry_date, "exit_date": row.exit_date,
                    "prior_observed_opens": prior_count, "candidate_logbp": r,
                    "original_oracle1_logbp": row.oracle_top1_logbp,
                    "original_oracle2_logbp": row.oracle_top2_logbp,
                    "single_add_oracle1_gain_logbp": max(0.0, r-row.oracle_top1_logbp),
                    "single_add_oracle2_gain_logbp": max(
                        0.0,
                        float(np.mean(sorted(
                            [r, row.oracle_top1_logbp,
                             2*row.oracle_top2_logbp - row.oracle_top1_logbp],
                            reverse=True)[:2])) - row.oracle_top2_logbp,
                    ),
                })
            records.extend(entries)
            qa.append({"market":market,"ticker":ticker,"isin":isin,"theme":theme,
                       "venue_status":venue,"status":"download_ok",
                       "n_original_price_dates":len(prices),
                       "first_open":str(prices.index.min().date()),
                       "last_open":str(prices.index.max().date()),
                       "matched_months":len(entries),"quote_currency_status":"verify listing currency"})
        except Exception as exc:
            qa.append({"market":market,"ticker":ticker,"isin":isin,"theme":theme,
                       "venue_status":venue,"status":"download_error",
                       "error":repr(exc),"matched_months":0})
            print(f"WARNING {ticker}: {exc}",file=sys.stderr)
    pd.DataFrame(qa).to_csv(OUT/"candidate_quote_quality.csv",index=False)
    if not records:
        (OUT/"STATUS.txt").write_text(
            "NO COMPARABLE NEW PRICES. E1 not evaluable. Read candidate_quote_quality.csv\n")
        raise RuntimeError("All candidate quote downloads/matches failed; no E1 conclusion.")
    rowdf = pd.DataFrame.from_records(records)
    rowdf.to_csv(OUT/"candidate_monthly_labels.csv",index=False)

    # Only verified venues count toward primary E1 aggregate. The provisional
    # symbols remain visible for diagnosis, never silently merged.
    accepted = rowdf[rowdf.venue_status != "venue_unverified"]
    primary = []
    for row in baseline.itertuples(index=False):
        new = accepted[(accepted.market == row.market) &
                       (accepted.signal_date == row.signal_date)]
        prices = new.candidate_logbp.to_list()
        old_second = 2.0*float(row.oracle_top2_logbp) - float(row.oracle_top1_logbp)
        new_best = sorted([float(row.oracle_top1_logbp),old_second]+prices,reverse=True)
        primary.append({
            "market":row.market,"signal_date":row.signal_date,
            "entry_date":row.entry_date,"exit_date":row.exit_date,
            "eligible_new":len(prices),"original_n":int(row.original_n),
            "oracle1_old_logbp":row.oracle_top1_logbp,
            "oracle1_expanded_logbp":new_best[0],
            "oracle1_gain_logbp":max(0.0,new_best[0]-row.oracle_top1_logbp),
            "oracle2_old_logbp":row.oracle_top2_logbp,
            "oracle2_expanded_logbp":np.mean(new_best[:2]),
            "oracle2_gain_logbp":max(0.0,np.mean(new_best[:2])-row.oracle_top2_logbp),
        })
    p = pd.DataFrame(primary)
    assert len(p) == 96
    assert (p.oracle1_gain_logbp >= -1e-8).all()
    assert (p.oracle2_gain_logbp >= -1e-8).all()
    p.to_csv(OUT/"incremental_oracle_primary_monthly.csv",index=False)
    summ = p.groupby("market").agg(
        months=("signal_date","count"),
        months_with_new_quotes=("eligible_new",lambda v:int((v>0).sum())),
        months_new_best=("oracle1_gain_logbp",lambda v:int((v>1e-8).sum())),
        mean_oracle1_gain_logbp=("oracle1_gain_logbp","mean"),
        mean_oracle2_gain_logbp=("oracle2_gain_logbp","mean"),
    ).reset_index()
    summ.to_csv(OUT/"incremental_oracle_primary_summary.csv",index=False)
    manifest={
        "generated_utc":datetime.now(timezone.utc).isoformat(),
        "method":"EXPOST ORACLE ONLY, NOT FORECAST OR EXECUTABLE PERFORMANCE",
        "baseline_sha256":hashlib.sha256(BASE.read_bytes()).hexdigest(),
        "quote_provider":"Yahoo via yfinance adjusted daily Open",
        "historical_series":f"{START} to {END_EXCLUSIVE} exclusive",
        "costs":"not applied; gross theoretical ceiling only",
        "minimum_prior_observed_daily_opens":MIN_PRIOR_OBSERVED,
        "exact_entry_exit_dates_required":True,
        "unverified_venues_excluded_from_primary":True,
        "critical_caveats":["survivorship selection as of 2026","calendar and venue currency identity",
                            "quote adjustments and vendor drift","no bid/ask or slippage",
                            "past period heavily researched; ex-post not live alpha",
                            "new ETF not scored or trained by original models"],
        "python_version":sys.version,"pandas_version":pd.__version__,
        "yfinance_version":getattr(yf,"__version__","unknown"),
    }
    (OUT/"manifest.json").write_text(json.dumps(manifest,indent=2))
    print(summ.to_string(index=False))

if __name__ == "__main__":
    main()
