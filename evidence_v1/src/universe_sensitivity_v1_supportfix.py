#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import universe_sensitivity_v1 as base


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def common_support(reference: pd.DataFrame, native: pd.DataFrame, subset: str):
    keys = ["signal_date", "ticker"]
    r = reference.copy()
    n = native.copy()
    r["signal_date"] = pd.to_datetime(r.signal_date)
    n["signal_date"] = pd.to_datetime(n.signal_date)
    r["ticker"] = r.ticker.astype(str)
    n["ticker"] = n.ticker.astype(str)

    rk = r[keys].drop_duplicates().sort_values(keys).reset_index(drop=True)
    nk = n[keys].drop_duplicates().sort_values(keys).reset_index(drop=True)
    if len(rk) != len(r) or len(nk) != len(n):
        raise RuntimeError(f"{subset}: duplicate panel keys")

    support = rk.merge(nk, on=keys, how="inner", validate="one_to_one")
    if support.empty:
        raise RuntimeError(f"{subset}: empty common support")

    r_index = pd.MultiIndex.from_frame(rk)
    n_index = pd.MultiIndex.from_frame(nk)
    s_index = pd.MultiIndex.from_frame(support)
    reference_only = r_index.difference(s_index)
    native_only = n_index.difference(s_index)

    r2 = r.merge(support, on=keys, how="inner", validate="one_to_one")
    n2 = n.merge(support, on=keys, how="inner", validate="one_to_one")
    r2 = r2.sort_values(keys).reset_index(drop=True)
    n2 = n2.sort_values(keys).reset_index(drop=True)

    diag = {
        "subset": subset,
        "reference_rows_before": int(len(r)),
        "native_rows_before": int(len(n)),
        "common_rows": int(len(support)),
        "reference_only_rows": int(len(reference_only)),
        "native_only_rows": int(len(native_only)),
        "reference_signal_dates_before": int(r.signal_date.nunique()),
        "native_signal_dates_before": int(n.signal_date.nunique()),
        "common_signal_dates": int(support.signal_date.nunique()),
        "reference_retention_on_common_support": float(len(support) / len(r)) if len(r) else float("nan"),
        "native_retention_on_common_support": float(len(support) / len(n)) if len(n) else float("nan"),
    }
    return r2, n2, support, diag


def fixed_on_support(checkpoint: pd.DataFrame, support: pd.DataFrame, subset: str) -> pd.DataFrame:
    keys = ["signal_date", "ticker"]
    cp = checkpoint.copy()
    cp["signal_date"] = pd.to_datetime(cp.signal_date)
    cp["ticker"] = cp.ticker.astype(str)
    s = support[keys].copy()
    s["signal_date"] = pd.to_datetime(s.signal_date)
    s["ticker"] = s.ticker.astype(str)
    x = s.merge(
        cp[keys + ["LTR_SCORE"]], on=keys, how="left", validate="one_to_one"
    )
    if x.LTR_SCORE.isna().any():
        miss = x.loc[x.LTR_SCORE.isna(), keys].head(10).to_dict("records")
        raise RuntimeError(f"{subset}: common-support keys missing from frozen LTR checkpoint: {miss}")
    x = x.sort_values(
        ["signal_date", "LTR_SCORE", "ticker"], ascending=[True, False, True]
    ).reset_index(drop=True)
    x["FIXED_RANK"] = x.groupby("signal_date").cumcount() + 1
    return x[keys + ["LTR_SCORE", "FIXED_RANK"]].rename(
        columns={"LTR_SCORE": "FIXED_SCORE"}
    )


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--full-panel", required=True)
    ap.add_argument("--checkpoint", required=True)
    ap.add_argument("--frozen-source", required=True)
    ap.add_argument("--u120", required=True)
    ap.add_argument("--u100", required=True)
    ap.add_argument("--u70", required=True)
    ap.add_argument("--native120", required=True)
    ap.add_argument("--native100", required=True)
    ap.add_argument("--native70", required=True)
    ap.add_argument("--out", required=True)
    args = ap.parse_args()

    frozen_source = Path(args.frozen_source).resolve()
    sys.path.insert(0, str(frozen_source / "src"))
    from etf_trader.ma3.producer import FEATURES_42

    features = list(FEATURES_42)
    full = pd.read_pickle(args.full_panel).copy()
    full["signal_date"] = pd.to_datetime(full.signal_date)
    checkpoint = pd.read_csv(Path(args.checkpoint) / "OOS_PREDICTIONS.csv")
    checkpoint["signal_date"] = pd.to_datetime(checkpoint.signal_date)

    universes = {
        "U120": (args.u120, args.native120),
        "U100": (args.u100, args.native100),
        "U70": (args.u70, args.native70),
    }
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)

    all_per_date = []
    all_feature_drift = []
    all_cluster = []
    all_audit = []
    full_summary: dict[str, dict] = {}
    split_summary: dict[str, dict] = {}
    coverage = {}

    for subset, (universe_path, native_path) in universes.items():
        u = pd.read_csv(universe_path)
        tickers = set(u.ticker.astype(str).str.upper())
        expected_n = int(subset[1:])
        if len(tickers) != expected_n:
            raise RuntimeError(f"{subset}: expected {expected_n} frozen tickers, got {len(tickers)}")
        if "SPY" not in tickers:
            raise RuntimeError(f"{subset}: SPY anchor missing")

        reference0 = full[full.ticker.astype(str).isin(tickers)].copy()
        native0 = pd.read_pickle(native_path).copy()
        native0["signal_date"] = pd.to_datetime(native0.signal_date)
        if set(native0.ticker.astype(str).unique()) - tickers:
            raise RuntimeError(f"{subset}: native panel contains non-candidate ticker")

        reference, native, support, support_diag = common_support(reference0, native0, subset)
        reference = base.recompute_candidate_targets(reference)
        native = base.recompute_candidate_targets(native)
        base.assert_same_keys_and_targets(reference, native, subset)

        coverage[subset] = {
            **support_diag,
            "tickers_seen_common": int(reference.ticker.nunique()),
            "evaluation_signal_dates_common": int(
                support.loc[
                    (support.signal_date >= base.EVAL_START)
                    & (support.signal_date < base.EVAL_END),
                    "signal_date",
                ].nunique()
            ),
        }

        ref_pred, ref_audit = base.fit_ltr(reference, features, "REF")
        native_pred, native_audit = base.fit_ltr(native, features, "NATIVE")
        ref_audit.insert(0, "subset", subset)
        native_audit.insert(0, "subset", subset)
        all_audit.extend([ref_audit, native_audit])

        fixed = fixed_on_support(checkpoint, support, subset)
        eval_base = reference[
            (reference.signal_date >= base.EVAL_START)
            & (reference.signal_date < base.EVAL_END)
        ][["signal_date", "ticker", "fwd_ret_21"]].copy()
        merged = eval_base.merge(fixed, on=["signal_date", "ticker"], how="inner", validate="one_to_one")
        merged = merged.merge(ref_pred, on=["signal_date", "ticker"], how="inner", validate="one_to_one")
        merged = merged.merge(native_pred, on=["signal_date", "ticker"], how="inner", validate="one_to_one")
        expected_eval_rows = len(eval_base.dropna(subset=["fwd_ret_21"]))
        actual_eval_rows = len(merged.dropna(subset=["fwd_ret_21"]))
        if actual_eval_rows != expected_eval_rows:
            raise RuntimeError(
                f"{subset}: evaluation merge lost rows {actual_eval_rows} != {expected_eval_rows}"
            )

        per_date = base.date_stability(merged, subset)
        if len(per_date) != 114:
            raise RuntimeError(f"{subset}: expected 114 evaluation periods, got {len(per_date)}")
        all_per_date.append(per_date)
        full_mask = pd.Series(True, index=per_date.index)
        old_mask = pd.to_datetime(per_date.signal_date) < pd.Timestamp("2023-01-01")
        new_mask = pd.to_datetime(per_date.signal_date) >= pd.Timestamp("2023-01-01")
        full_summary[subset] = base.summarize_period(per_date, full_mask)
        split_summary[subset] = {
            "2017_2022": base.summarize_period(per_date, old_mask),
            "2023_2026": base.summarize_period(per_date, new_mask),
        }
        all_feature_drift.append(base.feature_drift(reference, native, features, subset))
        all_cluster.append(base.cluster_stability(reference, native, subset))

    per_date_all = pd.concat(all_per_date, ignore_index=True)
    feature_all = pd.concat(all_feature_drift, ignore_index=True)
    cluster_all = pd.concat(all_cluster, ignore_index=True)
    audit_all = pd.concat(all_audit, ignore_index=True)

    decision = base.directional_decision(full_summary)
    cluster_summary = {
        subset: {
            "mean_adjusted_rand_index": float(g.adjusted_rand_index.mean()),
            "median_adjusted_rand_index": float(g.adjusted_rand_index.median()),
            "mean_cluster_change_1_minus_ari": float((1.0 - g.adjusted_rand_index).mean()),
        }
        for subset, g in cluster_all.groupby("subset", sort=True)
    }
    feature_summary = {
        subset: {
            "mean_of_feature_mean_abs_delta": float(g.mean_abs_delta.mean()),
            "max_feature_mean_abs_delta": float(g.mean_abs_delta.max()),
            "most_sensitive_feature": str(g.sort_values("mean_abs_delta", ascending=False).iloc[0].feature),
        }
        for subset, g in feature_all.groupby("subset", sort=True)
    }

    summary = {
        "line": "Evidence V1",
        "test": "universe_sensitivity_v1_supportfix",
        "status": "DIAGNOSTIC_COMPLETE",
        "invalidated_technical_run": 37053782730,
        "invalidated_run_produced_metrics": False,
        "universe": "Original149 frozen with preregistered nested U120/U100/U70 candidates",
        "holdout70_used": False,
        "support_rule": "A/B/C are aligned to identical common (signal_date,ticker) support before candidate-relative targets are recomputed",
        "anchor_A": "frozen full149 Retriever LTR v1 OOS scores restricted to common candidate/date support; no retraining",
        "method_B_reference": "same LTR v1 retrained on common-support candidate rows with FEATURES_42 computed in full149 reference universe; common-support candidate-relative targets",
        "method_C_native": "same LTR v1 retrained on native source-only features on identical common support; same common-support candidate-relative targets",
        "primary_stability_metrics": [
            "Top1 agreement to A",
            "Top5 turnover to A",
            "rank correlation to A",
            "normalized mean absolute rank displacement to A",
        ],
        "coverage": coverage,
        "full_2017_2026": full_summary,
        "temporal_splits": split_summary,
        "cluster_stability_reference_vs_native": cluster_summary,
        "feature_drift_reference_vs_native": feature_summary,
        "decision": decision,
        "interpretation_rule": (
            "Performance metrics are diagnostic only. This test asks whether stable-reference representation "
            "reduces ranking sensitivity to candidate-universe shrinkage; it is not a promotion test."
        ),
    }

    per_date_all.to_csv(out / "PER_DATE_STABILITY.csv", index=False)
    feature_all.to_csv(out / "FEATURE_DRIFT.csv", index=False)
    cluster_all.to_csv(out / "CLUSTER_STABILITY.csv", index=False)
    audit_all.to_csv(out / "FIT_AUDIT.csv", index=False)
    (out / "CONFIG.json").write_text(json.dumps({
        "ltr_config": base.LTR_CFG,
        "eval_start": str(base.EVAL_START.date()),
        "eval_end_exclusive": str(base.EVAL_END.date()),
        "subsets": [120, 100, 70],
        "common_support_alignment": True,
        "decision_rule": decision["rule"],
    }, indent=2) + "\n")
    (out / "SUMMARY.json").write_text(json.dumps(summary, indent=2) + "\n")

    files = [
        "PER_DATE_STABILITY.csv",
        "FEATURE_DRIFT.csv",
        "CLUSTER_STABILITY.csv",
        "FIT_AUDIT.csv",
        "CONFIG.json",
        "SUMMARY.json",
    ]
    manifest = {
        "test": "universe_sensitivity_v1_supportfix",
        "files_sha256": {f: sha256_file(out / f) for f in files},
    }
    (out / "RESULT_MANIFEST.json").write_text(json.dumps(manifest, indent=2) + "\n")
    print(json.dumps(summary, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
