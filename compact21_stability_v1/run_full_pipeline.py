#!/usr/bin/env python3
"""Research-local Compact21 intervention followed by the canonical full replay.

No canonical source is edited.  Compact63 uses precisely the original matrices,
labels, seeds, worker and prediction reduction; only Compact21 is transformed.
Q4_LEGACY is an explicit historical control, rounding both horizons instead.
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

VARIANTS = ("BASE", "Q4", "ORDINAL", "ECON1BP", "Q4_ECON1BP", "SCALE", "SCALE_ECON1BP", "Q4_LEGACY")


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


def transform21(train: pd.DataFrame, test: pd.DataFrame, names: list[str], variant: str, cutoff):
    """All fitting is restricted to mature training rows for this fit year."""
    xtr = train[names].replace([np.inf, -np.inf], np.nan)
    xte = test[names].replace([np.inf, -np.inf], np.nan)
    metadata = {"feature_transform": "identity", "fit_rows": len(train), "feature_count": len(names)}
    if variant in ("Q4", "Q4_ECON1BP"):
        xtr, xte = xtr.round(4), xte.round(4)
        metadata.update(feature_transform="decimal_round", decimals=4)
    elif variant in ("SCALE", "SCALE_ECON1BP"):
        from compact21_stability_v1.quantization import ScaleAwareQuantizer
        quantizer = ScaleAwareQuantizer(names).fit(xtr)
        xtr, xte = quantizer.transform(xtr), quantizer.transform(xte)
        metadata.update(feature_transform="training_only_scale_aware", quantizer=quantizer.to_dict())
    y = (train.target_rank_21 * 100).round().astype(int).to_numpy()
    metadata["target_transform"] = "legacy_round_rank_x100"
    if variant in ("ORDINAL", "ECON1BP", "Q4_ECON1BP", "SCALE_ECON1BP"):
        from compact21_stability_v1.targets import RETURN_QUANTUM, training_labels
        target_mode = "ordinal" if variant == "ORDINAL" else "economic"
        y = training_labels(train, cutoff, mode=target_mode)
        metadata.update(target_transform=target_mode,
                        target_metadata={"return_quantum": RETURN_QUANTUM if target_mode == "economic" else None,
                                         "ties": "preserved", "rank": "dense_zero_based",
                                         "training_maturity_checked": True, "calibration": "fixed_preregistered"})
    return np.asarray(xtr), np.asarray(xte), np.asarray(y), metadata


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
        tasks, training, audit = [], {}, {}
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
                if horizon == 21 and variant not in ("BASE", "Q4_LEGACY"):
                    xtr, xte, y, transform = transform21(train, te, k.F2D_FEATURES, variant, cutoff)
                if variant == "Q4_LEGACY":
                    transform["feature_transform"] = "global_frame_decimal_round_4"
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
                    "canonical63_input_contract": horizon == 63 and variant != "Q4_LEGACY",
                }
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
            predictions = {}
            for horizon in (21, 63):
                seed_predictions = [np.load(td / f"pred_{horizon}_{int(seed)}.npy") for seed in k.COMPACT_SEEDS]
                predictions[horizon] = np.mean(seed_predictions, axis=0)
                audit[str(horizon)]["seed_predictions_sha256"] = [array_hash(p) for p in seed_predictions]
                audit[str(horizon)]["mean_predictions_sha256"] = array_hash(predictions[horizon])
            metadata = {"year": int(year), "variant": variant, "horizons": audit,
                        "seeds": [int(seed) for seed in k.COMPACT_SEEDS], "rounds": rounds,
                        "canonical_worker_sha256": file_hash(worker), "params": params,
                        "negative_feedback_changed": False}
            (Path(out) / f"stability_transform_{year}.json").write_text(json.dumps(metadata, indent=2) + "\n")
            return predictions, training, {"mode": "isolated_parallel_workers", "workers": max_workers,
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
    if variant == "Q4_LEGACY":
        compact.loc[:, k.F2D_FEATURES] = compact[k.F2D_FEATURES].round(4)
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
    contract = {"line": "COMPACT21_STABILITY_V1", "variant": args.variant,
                "raw": str(raw), "reference_raw": str(reference), "universe": args.universe_name,
                "canonical_models_sha256": file_hash(SRC / "etf_trader" / "source_only" / "models.py"),
                "canonical_compare_sha256": file_hash(compare_path), "runner_sha256": file_hash(Path(__file__)),
                "raw_files_sha256": {path.name: file_hash(path) for path in sorted(raw.glob("*.csv"))},
                "reference_infrastructure_sha256": {path.name: file_hash(path)
                                                       for ticker in compare.INFRA
                                                       if (path := reference / f"{ticker}.csv").exists()},
                "intervention_sources_sha256": {path.name: file_hash(path)
                                                  for path in (HERE / "targets.py", HERE / "quantization.py")
                                                  if path.exists()},
                "compact63_unchanged_by_design": args.variant != "Q4_LEGACY",
                "legacy_q4_note": "Prior full Q4 rounded both Compact21 and Compact63; Q4 here intervenes only on Compact21.",
                "negative_feedback_changed": False, "CAGR_used_for_selection": False}
    contract["execution_control"] = {
        "hybrid_ensemble_n_jobs": 1,
        "historical_hybrid_ensemble_n_jobs": 2,
        "comparison": "all candidates versus a fresh BASE with the same deterministic execution",
        "reason": "control ExtraTrees thread scheduling nondeterminism without changing model parameters",
    }
    (out / "INPUT_CONTRACT.json").write_text(json.dumps(contract, indent=2) + "\n")
    candidate, titanium_raw, candidate_tickers = compare.prepare_candidate_and_titanium_raw(name, raw)
    base = compare.OUT / name
    titanium_out = base / "titanium"
    full_tit, full_tit_path = build_titanium(titanium_raw, titanium_out, args.variant)
    tit = full_tit[full_tit.ticker.astype(str).isin(candidate_tickers)].copy()
    if tit.ticker.nunique() != len(candidate_tickers):
        raise RuntimeError("Titanium candidate coverage incomplete")
    tit_path = base / "TIT_R_CANDIDATES_ONLY.csv"
    tit.to_csv(tit_path, index=False)
    ma3_out = base / "ma3_panel"
    compare.run([sys.executable, str(compare.ETF / "scripts" / "build_ma3_panel_source_only.py"),
                 "--data", str(candidate), "--cluster-data", str(candidate), "--output", str(ma3_out)])
    panel = pd.read_pickle(ma3_out / "RAW_FEATURE_PANEL.pkl")
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
    result["stability"] = {"variant": args.variant, "Compact21_only": args.variant != "Q4_LEGACY",
                           "transforms": transforms, "fit_years": [row["year"] for row in transforms],
                           "maturity_all": all(h["maturity_ok"] for row in transforms for h in row["horizons"].values()),
                           "negative_feedback_changed": False,
                           "compact63_mean_prediction_sha256": {str(row["year"]): row["horizons"]["63"]["mean_predictions_sha256"] for row in transforms}}
    (out / f"RESULT_{args.variant}.json").write_text(json.dumps(result, indent=2) + "\n")
    shutil.copyfile(base / "DAILY_LEADERS.csv", out / f"DAILY_LEADERS_{args.variant}.csv")
    print(json.dumps({"variant": args.variant, "metrics": result["v2_full_universe"],
                      "maturity_all": result["stability"]["maturity_all"]}, indent=2), flush=True)


if __name__ == "__main__":
    main()
