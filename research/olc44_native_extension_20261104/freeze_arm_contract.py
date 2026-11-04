#!/usr/bin/env python3
"""OLC44-N1: immutable base universe + factorial experiment-arm constructor.

The 2026-catalogue EU152 is explicitly NOT point-in-time certified.  This
script does not adjust NAV, impute prices, or claim a trained model.

Inputs: original OLC41/42 membership/census, legacy USA149 roster,
and OLC46 as-of historical price/feature gate.
"""
from __future__ import annotations

import argparse
from pathlib import Path
import hashlib
import json
import pandas as pd

LOCAL = Path(__file__).resolve().parent
PROJECT = LOCAL.parents[1]
SOURCE_OLC42 = Path("source_olc42")
if not SOURCE_OLC42.exists():
    SOURCE_OLC42 = Path("..") / "source_olc42"
RESULTS = LOCAL / "results"
RESULTS.mkdir(parents=True, exist_ok=True)

CENSUS = SOURCE_OLC42 / "research/olc41_eu165_acc_census_20261103/results/EU165_DISTRIBUTION_POLICY_CENSUS.csv"
EU152 = SOURCE_OLC42 / "research/olc42_eu165_dedup_opportunity_20261103/results/EU152_RESEARCH_UNIVERSE_NOT_PROMOTED.csv"
DELETED = SOURCE_OLC42 / "research/olc42_eu165_dedup_opportunity_20261103/results/EU13_DIST_EXCLUDED_RESEARCH_ONLY.csv"
USA = PROJECT / "etf-trader-v3 corrected/fullstack_legacy/data/ETF_UNIVERSE.csv"
GATES = PROJECT / "research/olc46_price_integrity/results/asof_feature_eligibility_summary.csv"

EU_ADD = {"G2X.DE", "USPY.DE", "WTIC.DE", "2B76.DE"}
US_ADD = {"BOTZ", "LIT", "PAVE"}
ARMS = {
    "EU165_ORIGINAL": ("EU", "ORIGINAL", False),
    "EU152_DEDUP_RESEARCH": ("EU", "DEDUP", False),
    "EU165_PLUS4": ("EU", "ORIGINAL", True),
    "EU152_PLUS4": ("EU", "DEDUP", True),
    "USA149_ORIGINAL": ("USA", "ORIGINAL", False),
    "USA149_PLUS3": ("USA", "ORIGINAL", True),
}

def source_digest(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()

def assert_no_duplicate_keys(df, label: str):
    if df.ticker.isna().any() or df.ticker.duplicated().any():
        raise AssertionError(f"Duplicate or empty ticker in {label}")

def build():
    cen = pd.read_csv(CENSUS, dtype=str).fillna("")
    ded = pd.read_csv(EU152, dtype=str).fillna("")
    removed = pd.read_csv(DELETED, dtype=str).fillna("")
    us = pd.read_csv(USA, dtype=str).fillna("")
    eligible = pd.read_csv(GATES, dtype=str).fillna("")
    for data, name, n in [(cen, "EU165", 165), (ded, "EU152", 152),
                           (removed, "13 potential duplicates", 13)]:
        if len(data) != n:
            raise AssertionError(f"{name} has {len(data)} rows; expected {n}")
    assert_no_duplicate_keys(cen, "EU165")
    assert_no_duplicate_keys(ded, "EU152")
    actual_us = us.loc[us.usable.eq("1"), "ticker"].tolist()
    if len(actual_us) != 149 or len(set(actual_us)) != 149:
        raise AssertionError(f"USA usable roster mismatch: {len(actual_us)}")
    old = set(cen.ticker)
    sub = set(ded.ticker)
    excludes = set(removed.dist_ticker)
    if not sub.issubset(old) or old - sub != excludes:
        raise AssertionError("EU152 is not exactly EU165 minus audited 13")
    if not (set(removed.acc_kept) <= sub):
        raise AssertionError("At least one saved acc candidate missing from EU152")
    if not (EU_ADD.isdisjoint(old) and US_ADD.isdisjoint(actual_us)):
        raise AssertionError("One new ETF already exists in the original population")

    # Endogenous PIT inputs should be rebuilt from source-price history in
    # the native pipeline. Here we can certify only the previous 48/48
    # month E1 quote gate, not point-in-time fund identity.
    for market, tset in [("EU", EU_ADD), ("USA", US_ADD)]:
        rows = eligible[eligible.market.eq(market) & eligible.ticker.isin(tset)]
        if set(rows.ticker) != tset:
            raise AssertionError("Missing OLC46 as-of warmup records")
        for r in rows.itertuples(index=False):
            if r.eligible_252_full_ohlc != "48":
                raise AssertionError(f"New ETF lacks 252-session OHLC readiness: {r.ticker}")

    eu165 = {r.ticker: (r.current_policy, r.isin_snapshot_2026, r.first_observed_open)
             for r in cen.itertuples(index=False)}
    eu152 = {r.ticker: (r.current_policy_snapshot2026, r.isin_snapshot2026,
                        r.first_observed_open)
             for r in ded.itertuples(index=False)}
    usa149 = {x: ("UNKNOWN", "", "") for x in actual_us}
    added_eu = {x: ("NEW_CANDIDATE", "", "") for x in EU_ADD}
    added_usa = {x: ("NEW_CANDIDATE", "", "") for x in US_ADD}
    out_rows, summary = [], []
    for name, (market, selection, expand) in ARMS.items():
        if market == "EU":
            universe = dict(eu165 if selection == "ORIGINAL" else eu152)
            if expand:
                universe.update(added_eu)
            baseline = "EU165" if selection == "ORIGINAL" else "EU152_RESEARCH"
            expected = (165 if selection == "ORIGINAL" else 152) + (4 if expand else 0)
        else:
            universe = dict(usa149)
            if expand:
                universe.update(added_usa)
            baseline = "USA149"
            expected = 149 + (3 if expand else 0)
        if len(universe) != expected:
            raise AssertionError(f"Arm {name} is not exactly {expected} unique tickers")
        for ticker, (policy, isin, first_open) in sorted(universe.items()):
            out_rows.append({
                "arm": name, "market": market, "ticker": ticker,
                "original_roster": baseline,
                "is_new": int(ticker in EU_ADD or ticker in US_ADD),
                "share_class_snapshot2026": policy,
                "isin_snapshot2026": isin, "first_observed_open": first_open,
                "point_in_time_identity_certified": False,
                "asof_eligibility_required": True,
            })
        summary.append({
            "arm": name, "market": market, "member_count": len(universe),
            "new_tickers": 4 if market == "EU" and expand else 3 if expand else 0,
            "research_only": True,
            "native_score_retrained": False,
            "score_PIT_verified": False,
            "cagr_measured": False,
            "roster_basis": baseline,
        })
    membership = pd.DataFrame(out_rows)
    assert not membership.duplicated(["arm", "ticker"]).any()
    if membership.groupby("arm").size().to_dict() != {
            "EU165_ORIGINAL":165,"EU152_DEDUP_RESEARCH":152,
            "EU165_PLUS4":169,"EU152_PLUS4":156,
            "USA149_ORIGINAL":149,"USA149_PLUS3":152}:
        raise AssertionError("Unexpected cardinality after freezing arms")
    membership.to_csv(RESULTS/"OLC44N_ARM_MEMBERSHIP.csv",index=False)
    pd.DataFrame(summary).to_csv(RESULTS/"OLC44N_ARMS.csv",index=False)
    manifest = {
        "source_digests": {p.name:source_digest(p) for p in
                           [CENSUS,EU152,DELETED,USA,GATES]},
        "source_OLC42_branch": "research/olc42-eu165-dedup-opportunity-20261103",
        "new_ETFs_EU": sorted(EU_ADD),
        "new_ETFs_USA": sorted(US_ADD),
        "dedup_13_pairs_verified_point_in_time": False,
        "model_training_completed": False,
        "legacy_baseline_cagr_this_run": None,
        "arms": list(ARMS),
        "warning": "Rosters are fixed 2026 universe definitions. Historical eligibility must be computed as of signal date. Source labels cannot be reused unchanged after membership changes."
    }
    (RESULTS/"OLC44N_CONTRACT.json").write_text(json.dumps(manifest,indent=2,sort_keys=True)+"\n")
    print(pd.DataFrame(summary).to_string(index=False))
    return membership, pd.DataFrame(summary)

if __name__ == "__main__":
    build()
