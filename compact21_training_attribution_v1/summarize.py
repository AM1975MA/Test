"""Independently rebuild pooled 114-query comparisons from physical prediction vectors."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd

from compact21_semidev_v1.view import sha
from compact21_predictive_v2.summarize import normalized_numeric
from ranker_stability_v1.run_ranker_benchmark_full import stability

LINE = "COMPACT21_TRAINING_SOURCE_ATTRIBUTION_V1"
YEARS = range(2017, 2027)
VARIANTS = ("BASE_NATIVE", "OWN_X_R2_Y", "R2_X_OWN_Y", "R2_X_R2_Y_NEGATIVE")
PAIRS = ((1, 2), (1, 3), (2, 3))
KEYS = ["signal_date", "ticker"]


def evaluate_vectors(frames, variant):
    base = frames.loc[frames.variant.eq(variant)]
    coverage = []
    preds = {}
    for vintage in (1, 2, 3):
        df = base.loc[base.vintage.eq(vintage)].sort_values(KEYS).reset_index(drop=True)
        if df.empty or df.duplicated(KEYS).any() or not np.isfinite(df.pred.to_numpy()).all():
            raise ValueError("Invalid/missing common vintage prediction")
        coverage.append(df[KEYS])
        preds[vintage] = df.pred.to_numpy()
    for others in coverage[1:]:
        pd.testing.assert_frame_equal(coverage[0], others, check_exact=True)
    per_pair = {f"{i}-{j}": stability(coverage[0], preds[i], preds[j])
                for i, j in PAIRS}
    return per_pair, len(coverage[0]), int(coverage[0].signal_date.nunique())


def summarize(root: Path):
    all_frames = []
    hashes = None
    for year in YEARS:
        directory = root / f"attribution-{year}"
        result_path, vector_path = directory / "RESULT.json", directory / "PREDICTIONS.parquet"
        r = json.loads(result_path.read_text())
        if (r.get("line"), r.get("status"), r.get("year")) != (LINE, LINE + "_COMPLETE", year):
            raise ValueError("Missing/invalid annual result")
        if r.get("prediction_file_sha256") != sha(vector_path) or \
           r.get("production_adoption") is not False or \
           r.get("negative_feedback_changed") is not False or \
           r.get("portfolio_evaluation") is not False or \
           r.get("deployable_treatment") is not False:
            raise ValueError("Prediction provenance/research-only contract mismatch")
        if not r["input_contract"]["train_keys_are_identical"]:
            raise ValueError("Unexpected training cohort handling")
        if not all(x.get("independent_refits_exact") is True
                   for name, x in r["per_variant"].items()
                   if name in ("OWN_X_R2_Y", "R2_X_OWN_Y")):
            raise ValueError("Refit proof missing")
        if not all(v.get("native_bytes_exact") and v.get("common_bytes_exact")
                   and v.get("metadata_exact") for v in r["controls"].values()):
            raise ValueError("Original BASE exact parity missing")
        fixed = (r["input_sha256"], r["fit_sources"],
                 r["preregistration_sha256"], normalized_numeric(r["numeric_contract"]),
                 r["reference_baseline_sha256"])
        if hashes is None:
            hashes = fixed
        elif fixed != hashes:
            raise ValueError("Different frozen sources or runtime across folds")
        df = pd.read_parquet(vector_path)
        if list(df.columns) != KEYS + ["pred", "variant", "vintage"] or set(df.variant) != set(VARIANTS):
            raise ValueError("Wrong prediction vector schema")
        if not df.signal_date.dt.year.eq(year).all() or df.duplicated(KEYS + ["variant", "vintage"]).any():
            raise ValueError("Invalid duplicate or out-of-year predictions")
        if df[KEYS].isna().any().any():
            raise ValueError("Null prediction keys")
        for variant in VARIANTS:
            pair, _, _ = evaluate_vectors(df, variant)
            for k, expected in r["per_variant"][variant]["pair_metrics"].items():
                if set(pair[k]) != set(expected) or any(
                    not np.isclose(pair[k][metric], expected[metric], rtol=0, atol=1e-12)
                    for metric in expected):
                    raise ValueError("Independent annual recomputation differs")
        all_frames.append(df)
    whole = pd.concat(all_frames, ignore_index=True)
    reports = {}
    row_counts, n_dates = None, None
    for variant in VARIANTS:
        metrics, nrows, ndates = evaluate_vectors(whole, variant)
        reports[variant] = {"pairs": metrics,
                            "rank_mad_mean_equal_pairs": float(np.mean([m["rank_mean_abs"] for m in metrics.values()])),
                            "top1_disagreement_mean_equal_pairs": float(np.mean(
                                [m["top1_disagreement_fraction"] for m in metrics.values()])),
                            "spearman_mean_equal_pairs": float(np.mean(
                                [m["mean_daily_spearman"] for m in metrics.values()])),
                            "row_count_per_vintage": nrows, "date_count": ndates}
        if row_counts is None:
            row_counts, n_dates = nrows, ndates
        elif (row_counts, n_dates) != (nrows, ndates):
            raise ValueError("Variant cohorts differ")
    if n_dates != 114:
        raise ValueError(f"Incomplete 114-month evaluation: {n_dates}")
    base = reports["BASE_NATIVE"]
    for name, r in reports.items():
        r["rank_mad_change_vs_BASE_percent"] = float(
            100 * (r["rank_mad_mean_equal_pairs"] / base["rank_mad_mean_equal_pairs"] - 1))
        r["top1_change_vs_BASE_pp"] = float(
            100 * (r["top1_disagreement_mean_equal_pairs"] -
                   base["top1_disagreement_mean_equal_pairs"]))
    zero = reports["R2_X_R2_Y_NEGATIVE"]
    if zero["rank_mad_mean_equal_pairs"] != 0.0 or zero["top1_disagreement_mean_equal_pairs"] != 0.0:
        raise ValueError("Negative control must be exactly stable")
    return {
        "status": "ATTRIBUTION_DIAGNOSTIC_COMPLETE", "production_adoption": False,
        "years": list(YEARS), "total_months": n_dates, "total_rows_per_vintage": row_counts,
        "data": "three correlated repeats of Original149; reused historical development data",
        "interpretation_scope": "paired training-factor sensitivity, NOT improvement/production/OOS/CAGR",
        "models": reports, "all_integrity_checks": True}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--inputs", type=Path, required=True)
    ap.add_argument("--out", type=Path, required=True)
    args = ap.parse_args()
    if args.out.exists() and any(args.out.iterdir()):
        raise ValueError("Fresh summary output required")
    args.out.mkdir(parents=True, exist_ok=True)
    report = summarize(args.inputs)
    (args.out / "SUMMARY.json").write_text(json.dumps(report, indent=2, allow_nan=False) + "\n")
    rows = ["# Compact21 feature/label training-source attribution", "",
            "Research-only four-cell factorial; controls verified across 2017–2026.",
            "Metrics are on 114 monthly inference dates, shared Repeat2 feature inputs.",
            "Do not read factor contrasts as additive, deployable or prospective performance.",
            "",
            "| Training-source cell | Rank-MAD | Rank-MAD change vs BASE | Top1 disagreement | Top1 change (pp) |",
            "|---|---:|---:|---:|---:|"]
    for name, r in report["models"].items():
        rows.append(f"| {name} | {r['rank_mad_mean_equal_pairs']:.6f} | "
                    f"{r['rank_mad_change_vs_BASE_percent']:+.2f}% | "
                    f"{100*r['top1_disagreement_mean_equal_pairs']:.2f}% | "
                    f"{r['top1_change_vs_BASE_pp']:+.2f} |")
    rows += ["", "## Pair-level results", ""]
    for name, r in report["models"].items():
        rows.append(f"### {name}")
        rows.append("| Pair | Rank-MAD | Top1 disagreement | Spearman |")
        rows.append("|---|---:|---:|---:|")
        for pair, m in r["pairs"].items():
            rows.append(f"| {pair} | {m['rank_mean_abs']:.6f} | "
                        f"{100*m['top1_disagreement_fraction']:.2f}% | "
                        f"{m['mean_daily_spearman']:.6f} |")
        rows.append("")
    rows.append("Next step: preregister one noise-robust training treatment only if attribution is interpretable; retain original model and cost/CAGR as subsequent hard gates.")
    (args.out / "SUMMARY.md").write_text("\n".join(rows) + "\n")
    print((args.out / "SUMMARY.md").read_text(), flush=True)


if __name__ == "__main__":
    main()
