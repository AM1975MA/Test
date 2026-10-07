"""Annual four-mask BASE XGB trial, after exact retained BASE control fits."""
from __future__ import annotations

import argparse
import importlib.metadata
import json
from pathlib import Path
import sys
import tempfile

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / "vendor/etf_trader_v2/src")]
from compact21_learner_swap_v1 import learners
from compact21_learner_swap_v1.run_benchmark import evaluation_coverage, score_gap, compare_native
from compact21_predictive_v2.run import numerical_gate, predictions_frame
from compact21_predictive_v2.summarize import normalized_numeric
from compact21_semidev_v1.run import (FROZEN_TI, select_original_frames, original_controls,
                                      source_gate, retained_slice)
from compact21_semidev_v1.view import sha
from ranker_stability_v1.run_ranker_benchmark_full import load, stability, quality
from compact21_feature_ablation_v1.variants import MASKS, mask_manifest

LINE = "COMPACT21_FEATURE_ABLATION_V1"
KEYS = ["signal_date", "ticker"]
PAIRS = ((1, 2), (1, 3), (2, 3))


def masked(frame, columns):
    # Original frame selection and >=30 finite-feature eligibility precede this call.
    z = frame.copy(deep=True)
    z.loc[:, list(columns)] = np.nan
    pd.testing.assert_frame_equal(z.drop(columns=list(columns)), frame.drop(columns=list(columns)), check_exact=True)
    if not z[list(columns)].isna().all().all():
        raise ValueError("Masked feature still contains finite data")
    return z


def frozen_reference(path, hashes, numeric):
    r = json.loads((path / "RESULT.json").read_text())
    if r.get("status") != "COMPACT21_PREDICTIVE_V2_COMPLETE" or r.get("variant") != "BASE" or r.get("input_sha256") != hashes:
        raise ValueError("Wrong retained BASE reference")
    if normalized_numeric(r["numeric_contract"]) != normalized_numeric(numeric):
        raise ValueError("Numeric profile changed")
    canonical_sources = source_gate(r)
    for name in ("NATIVE_PREDICTIONS.parquet", "COMMON_PREDICTIONS.parquet"):
        if r["files_sha256"][name] != sha(path / name):
            raise ValueError("Retained BASE vectors changed")
    return r, canonical_sources, pd.read_parquet(path / "NATIVE_PREDICTIONS.parquet"), pd.read_parquet(path / "COMMON_PREDICTIONS.parquet")


def run_variant(name, columns, manifest, args, base, canonical_sources, hashes, numeric,
                trains, tests, common, controls, control_audits, cn, cc, scratch):
    out = args.out / name
    out.mkdir(parents=True, exist_ok=False)
    source_files = list((ROOT / "compact21_feature_ablation_v1").glob("*.py"))
    sources = {p.relative_to(ROOT).as_posix(): sha(p) for p in source_files}
    sources.update(canonical_sources)
    expected_coverage = evaluation_coverage(trains, tests, common)
    ctrains = {i: masked(trains[i], columns) for i in (1, 2, 3)}
    ctests = {i: masked(tests[i], columns) for i in (1, 2, 3)}
    ccommon = masked(common, columns)
    coverage = evaluation_coverage(ctrains, ctests, ccommon)
    if coverage != expected_coverage:
        raise ValueError("Cohort or label changed under mask")
    for i in (1, 2, 3):
        learners.validate(ctrains[i], [ccommon, ctests[i]], args.year)
        pd.testing.assert_frame_equal(ctrains[i][["signal_date", "ticker", "target_rank_21", "exit_date_21"]],
                                      trains[i][["signal_date", "ticker", "target_rank_21", "exit_date_21"]], check_exact=True)
    result = {"status": "RUNNING", "line": LINE, "variant": name, "years": [args.year],
              "input_sha256": hashes, "per_year": {}, "numeric_contract": numeric,
              "environment": {n: importlib.metadata.version(n) for n in
                              ("numpy", "pandas", "scikit-learn", "xgboost", "lightgbm", "scipy", "pyarrow")},
              "python": sys.version, "sources": sources, "fit_sources": canonical_sources,
              "baseline_input_contract": base["input_contract"],
              "preregistration_sha256": sha(ROOT / "compact21_feature_ablation_v1/PREREGISTRATION.md"),
              "mask_manifest_sha256": sha(args.out / "MASK_MANIFEST.json"),
              "mask_feature_names": list(columns), "mask_feature_names_sha256": manifest[name]["masked_columns_sha256"],
              "input_contract": {"line": LINE, "original_ti_sha256": hashes,
                                 "signal_cutoff": "2026-06-30", "quality_exit_cutoff": "2026-07-01",
                                 "common_inference_repeat": 2, "train_cohorts": "original_native_frozen_before_mask",
                                 "changed_columns": list(columns),
                                 "ref_base_result_sha256": sha(args.reference / "RESULT.json"),
                                 "reference_prediction_sha256": base["files_sha256"]},
              "negative_feedback_changed": False, "portfolio_evaluation": False, "production_adoption": False}
    (out / "INPUT_CONTRACT.json").write_text(json.dumps(result, indent=2, allow_nan=False) + "\n")
    cn.to_parquet(out / "CONTROL_NATIVE_PREDICTIONS.parquet", index=False)
    cc.to_parquet(out / "CONTROL_COMMON_PREDICTIONS.parquet", index=False)
    (out / "CONTROL_GATE.json").write_text(json.dumps({"PASS": True, "controls": controls}, indent=2) + "\n")
    pcs, pns, audits, times, refits = {}, {}, {}, {}, {}
    native, common_frames = [], []
    for i in (1, 2, 3):
        tag = f"ablation_{name}_{args.year}_{i}"
        p, audit, _, elapsed = learners.fit(ctrains[i], [ccommon, ctests[i]], "BASE", args.year, scratch, tag)
        again, second_audit, _, _ = learners.fit(ctrains[i], [ccommon, ctests[i]], "BASE", args.year, scratch, tag + "_refit")
        if audit != second_audit or any(x.dtype != y.dtype or x.tobytes() != y.tobytes() for x, y in zip(p, again)):
            raise ValueError("Independent candidate refit differs")
        if audit["train_labels_sha256"] != control_audits[str(i)]["train_labels_sha256"] or audit["train_groups_sha256"] != control_audits[str(i)]["train_groups_sha256"]:
            raise ValueError("Candidate labels or groups changed")
        pcs[i], pns[i] = p
        audits[str(i)], times[str(i)] = audit, elapsed
        refits[str(i)] = {"common_bytes_exact": True, "native_bytes_exact": True,
                         "learned_audit_exact": True, "refit_audit": second_audit,
                         "prediction_sha256": second_audit["prediction_sha256"]}
        native.append(predictions_frame(tests[i], p[1], i))
        common_frames.append(common[KEYS].assign(pred=p[0], vintage=i))
    qualities = {}
    for i in (1, 2, 3):
        mature = (tests[i].target_rank_21.notna() & tests[i].exit_date_21.notna() &
                  tests[i].exit_date_21.le(pd.Timestamp("2026-07-01"))).to_numpy()
        if not mature.any():
            raise ValueError("Empty annual mature quality cohort")
        qualities[str(i)] = quality(tests[i].loc[mature], pns[i][mature])
    result["per_year"][str(args.year)] = {
        "quality": qualities, "evaluation_coverage": coverage,
        "common_inference": {f"{i}-{j}": stability(common[KEYS], pcs[i], pcs[j]) for i, j in PAIRS},
        "native_inference": compare_native(tests, pns),
        "common_score_gap": {f"{i}-{j}": score_gap(common[KEYS], pcs[i], pcs[j]) for i, j in PAIRS},
        "transforms": audits, "fit_seconds": times, "determinism_PASS": True,
        "legacy_control": controls, "control_transforms": control_audits,
        "independent_refits": refits}
    pd.concat(native, ignore_index=True).to_parquet(out / "NATIVE_PREDICTIONS.parquet", index=False)
    pd.concat(common_frames, ignore_index=True).to_parquet(out / "COMMON_PREDICTIONS.parquet", index=False)
    result.update(ALL_DETERMINISM_PASS=True, LEGACY_PARITY_PASS=True)
    result["files_sha256"] = {p.name: sha(p) for p in out.glob("*.parquet")}
    result["status"] = LINE + "_COMPLETE"
    (out / "RESULT.json").write_text(json.dumps(result, indent=2, allow_nan=False) + "\n")
    print(json.dumps({"year": args.year, "variant": name, "status": result["status"]}), flush=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--year", type=int, required=True, choices=range(2017, 2027))
    for n in ("r1", "r2", "r3", "reference", "out"):
        parser.add_argument("--" + n, type=Path, required=True)
    args = parser.parse_args()
    if args.out.exists() and any(args.out.iterdir()):
        raise ValueError("Output must be fresh")
    args.out.mkdir(parents=True, exist_ok=True)
    numeric = numerical_gate()
    paths = {i: getattr(args, f"r{i}") for i in (1, 2, 3)}
    hashes = {str(i): sha(path / "TI_COMPACT.parquet") for i, path in paths.items()}
    if hashes != FROZEN_TI:
        raise ValueError("Wrong frozen TI inputs")
    manifest = mask_manifest()
    (args.out / "MASK_MANIFEST.json").write_text(json.dumps(manifest, indent=2) + "\n")
    base, canonical_sources, bn, bc = frozen_reference(args.reference, hashes, numeric)
    frames = {i: load(path) for i, path in paths.items()}
    trains, tests, common = select_original_frames(frames, args.year)
    with tempfile.TemporaryDirectory() as td:
        scratch = Path(td)
        controls, audits, cn, cc = original_controls(trains, tests, common, args.year, base, bn, bc, scratch)
        # All original BASE controls pass before the first candidate fit.
        for name, columns in MASKS.items():
            run_variant(name, columns, manifest, args, base, canonical_sources, hashes, numeric,
                        trains, tests, common, controls, audits, cn, cc, scratch)


if __name__ == "__main__":
    main()
