#!/usr/bin/env python3
"""Research-local Compact21 intervention followed by the canonical full replay.

No canonical source is edited.  Compact63 uses precisely the original matrices,
labels, seeds, worker and prediction reduction; only Compact21 is transformed.
Ridge and LambdaRank replace only Compact21; all other model paths remain canonical.
"""
from __future__ import annotations

import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import shutil
import sys
import tempfile

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
REPO = HERE.parent
SRC = REPO / "vendor" / "etf_trader_v2" / "src"
sys.path.insert(0, str(SRC))
sys.path.insert(0, str(REPO))

VARIANTS = ("BASE", "RIDGE", "LGBM_LAMBDARANK")


def file_hash(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def array_hash(array: np.ndarray) -> str:
    array = np.ascontiguousarray(array)
    h = hashlib.sha256()
    h.update(str(array.shape).encode())
    h.update(array.dtype.str.encode())
    h.update(array.tobytes())
    return h.hexdigest()


def load_compare(path: Path):
    spec = importlib.util.spec_from_file_location("compact21_full_compare", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


ENVIRONMENT_GATE_KEYS = ("python", "machine", "numpy", "pandas", "scipy", "sklearn", "execution_env", "numpy_build_config")


def persist_input_environment_evidence(out, contract, reference_contract):
    """Keep blocking environment differences reviewable even when replay stops."""
    actual, expected = contract["environment"], reference_contract.get("environment", {})
    mismatches = [key for key in ENVIRONMENT_GATE_KEYS if actual.get(key) != expected.get(key)]
    comparison = {"passed": not mismatches, "required_keys": list(ENVIRONMENT_GATE_KEYS),
                  "mismatched_keys": mismatches,
                  "expected": {key: expected.get(key) for key in ENVIRONMENT_GATE_KEYS},
                  "actual": {key: actual.get(key) for key in ENVIRONMENT_GATE_KEYS},
                  "gate": "exact_environment_metadata; no tolerance"}
    (Path(out) / "INPUT_CONTRACT.json").write_text(json.dumps(contract, indent=2) + "\n")
    (Path(out) / "ENVIRONMENT_COMPARISON.json").write_text(json.dumps(comparison, indent=2) + "\n")
    return comparison


def make_compact_hook(variant: str, model_module):
    """Mirror canonical worker scheduling exactly, altering only horizon 21."""
    if variant not in VARIANTS:
        raise ValueError(variant)

    def hook(k, frame, te, valid, cutoff, out, year):
        params = dict(k.COMPACT_PARAMS)
        rounds = int(params.pop("n_estimators"))
        params.pop("n_jobs", None)
        worker_threads = max(1, int(os.environ.get("ETF_TRADER_XGB_THREADS_PER_WORKER", "1")))
        worker_count = max(1, int(os.environ.get("ETF_TRADER_XGB_WORKERS", "3")))
        worker = Path(model_module.__file__).with_name("_xgb_worker.py")
        params_json = json.dumps(params, separators=(",", ":"), sort_keys=True)
        scratch_root = Path(out) / ".xgb_scratch"
        scratch_root.mkdir(parents=True, exist_ok=True)
        td = Path(tempfile.mkdtemp(prefix=f"{year}_", dir=scratch_root))
        tasks, training, audit, predictions = [], {}, {}, {}
        learned = Path(out) / f"learner_evidence_{year}"
        learned.mkdir(parents=True, exist_ok=True)
        canonical_test = te[k.F2D_FEATURES].replace([np.inf, -np.inf], np.nan).to_numpy()
        try:
            for horizon in (21, 63):
                train = frame[(frame.signal_date < cutoff)
                              & (frame[f"exit_date_{horizon}"] < cutoff)
                              & frame[f"target_rank_{horizon}"].notna()
                              & valid].sort_values(["signal_date", "ticker"])
                maturity_ok = bool((train.signal_date < cutoff).all()
                                   and (train[f"exit_date_{horizon}"] < cutoff).all())
                if not maturity_ok:
                    raise RuntimeError(f"look-ahead: immature compact{horizon} label in fit year {year}")
                xtr = train[k.F2D_FEATURES].replace([np.inf, -np.inf], np.nan).to_numpy()
                xte = canonical_test
                y = (train[f"target_rank_{horizon}"] * 100).round().astype(int).to_numpy()
                transform = {"feature_transform": "identity", "target_transform": "legacy_round_rank_x100"}
                groups = train.groupby("signal_date", sort=True).size().to_numpy()
                data = td / f"data_{horizon}.npz"
                np.savez(data, Xtr=xtr, Xte=xte, y=y, groups=groups)
                training[horizon] = train
                audit[str(horizon)] = {
                    "maturity_ok": maturity_ok,
                    "train_rows": len(train), "max_signal": str(train.signal_date.max()),
                    "max_exit": str(train[f"exit_date_{horizon}"].max()), "fit_cutoff": str(cutoff),
                    "Xtr_sha256": array_hash(xtr), "Xte_sha256": array_hash(xte),
                    "y_sha256": array_hash(y), "groups_sha256": array_hash(groups),
                    "transform": transform,
                    "canonical63_input_contract": horizon == 63,
                }
                if horizon == 21 and variant != "BASE":
                    from compact21_learner_swap_v1 import learners
                    learner_predictions, learner_meta, learner_y, fit_seconds = learners.fit(
                        train, [te], variant, year, learned, f"full_{year}")
                    predictions[21] = np.asarray(learner_predictions[0])
                    if predictions[21].shape != (len(te),) or not np.isfinite(predictions[21]).all():
                        raise RuntimeError("Compact21 learner prediction shape/nonfinite failure")
                    audit["21"].update(y_sha256=array_hash(np.asarray(learner_y)),
                                       learner=learner_meta, fit_seconds=float(fit_seconds),
                                       transform={"learner": variant, "metadata": learner_meta},
                                       mean_predictions_sha256=array_hash(predictions[21]))
                    np.save(learned / "compact21_prediction.npy", predictions[21])
                    continue
                for seed in k.COMPACT_SEEDS:
                    pred = td / f"pred_{horizon}_{int(seed)}.npy"
                    cmd = [sys.executable, str(worker), "--data", str(data),
                           "--seed", str(int(seed)), "--threads", str(worker_threads),
                           "--rounds", str(rounds), "--params-json", params_json, "--output", str(pred)]
                    tasks.append((horizon, int(seed), pred, cmd))
            max_workers = min(worker_count, len(k.COMPACT_SEEDS), max(1, os.cpu_count() or 1))
            for horizon in (21, 63):
                batch = [task for task in tasks if task[0] == horizon]
                with ThreadPoolExecutor(max_workers=max_workers) as executor:
                    futures = [executor.submit(model_module._run_xgb_worker, cmd) for _, _, _, cmd in batch]
                    for future in as_completed(futures):
                        future.result()
            for horizon in (21, 63):
                if horizon == 21 and variant != "BASE":
                    continue
                seed_predictions = [np.load(td / f"pred_{horizon}_{int(seed)}.npy") for seed in k.COMPACT_SEEDS]
                predictions[horizon] = np.mean(seed_predictions, axis=0)
                if predictions[horizon].shape != (len(te),) or not np.isfinite(predictions[horizon]).all():
                    raise RuntimeError(f"Canonical Compact{horizon} prediction shape/nonfinite failure")
                audit[str(horizon)]["seed_predictions_sha256"] = [array_hash(p) for p in seed_predictions]
                audit[str(horizon)]["mean_predictions_sha256"] = array_hash(predictions[horizon])
                np.save(learned / f"compact{horizon}_prediction.npy", predictions[horizon])
                for seed, seed_prediction in zip(k.COMPACT_SEEDS, seed_predictions):
                    np.save(learned / f"compact{horizon}_seed_{seed}.npy", seed_prediction)
            metadata = {"year": int(year), "variant": variant, "horizons": audit,
                        "seeds": [int(seed) for seed in k.COMPACT_SEEDS], "rounds": rounds,
                        "canonical_worker_sha256": file_hash(worker), "params": params,
                        "negative_feedback_changed": False}
            metadata["learner_artifacts_sha256"] = {str(path.relative_to(learned)): file_hash(path)
                                                        for path in sorted(learned.rglob("*")) if path.is_file()}
            (Path(out) / f"stability_transform_{year}.json").write_text(json.dumps(metadata, indent=2) + "\n")
            return predictions, training, {"mode": "isolated_parallel_workers" if variant == "BASE"
                                            else "canonical63_isolated_plus_compact21_swap",
                                           "compact21_learner": variant, "workers": max_workers,
                                           "threads_per_worker": worker_threads}
        finally:
            shutil.rmtree(td, ignore_errors=True)
    return hook


def build_titanium(titanium_raw: Path, out: Path, variant: str):
    from etf_trader.source_only import kernel as k, models
    from etf_trader.source_only.features import build as build_extra_features
    from etf_trader.source_only.raw_io import load_ticker_csv_folder
    out.mkdir(parents=True, exist_ok=True)
    mats, categories, _ = load_ticker_csv_folder(titanium_raw)
    columns = list(mats["Close"].columns)
    k.ALL_TICKERS = sorted(columns)
    k.TICKER_CATEGORY = categories
    k.CATEGORY_TICKERS = {category: sorted(t for t in columns if categories[t] == category)
                          for category in sorted(set(categories.values()))}
    dates = k.month_end_dates(mats["Close"].index)
    if len(dates) and dates[-1] == mats["Close"].index[-1]:
        dates = dates[:-1]
    _, compact, tail, _ = k.build_features(mats)
    compact = k.add_labels(compact[compact.signal_date.isin(dates)].copy(), mats["Open"], dates)
    tail = k.add_labels(tail[tail.signal_date.isin(dates)].copy(), mats["Open"], dates)
    tail_without_labels = tail.drop(columns=[column for column in tail
                                            if column.startswith(("fwd_", "target_", "exit_"))
                                            or column in ("entry_date", "y_tailmix")])
    macro, macro_features = k.build_macro_panel(tail_without_labels, tail)
    extra = build_extra_features(mats, categories, dates)
    canonical_hook = models._fit_compact_rankers_isolated
    models._fit_compact_rankers_isolated = make_compact_hook(variant, models)
    try:
        predictions = models.fit_predict(k, compact, tail, macro, macro_features, extra, out / "annual_models")
    finally:
        models._fit_compact_rankers_isolated = canonical_hook
    predictions = predictions[(predictions.signal_date >= "2017-01-31")
                              & (predictions.signal_date <= "2026-06-30")].copy()
    predictions.to_csv(out / "ANNUAL_PREDICTIONS.csv", index=False)
    baseline = models.variants(predictions)["baseline"].rename(columns={"score": "TIT_R"})
    calendar = predictions[["signal_date", "ticker", "entry_date", "exit_date"]].drop_duplicates(["signal_date", "ticker"])
    panel = baseline.merge(calendar, on=["signal_date", "ticker"], how="inner", validate="one_to_one")
    panel = panel[["signal_date", "entry_date", "exit_date", "ticker", "TIT_R"]].sort_values(["signal_date", "ticker"])
    path = out / "TIT_R_SOURCE_ONLY.csv"
    panel.to_csv(path, index=False)
    return panel, path


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--raw", required=True, help="Frozen raw folder containing universe.csv and ticker CSVs")
    parser.add_argument("--compare-script", default=str(REPO / "holdout70" / "v2_canonical_same_source_compare.py"))
    parser.add_argument("--out", required=True)
    parser.add_argument("--variant", choices=VARIANTS, required=True)
    parser.add_argument("--universe-name", default="original149")
    parser.add_argument("--ma3-reference", required=True, help="Independent preflight MA3 artifact directory")
    parser.add_argument("--reference-raw", help="Frozen original149 raw; required if candidate universe lacks infrastructure")
    args = parser.parse_args()
    raw, out = Path(args.raw).resolve(), Path(args.out).resolve()
    if out.exists() and any(out.iterdir()):
        raise RuntimeError(f"output already contains files; use a fresh directory: {out}")
    out.mkdir(parents=True, exist_ok=True)
    reference = Path(args.reference_raw).resolve() if args.reference_raw else raw
    os.environ["FROZEN_149_ROOT"] = str(reference.parent)
    os.environ["FROZEN_HOLDOUT70_ROOT"] = str(raw.parent)
    compare_path = Path(args.compare_script).resolve()
    compare = load_compare(compare_path)
    compare.FROZEN149, compare.FROZEN70, compare.OUT = reference, raw, out / "work"
    name = f"{args.universe_name}_{args.variant.lower()}"
    contract = {"line": "COMPACT21_LEARNER_SWAP_V1", "variant": args.variant,
                "raw": str(raw), "reference_raw": str(reference), "universe": args.universe_name,
                "canonical_models_sha256": file_hash(SRC / "etf_trader" / "source_only" / "models.py"),
                "canonical_compare_sha256": file_hash(compare_path), "runner_sha256": file_hash(Path(__file__)),
                "raw_files_sha256": {path.name: file_hash(path) for path in sorted(raw.glob("*.csv"))},
                "reference_infrastructure_sha256": {path.name: file_hash(path)
                                                       for ticker in compare.INFRA
                                                       if (path := reference / f"{ticker}.csv").exists()},
                "intervention_sources_sha256": {path.name: file_hash(path)
                                                  for path in (HERE / "learners.py", HERE / "integrity.py")
                                                  if path.exists()},
                "compact63_unchanged_by_design": True,
                "negative_feedback_changed": False, "CAGR_used_for_selection": False}
    contract["execution_control"] = {
        "hybrid_ensemble_n_jobs": 1,
        "historical_hybrid_ensemble_n_jobs": 2,
        "comparison": "all candidates versus a fresh BASE with the same deterministic execution",
        "reason": "control ExtraTrees thread scheduling nondeterminism without changing model parameters",
    }
    ma3_reference = Path(args.ma3_reference).resolve()
    reference_contract_path = ma3_reference / "INPUT_CONTRACT.json"
    reference_contract = json.loads(reference_contract_path.read_text())
    contract["ma3_reference_contract_sha256"] = file_hash(reference_contract_path)
    contract["ma3_reference_contract"] = reference_contract
    from compact21_learner_swap_v1.prepare_ma3 import environment_contract
    contract["environment"] = environment_contract()
    environment_comparison = persist_input_environment_evidence(out, contract, reference_contract)

    if (reference_contract.get("line") != "COMPACT21_LEARNER_SWAP_V1"
            or reference_contract.get("purpose") != "independent_ma3_reference"
            or reference_contract.get("historical_outputs_consumed") is not False
            or reference_contract.get("titanium_scores_consumed") is not False
            or not reference_contract.get("canonical_sources_sha256")
            or reference_contract.get("repeat_verification", {}).get("requested") is not True
            or reference_contract.get("repeat_verification", {}).get("passed") is not True):
        raise RuntimeError("Independent MA3 preflight reference provenance/repeat gate failed")
    if reference_contract.get("raw_files_sha256") != contract["raw_files_sha256"]:
        raise RuntimeError("Independent MA3 reference raw source mismatch")
    for relative, expected in reference_contract.get("canonical_sources_sha256", {}).items():
        if file_hash(REPO / relative) != expected:
            raise RuntimeError(f"Independent MA3 reference canonical source changed: {relative}")
    if not environment_comparison["passed"]:
        raise RuntimeError("Independent MA3 reference numerical environment mismatch; see ENVIRONMENT_COMPARISON.json")
    candidate, titanium_raw, candidate_tickers = compare.prepare_candidate_and_titanium_raw(name, raw)
    candidate_hashes = {path.name: file_hash(path) for path in sorted(candidate.glob("*.csv"))}
    if candidate_hashes != reference_contract.get("candidate_raw_files_sha256"):
        raise RuntimeError("Independent MA3 reference normalized candidate raw differs")
    contract["candidate_raw_files_sha256"] = candidate_hashes
    (out / "INPUT_CONTRACT.json").write_text(json.dumps(contract, indent=2) + "\n")
    base = compare.OUT / name
    ma3_out = base / "ma3_panel"
    compare.run([sys.executable, str(compare.ETF / "scripts" / "build_ma3_panel_source_only.py"),
                 "--data", str(candidate), "--cluster-data", str(candidate), "--output", str(ma3_out)])
    panel = pd.read_pickle(ma3_out / "RAW_FEATURE_PANEL.pkl")
    from compact21_learner_swap_v1.integrity import compare_panels, write_ma3_evidence
    panel_comparison = compare_panels(pd.read_pickle(ma3_reference / "RAW_FEATURE_PANEL.pkl"), panel)
    clusters_comparison = compare_panels(pd.read_csv(ma3_reference / "DYNAMIC_CLUSTER_MEMBERSHIP.csv"),
                                         pd.read_csv(ma3_out / "DYNAMIC_CLUSTER_MEMBERSHIP.csv"))
    if (panel_comparison["reference_sha256"] != reference_contract.get("ma3_panel_semantic_sha256")
            or clusters_comparison["reference_sha256"] != reference_contract.get("cluster_membership_semantic_sha256")):
        raise RuntimeError("Independent MA3 reference content does not match its contract")
    write_ma3_evidence(ma3_out)
    evidence = out / "evidence"
    evidence.mkdir()
    shutil.copytree(ma3_out, evidence / "ma3")
    reference_comparison = {"passed": panel_comparison["exact_equal"] and clusters_comparison["exact_equal"],
                            "panel": panel_comparison, "clusters": clusters_comparison,
                            "reference_contract_sha256": file_hash(reference_contract_path)}
    (out / "MA3_REFERENCE_COMPARISON.json").write_text(json.dumps(reference_comparison, indent=2) + "\n")
    if not reference_comparison["passed"]:
        raise RuntimeError("Independent MA3 regeneration differs semantically from preflight; complete evidence retained")
    titanium_out = base / "titanium"
    full_tit, full_tit_path = build_titanium(titanium_raw, titanium_out, args.variant)
    tit = full_tit[full_tit.ticker.astype(str).isin(candidate_tickers)].copy()
    if tit.ticker.nunique() != len(candidate_tickers):
        raise RuntimeError("Titanium candidate coverage incomplete")
    tit_path = base / "TIT_R_CANDIDATES_ONLY.csv"
    tit.to_csv(tit_path, index=False)
    fit = compare.fit_ensemble_producer(panel, tit, candidate_tickers, n_jobs=1)
    if not bool(fit.fit_audit["maturity_ok"].all()):
        raise RuntimeError("hybrid maturity audit failed")
    predictions_path = base / "ENSEMBLE_TAIL_OOS.csv"
    fit.predictions.to_csv(predictions_path, index=False)
    fit.fit_audit.to_csv(base / "ENSEMBLE_FIT_AUDIT.csv", index=False)
    state = {"base": base, "candidate_raw": candidate, "titanium_raw": titanium_raw,
             "candidate_tickers": candidate_tickers, "tit": tit, "tit_full_path": full_tit_path,
             "tit_candidate_path": tit_path, "pred": fit.predictions, "pred_path": predictions_path,
             "ma3_panel_path": ma3_out / "RAW_FEATURE_PANEL.pkl"}
    result = compare.replay_full_universe(state)
    transform_paths = sorted((titanium_out / "annual_models").glob("stability_transform_*.json"))
    transforms = [json.loads(path.read_text()) for path in transform_paths]
    if not transforms:
        raise RuntimeError("Missing Compact intervention fit metadata")
    result["stability"] = {"variant": args.variant, "Compact21_only": True,
                           "transforms": transforms, "fit_years": [row["year"] for row in transforms],
                           "maturity_all": all(h["maturity_ok"] for row in transforms for h in row["horizons"].values()),
                           "negative_feedback_changed": False,
                           "compact63_mean_prediction_sha256": {str(row["year"]): row["horizons"]["63"]["mean_predictions_sha256"] for row in transforms}}
    result["line"] = "COMPACT21_LEARNER_SWAP_V1"
    result["ma3_semantic_reference"] = reference_comparison
    for path in (titanium_out / "ANNUAL_PREDICTIONS.csv", full_tit_path, tit_path,
                 predictions_path, base / "ENSEMBLE_FIT_AUDIT.csv", base / "FULL_UNIVERSE_PATH.npz"):
        shutil.copy2(path, evidence / path.name)
    shutil.copytree(titanium_out / "annual_models", evidence / "annual_models",
                    ignore=shutil.ignore_patterns(".xgb_scratch"))
    result["evidence_files_sha256"] = {str(path.relative_to(evidence)): file_hash(path)
                                         for path in sorted(evidence.rglob("*")) if path.is_file()}
    (out / f"RESULT_{args.variant}.json").write_text(json.dumps(result, indent=2) + "\n")
    shutil.copyfile(base / "DAILY_LEADERS.csv", out / f"DAILY_LEADERS_{args.variant}.csv")
    print(json.dumps({"variant": args.variant, "metrics": result["v2_full_universe"],
                      "maturity_all": result["stability"]["maturity_all"]}, indent=2), flush=True)


if __name__ == "__main__":
    main()
