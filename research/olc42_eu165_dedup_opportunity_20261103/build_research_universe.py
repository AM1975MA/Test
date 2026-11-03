#!/usr/bin/env python3
"""OLC42 EU152 guarded research-universe derivation (not an investible universe).

Inputs are frozen OLC41 2026 metadata snapshots; equal current index names are
not proof of historical share-class or economic equivalence. NEVER write main
universe files, weights, OLC19 NAV, or an ETF price history from this script.
"""
import argparse
import csv
import io
from pathlib import Path


FOLDER = Path(__file__).resolve().parent
RESEARCH = FOLDER.parent
SOURCE = RESEARCH / "olc41_eu165_acc_census_20261103" / "results"
ORIGINAL = (RESEARCH / "olc39_eu_holdings_identity_20261103" /
            "migration_acc_guarded_20261103" / "EU165_original_universe.csv")
FIELDS_KEEP = [
    "market", "ticker", "current_policy_snapshot2026", "isin_snapshot2026",
    "index_snapshot2026", "first_observed_open", "pre_signal2021_observed",
    "observed_2021_24", "full_history_gate", "pit_issuer_venue_verified",
    "status", "production_applied"
]
FIELDS_REMOVED = [
    "dist_ticker", "dist_isin_snapshot2026", "acc_kept",
    "acc_isin_snapshot2026", "index_snapshot2026", "dist_full_history",
    "acc_full_history", "full_economic_PIT_verified", "identity_status",
    "operation", "production_applied"
]


def read_csv(path):
    with Path(path).open(encoding="utf-8-sig", newline="") as fd:
        return list(csv.DictReader(fd))


def to_csv(columns, records):
    s = io.StringIO(newline="")
    w = csv.DictWriter(s, fieldnames=columns, lineterminator="\n")
    w.writeheader()
    w.writerows(records)
    return s.getvalue()


def guarded_build():
    original = read_csv(ORIGINAL)
    census = read_csv(SOURCE / "EU165_DISTRIBUTION_POLICY_CENSUS.csv")
    candidates = read_csv(SOURCE / "EU69_DIST_CANDIDATE_AUDIT.csv")
    assert len(original) == len(census) == 165, "Full universe mismatch"
    assert len(candidates) == 69, "Full Dist census mismatch"
    keys = [r["ticker"] for r in original]
    assert len(set(keys)) == 165 and all(r["market"] == "EU" for r in original)
    indexed = {r["ticker"]: r for r in census}
    assert set(keys) == set(indexed)
    pairs = [r for r in candidates
             if r["status"] == "INTERNAL_SAME_INDEX_PRICE_PASS_DUPLICATE_REVIEW"]
    assert len(pairs) == 13, "Unexpected same-index screen size"
    assert len({p["dist_ticker"] for p in pairs}) == 13
    removed = []
    for x in pairs:
        dist, acc = indexed[x["dist_ticker"]], indexed[x["preferred_internal_acc_ticker"]]
        assert dist["current_policy"] == "Distributing"
        assert acc["current_policy"] == "Accumulating"
        assert dist["original_price_history_gate"] == "True"
        assert acc["original_price_history_gate"] == "True"
        assert x["dist_full_price_history"] == x["preferred_acc_history_pass"] == "True"
        assert x["would_duplicate_existing_universe"] == "yes"
        assert acc["first_observed_open"] <= "2019-02-01"
        assert int(acc["pre_first_2021_signal_obs"]) >= 500
        assert int(acc["valid_obs_2021_2024"]) >= 1021
        removed.append(dict(
            dist_ticker=x["dist_ticker"],
            dist_isin_snapshot2026=x["dist_isin_snapshot"],
            acc_kept=x["preferred_internal_acc_ticker"],
            acc_isin_snapshot2026=x["preferred_internal_acc_isin_snapshot"],
            index_snapshot2026=x["dist_index_snapshot"],
            dist_full_history=x["dist_full_price_history"],
            acc_full_history=x["preferred_acc_history_pass"],
            full_economic_PIT_verified="NO",
            identity_status="2026_SAME_INDEX_DIFFERENT_FUNDS_REVIEW",
            operation="EXCLUDE_DIST_FROM_RESEARCH_UNIVERSE_ONLY",
            production_applied="NO"
        ))
    exclude = {r["dist_ticker"] for r in removed}
    kept = []
    for r in original:
        name = r["ticker"]
        if name in exclude:
            continue
        row = indexed[name]
        kept.append(dict(
            market="EU", ticker=name,
            current_policy_snapshot2026=row["current_policy"],
            isin_snapshot2026=row["isin_snapshot_2026"],
            index_snapshot2026=row["index_snapshot_2026"],
            first_observed_open=row["first_observed_open"],
            pre_signal2021_observed=row["pre_first_2021_signal_obs"],
            observed_2021_24=row["valid_obs_2021_2024"],
            full_history_gate=row["original_price_history_gate"],
            pit_issuer_venue_verified=row["metadata_PIT_verified"],
            status="RESEARCH_ONLY_2026_CATALOG", production_applied="NO"
        ))
    assert len(kept) == 152 and len({r["ticker"] for r in kept}) == 152
    assert sum(x["current_policy_snapshot2026"] == "Accumulating" for x in kept) == 96
    assert sum(x["current_policy_snapshot2026"] == "Distributing" for x in kept) == 56
    assert sum(x["full_history_gate"] != "True" for x in kept) == 24
    assert not exclude.intersection(r["ticker"] for r in kept)
    assert "IM2A.DE" in exclude and "EEAA.DE" in {r["ticker"] for r in kept}
    return kept, removed


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--check-only", action="store_true",
                        help="Match frozen research outputs; never overwrite")
    parser.add_argument("--out", default=str(FOLDER / "results"))
    args = parser.parse_args()
    kept, removed = guarded_build()
    artifacts = {
        "EU152_RESEARCH_UNIVERSE_NOT_PROMOTED.csv": to_csv(FIELDS_KEEP, kept),
        "EU13_DIST_EXCLUDED_RESEARCH_ONLY.csv": to_csv(FIELDS_REMOVED, removed)
    }
    out = Path(args.out)
    for name, content in artifacts.items():
        p = out / name
        if args.check_only:
            assert p.read_text(encoding="utf-8") == content, name + " differs"
        else:
            out.mkdir(parents=True, exist_ok=True)
            p.write_text(content, encoding="utf-8")
        print(name, "validated" if args.check_only else "written")
    print("EU165 -> EU152 (96 Acc, 56 Dist); 13 Dist flagged, not executed")


if __name__ == "__main__":
    main()
