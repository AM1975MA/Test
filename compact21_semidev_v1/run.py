"""One annual BASE_SEMIDEV cloud job; strict old-BASE parity precedes candidate fits."""
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
from etf_trader.source_only import kernel as k
from compact21_learner_swap_v1 import learners
from compact21_learner_swap_v1.run_benchmark import evaluation_coverage, score_gap, compare_native
from compact21_predictive_v2.run import numerical_gate, predictions_frame
from compact21_predictive_v2.summarize import normalized_numeric
from ranker_stability_v1.run_ranker_benchmark_full import load, train_frame, align, stability, quality
from compact21_semidev_v1.view import CHANGED, sha, transfer_rows, from_frozen_raw

LINE = "COMPACT21_SEMIDEV_V1"
VARIANT = "BASE_SEMIDEV"
KEYS = ["signal_date", "ticker"]
PAIRS = ((1, 2), (1, 3), (2, 3))
FROZEN_TI = {"1": "f4767915385ebe49ec8737f24ee3a0296e39cfe70801afee952918445db1f05e",
             "2": "19d08dc2fd8d389755b6be174639240657bccfc48569e6d080ed14074a162db5",
             "3": "0b9c79ad5622d1295dfce01dc0271b6d771329369abae80833f66775a822a4ba"}


def select_original_frames(frames, year):
    trains = {i: train_frame(frames[i], year) for i in (1, 2, 3)}
    tests = {}
    for i in (1, 2, 3):
        f = frames[i]
        valid = f[k.F2D_FEATURES].notna().sum(axis=1) >= 30
        tests[i] = f[(f.signal_date.dt.year == year) & (f.signal_date <= "2026-06-30") & valid].sort_values(KEYS).reset_index(drop=True)
        if tests[i].empty or trains[i].empty or tests[i].duplicated(KEYS).any() or trains[i].duplicated(KEYS).any():
            raise ValueError("Invalid original cohorts")
    common = align([tests[i] for i in (1, 2, 3)])[1]
    if common.empty:
        raise ValueError("Empty original common inference")
    return trains, tests, common


def retained_slice(frame, year, repeat):
    if "vintage" not in frame or "pred" not in frame or frame[KEYS].isna().any().any():
        raise ValueError("Invalid retained reference predictions")
    z = frame[(pd.to_datetime(frame.signal_date).dt.year == year) & (frame.vintage == repeat)].sort_values(KEYS).reset_index(drop=True)
    if z.empty or z.duplicated(KEYS).any() or not np.isfinite(z.pred.to_numpy()).all():
        raise ValueError("Missing/invalid retained annual reference")
    return z


def compare_retained(original, prediction, retained, native):
    fresh = predictions_frame(original, prediction, int(retained.vintage.iloc[0])) if native else original[KEYS].assign(pred=prediction, vintage=int(retained.vintage.iloc[0]))
    fresh = fresh.sort_values(KEYS).reset_index(drop=True)
    if list(fresh.columns) != list(retained.columns):
        raise ValueError("Reference prediction evidence columns differ")
    pd.testing.assert_frame_equal(fresh.drop(columns="pred"), retained.drop(columns="pred"), check_exact=True)
    if fresh.pred.to_numpy().dtype != retained.pred.to_numpy().dtype or fresh.pred.to_numpy().tobytes() != retained.pred.to_numpy().tobytes():
        raise ValueError("Original BASE predictions differ from retained V2 bytes")
    return fresh


def original_controls(trains, tests, common, year, ref, native_reference, common_reference, scratch):
    """Fail closed before any candidate fit. Fits original BASE only."""
    audits = {}; controls = {}; native = []; common_frames = []
    expected = ref["per_year"][str(year)]
    for i in (1, 2, 3):
        predictions, audit, _, seconds = learners.fit(trains[i], [common, tests[i]], "BASE", year, scratch, f"control_{year}_{i}")
        native_frame = compare_retained(tests[i], predictions[1], retained_slice(native_reference, year, i), True)
        common_frame = compare_retained(common, predictions[0], retained_slice(common_reference, year, i), False)
        old = expected["transforms"][str(i)]
        fields = ("train_matrix_sha256", "train_labels_sha256", "train_groups_sha256", "test_matrix_sha256", "prediction_sha256")
        hashes_equal = all(audit[field] == old[field] for field in fields)
        if not hashes_equal:
            raise ValueError("Original BASE matrix/label/prediction hashes differ")
        if audit != old:
            raise ValueError("Original BASE complete learned audit differs")
        audits[str(i)] = audit
        controls[str(i)] = {"native_bytes_exact": True, "common_bytes_exact": True,
                             "metadata_exact": True, "legacy_hashes_exact": True, "fit_seconds": seconds}
        native.append(native_frame); common_frames.append(common_frame)
    if evaluation_coverage(trains, tests, common) != expected["evaluation_coverage"]:
        raise ValueError("Original coverage differs from retained BASE")
    return controls, audits, pd.concat(native, ignore_index=True), pd.concat(common_frames, ignore_index=True)


def source_gate(reference):
    required = ("compact21_learner_swap_v1/learners.py", "ranker_stability_v1/run_ranker_benchmark_full.py",
                "vendor/etf_trader_v2/src/etf_trader/source_only/kernel.py",
                "vendor/etf_trader_v2/src/etf_trader/source_only/_xgb_worker.py",
                "vendor/etf_trader_v2/src/etf_trader/source_only/raw_io.py",
                "compact21_predictive_v2/run.py")
    for name in required:
        if reference.get("sources", {}).get(name) != sha(ROOT/name):
            raise ValueError(f"Frozen BASE source changed {name}")
    return {name: sha(ROOT/name) for name in required}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--year", type=int, required=True, choices=range(2017, 2027))
    for i in (1, 2, 3):
        parser.add_argument(f"--r{i}", type=Path, required=True)
    parser.add_argument("--raw-root", type=Path, required=True)
    parser.add_argument("--contracts-root", type=Path, required=True)
    parser.add_argument("--reference", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    a = parser.parse_args()
    numeric = numerical_gate()
    if a.out.exists() and any(a.out.iterdir()):
        raise ValueError("Output directory must be fresh")
    a.out.mkdir(parents=True, exist_ok=True)
    paths = {i: getattr(a, f"r{i}") for i in (1, 2, 3)}
    hashes = {str(i): sha(paths[i]/"TI_COMPACT.parquet") for i in paths}
    if hashes != FROZEN_TI:
        raise ValueError("Frozen TI file identity differs")
    reference_path = a.reference/"RESULT.json"
    reference = json.loads(reference_path.read_text())
    if reference.get("status") != "COMPACT21_PREDICTIVE_V2_COMPLETE" or reference.get("variant") != "BASE" or reference.get("input_sha256") != hashes:
        raise ValueError("Wrong retained BASE V2 reference")
    if normalized_numeric(numeric) != normalized_numeric(reference["numeric_contract"]):
        raise ValueError("Actual numeric environment differs from retained BASE V2")
    canonical_sources = source_gate(reference)
    for name in ("NATIVE_PREDICTIONS.parquet", "COMMON_PREDICTIONS.parquet"):
        if reference.get("files_sha256", {}).get(name) != sha(a.reference/name):
            raise ValueError("Retained BASE reference file hash mismatch")
    native_reference = pd.read_parquet(a.reference/"NATIVE_PREDICTIONS.parquet")
    common_reference = pd.read_parquet(a.reference/"COMMON_PREDICTIONS.parquet")
    frames = {i: load(paths[i]) for i in paths}
    trains, tests, common = select_original_frames(frames, a.year)
    views = {}; view_audits = {}
    for i in (1, 2, 3):
        views[i], view_audits[str(i)] = from_frozen_raw(frames[i], a.raw_root/f"_repeat{i}", a.contracts_root/f"r{i}"/"INPUT_CONTRACT.json")
        view_audits[str(i)]["donor_repeat"] = i
    candidate_trains = {i: transfer_rows(trains[i], views[i]) for i in trains}
    candidate_tests = {i: transfer_rows(tests[i], views[i]) for i in tests}
    candidate_common = transfer_rows(common, views[2])
    coverage = evaluation_coverage(candidate_trains, candidate_tests, candidate_common)
    if coverage != evaluation_coverage(trains, tests, common):
        raise ValueError("Candidate changed original cohorts/labels")
    for i in (1, 2, 3):
        learners.validate(candidate_trains[i], [candidate_common, candidate_tests[i]], a.year)
        view_audits[str(i)].update(baseline_cohorts_exact=True, maturity_PASS=True, common_donor_repeat=2)
    sources = {p.relative_to(ROOT).as_posix(): sha(p) for p in sorted((ROOT/"compact21_semidev_v1").glob("*.py"))}
    sources.update(canonical_sources)
    result = {"status": "RUNNING", "line": LINE, "variant": VARIANT, "years": [a.year],
              "input_sha256": hashes, "per_year": {}, "numeric_contract": numeric,
              "environment": {n: importlib.metadata.version(n) for n in ("numpy", "pandas", "scikit-learn", "xgboost", "lightgbm", "scipy", "pyarrow")},
              "python": sys.version, "sources": sources, "fit_sources": canonical_sources,
              "baseline_input_contract": reference["input_contract"],
              "preregistration_sha256": sha(ROOT/"compact21_semidev_v1/PREREGISTRATION.md"),
              "build_protocol_sha256": sha(ROOT/"compact21_semidev_v1/BUILD_PROTOCOL.md"),
              "input_contract": {"line": LINE, "original_ti_sha256": hashes,
                  "signal_cutoff": "2026-06-30", "quality_exit_cutoff": "2026-07-01", "common_inference_repeat": 2,
                  "train_cohorts": "original_native_frozen_before_view", "changed_columns": CHANGED,
                  "ref_base_result_sha256": sha(reference_path), "reference_prediction_sha256": reference["files_sha256"],
                  "raw_contract_sha256": {str(i): sha(a.contracts_root/f"r{i}"/"INPUT_CONTRACT.json") for i in (1, 2, 3)}},
              "negative_feedback_changed": False, "portfolio_evaluation": False, "production_adoption": False}
    (a.out/"INPUT_CONTRACT.json").write_text(json.dumps(result, indent=2, allow_nan=False)+"\n")
    pcs = {}; pns = {}; audits = {}; times = {}; refits = {}; native = []; common_frames = []
    with tempfile.TemporaryDirectory() as td:
        controls, control_audits, cn, cc = original_controls(trains, tests, common, a.year, reference, native_reference, common_reference, Path(td))
        cn.to_parquet(a.out/"CONTROL_NATIVE_PREDICTIONS.parquet", index=False)
        cc.to_parquet(a.out/"CONTROL_COMMON_PREDICTIONS.parquet", index=False)
        (a.out/"CONTROL_GATE.json").write_text(json.dumps({"PASS": True, "controls": controls}, indent=2)+"\n")
        # No candidate fit exists above this point: all three original controls must pass.
        for i in (1, 2, 3):
            p, audit, _, elapsed = learners.fit(candidate_trains[i], [candidate_common, candidate_tests[i]], "BASE", a.year, Path(td), f"semidev_{a.year}_{i}")
            again, again_audit, _, _ = learners.fit(candidate_trains[i], [candidate_common, candidate_tests[i]], "BASE", a.year, Path(td), f"semidev_{a.year}_{i}_refit")
            common_exact = p[0].dtype == again[0].dtype and p[0].tobytes() == again[0].tobytes()
            native_exact = p[1].dtype == again[1].dtype and p[1].tobytes() == again[1].tobytes()
            if not common_exact or not native_exact or audit != again_audit:
                raise ValueError("Candidate independent annual/vintage refit differs")
            pcs[i], pns[i] = p; audits[str(i)] = audit; times[str(i)] = elapsed
            refits[str(i)] = {"common_bytes_exact": common_exact, "native_bytes_exact": native_exact, "learned_audit_exact": True,
                              "refit_audit": again_audit, "prediction_sha256": again_audit["prediction_sha256"]}
            native.append(predictions_frame(tests[i], pns[i], i))
            common_frames.append(common[KEYS].assign(pred=pcs[i], vintage=i))
    qualities = {}
    for i in (1, 2, 3):
        mask = (tests[i].target_rank_21.notna() & tests[i].exit_date_21.notna()
                & tests[i].exit_date_21.le(pd.Timestamp("2026-07-01"))).to_numpy()
        if not mask.any():
            raise ValueError("Empty mature annual quality")
        qualities[str(i)] = quality(tests[i].loc[mask], pns[i][mask])
    result["per_year"][str(a.year)] = {"quality": qualities, "evaluation_coverage": coverage,
        "common_inference": {f"{i}-{j}": stability(common[KEYS], pcs[i], pcs[j]) for i, j in PAIRS},
        "native_inference": compare_native(tests, pns),
        "common_score_gap": {f"{i}-{j}": score_gap(common[KEYS], pcs[i], pcs[j]) for i, j in PAIRS},
        "transforms": audits, "fit_seconds": times, "determinism_PASS": True,
        "legacy_control": controls, "control_transforms": control_audits,
        "independent_refits": refits, "view_audit": view_audits}
    pd.concat(native, ignore_index=True).to_parquet(a.out/"NATIVE_PREDICTIONS.parquet", index=False)
    pd.concat(common_frames, ignore_index=True).to_parquet(a.out/"COMMON_PREDICTIONS.parquet", index=False)
    result["ALL_DETERMINISM_PASS"] = True; result["LEGACY_PARITY_PASS"] = True
    result["files_sha256"] = {p.name: sha(p) for p in a.out.glob("*.parquet")}
    result["status"] = LINE+"_COMPLETE"
    (a.out/"RESULT.json").write_text(json.dumps(result, indent=2, allow_nan=False)+"\n")
    print(json.dumps({"year": a.year, "variant": VARIANT, "status": result["status"], "legacy_parity": True}), flush=True)


if __name__ == "__main__":
    main()
