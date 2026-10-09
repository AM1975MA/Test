"""One annual 2x2 Compact21 training-source attribution, research-only."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import sys
import tempfile

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / "vendor/etf_trader_v2/src")]

from etf_trader.source_only import kernel as k
from compact21_learner_swap_v1 import learners
from compact21_rolling_window_v1.run import frozen_reference
from compact21_predictive_v2.run import numerical_gate
from compact21_semidev_v1.run import FROZEN_TI, select_original_frames, original_controls
from compact21_semidev_v1.view import sha
from ranker_stability_v1.run_ranker_benchmark_full import load, quality, stability
from compact21_training_attribution_v1.mix import mixed_training, assert_common_training_keys

LINE = "COMPACT21_TRAINING_SOURCE_ATTRIBUTION_V1"
KEYS = ["signal_date", "ticker"]
PAIRS = ((1, 2), (1, 3), (2, 3))
TREATMENTS = {"OWN_X_R2_Y": ("own", "repeat2"),
              "R2_X_OWN_Y": ("repeat2", "own")}


def forensic_diff(a, b, features):
    """Counts all compared physical cells; does not turn percentages into i.i.d. tests."""
    left = a[features].to_numpy(dtype=float, copy=True)
    right = b[features].to_numpy(dtype=float, copy=True)
    fin = np.isfinite(left) & np.isfinite(right)
    changes = int((np.not_equal(left, right) & fin).sum())
    mask_changes = int((np.isfinite(left) != np.isfinite(right)).sum())
    ya = a.target_rank_21.to_numpy(dtype=float)
    yb = b.target_rank_21.to_numpy(dtype=float)
    ra = np.rint(np.clip(ya, 0, 1) * 100).astype(int)
    rb = np.rint(np.clip(yb, 0, 1) * 100).astype(int)
    return {"feature_finite_value_changed": changes,
            "feature_finite_common_cells": int(fin.sum()),
            "feature_finite_mask_changed": mask_changes,
            "feature_total_cells": int(left.size),
            "label_continuous_changed": int((ya != yb).sum()),
            "label_integer_changed": int((ra != rb).sum()),
            "label_rows": len(a)}


def identical_prediction(left, right):
    return (np.asarray(left).dtype == np.asarray(right).dtype
            and np.asarray(left).shape == np.asarray(right).shape
            and np.asarray(left).tobytes() == np.asarray(right).tobytes())


def common_output(common, pred, variant, vintage):
    z = common[KEYS].copy().reset_index(drop=True)
    z["pred"] = pred
    z["variant"] = variant
    z["vintage"] = vintage
    if len(z) != len(pred) or not np.isfinite(z.pred.to_numpy()).all():
        raise ValueError("Invalid common prediction")
    return z


def mature_quality(common, pred):
    mask = (common.target_rank_21.notna() & common.exit_date_21.notna()
            & common.exit_date_21.le(pd.Timestamp("2026-07-01")))
    if not mask.any():
        raise ValueError("No mature common Repeat2 outcomes")
    return quality(common.loc[mask], np.asarray(pred)[mask.to_numpy()])


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--year", type=int, required=True, choices=range(2017, 2027))
    for n in ("r1", "r2", "r3", "reference", "out"):
        parser.add_argument("--" + n, type=Path, required=True)
    a = parser.parse_args()
    if a.out.exists() and any(a.out.iterdir()):
        raise ValueError("Output must be a fresh directory")
    a.out.mkdir(parents=True, exist_ok=True)
    numerical = numerical_gate()
    paths = {v: getattr(a, "r" + str(v)) for v in (1, 2, 3)}
    hashes = {str(v): sha(paths[v] / "TI_COMPACT.parquet") for v in (1, 2, 3)}
    if hashes != FROZEN_TI:
        raise ValueError("Frozen three-vintage TI input mismatch")
    ref, source_hashes, ref_native, ref_common = frozen_reference(a.reference, hashes, numerical)
    frames = {v: load(paths[v]) for v in (1, 2, 3)}
    trains, tests, common = select_original_frames(frames, a.year)
    # Fail closed before fitting: this is a true 2x2 factorial only on identical rows.
    assert_common_training_keys(trains)
    features = list(k.F2D_FEATURES)
    if len(features) != 125:
        raise ValueError("Canonical 125 features changed")
    differences = {f"{v}-{w}": forensic_diff(trains[v], trains[w], features)
                   for v, w in PAIRS}
    input_hashes = {str(v): {
        "features": learners.array_hash(trains[v][features].to_numpy()),
        "continuous_target": learners.array_hash(trains[v].target_rank_21.to_numpy()),
        "exit_dates": learners.array_hash(trains[v].exit_date_21.astype("int64").to_numpy()),
    } for v in (1, 2, 3)}
    result = {
        "status": "RUNNING", "line": LINE, "year": a.year, "years": [a.year],
        "negative_feedback_changed": False, "production_adoption": False,
        "portfolio_evaluation": False, "deployable_treatment": False,
        "input_sha256": hashes, "fit_sources": source_hashes,
        "reference_baseline_sha256": sha(a.reference / "RESULT.json"),
        "preregistration_sha256": sha(ROOT / "compact21_training_attribution_v1/PREREGISTRATION.md"),
        "numeric_contract": numerical, "training_source_hashes": input_hashes,
        "forensic_differences": differences, "per_variant": {}, "controls": {},
        "input_contract": {
            "signal_cutoff": "2026-06-30", "outcome_exit_cutoff": "2026-07-01",
            "year": a.year, "train_keys_are_identical": True,
            "source_run": 37150436612, "reference_run": 37229180477,
        },
    }
    (a.out / "INPUT_CONTRACT.json").write_text(json.dumps(result, indent=2, allow_nan=False) + "\n")
    vectors = []
    with tempfile.TemporaryDirectory() as temp:
        scratch = Path(temp)
        controls, audits, control_native, control_common = original_controls(
            trains, tests, common, a.year, ref, ref_native, ref_common, scratch)
        result["controls"] = controls
        result["control_fit_audits"] = audits
        # Retained BASE alone supplies native/native cell; no implicit refitting.
        base = {v: control_common.loc[control_common.vintage.eq(v)].sort_values(KEYS).pred.to_numpy()
                for v in (1, 2, 3)}
        for v in (1, 2, 3):
            if len(base[v]) != len(common):
                raise ValueError("Original common BASE vintage coverage changed")
            vectors.append(common_output(common, base[v], "BASE_NATIVE", v))
        q = {str(v): mature_quality(common, base[v]) for v in (1, 2, 3)}
        result["per_variant"]["BASE_NATIVE"] = {
            "pair_metrics": {f"{v}-{w}": stability(common[KEYS], base[v], base[w])
                             for v, w in PAIRS},
            "quality_on_common_r2_outcomes": q, "fit_audits": audits,
            "control_prediction_exact": True,
        }
        for variant, (xs, ys) in TREATMENTS.items():
            preds = {}
            fit_audits = {}
            for v in (1, 2, 3):
                source = mixed_training(trains[v], trains[2], feature_cols=features,
                                        feature_source=xs, label_source=ys)
                learners.validate(source, [common], a.year)
                primary, audit, _, seconds = learners.fit(
                    source, [common], "BASE", a.year, scratch, f"{variant}_{a.year}_{v}")
                replay, again, _, _ = learners.fit(
                    source, [common], "BASE", a.year, scratch, f"{variant}_{a.year}_{v}_refit")
                if audit != again or not identical_prediction(primary[0], replay[0]):
                    raise ValueError("Independent treatment refit differs")
                if audit["train_groups_sha256"] != audits[str(v)]["train_groups_sha256"]:
                    raise ValueError("Train groups changed")
                if audit["test_matrix_sha256"][0] != audits[str(v)]["test_matrix_sha256"][0]:
                    raise ValueError("Common Repeat2 inference matrix changed")
                if v == 2 and not identical_prediction(primary[0], base[2]):
                    raise ValueError("Identity arm fails original Repeat2 BASE byte equality")
                preds[v] = primary[0]
                fit_audits[str(v)] = {
                    "fitted_inputs": audit, "independent_refit_exact": True,
                    "time_seconds": seconds,
                }
                vectors.append(common_output(common, preds[v], variant, v))
            result["per_variant"][variant] = {
                "pair_metrics": {f"{v}-{w}": stability(common[KEYS], preds[v], preds[w])
                                 for v, w in PAIRS},
                "quality_on_common_r2_outcomes":
                    {str(v): mature_quality(common, preds[v]) for v in (1, 2, 3)},
                "fit_audits": fit_audits, "independent_refits_exact": True,
                "repeat2_identity_exact": True,
            }
        for v in (1, 2, 3):
            vectors.append(common_output(common, base[2], "R2_X_R2_Y_NEGATIVE", v))
        result["per_variant"]["R2_X_R2_Y_NEGATIVE"] = {
            "pair_metrics": {f"{v}-{w}": stability(common[KEYS], base[2], base[2])
                             for v, w in PAIRS},
            "quality_on_common_r2_outcomes": {"2": mature_quality(common, base[2])},
            "exact_identity_control": True, "model_fit": False,
        }
    predictions = pd.concat(vectors, ignore_index=True)
    predictions.to_parquet(a.out / "PREDICTIONS.parquet", index=False)
    result["prediction_file_sha256"] = sha(a.out / "PREDICTIONS.parquet")
    result["source_files_sha256"] = {
        p.relative_to(ROOT).as_posix(): sha(p) for p in
        sorted((ROOT / "compact21_training_attribution_v1").glob("*.py"))}
    result["status"] = LINE + "_COMPLETE"
    (a.out / "RESULT.json").write_text(json.dumps(result, indent=2, allow_nan=False) + "\n")
    print(json.dumps({"year": a.year, "status": result["status"],
                      "attribution": {v: {pair: round(m["rank_mean_abs"], 6)
                      for pair, m in d["pair_metrics"].items()}
                      for v, d in result["per_variant"].items()}}, allow_nan=False), flush=True)


if __name__ == "__main__":
    main()
