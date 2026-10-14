"""Fattibilità ListNet offline: tre acquisizioni native, BASE conservato."""
from __future__ import annotations

import argparse
import hashlib
import importlib.metadata
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / "vendor/etf_trader_v2/src")]
from etf_trader.source_only import kernel as k
from compact21_predictive_v2.run import numerical_gate, predictions_frame
from compact21_predictive_v2.metrics import evaluate
from compact21_learner_swap_v1.run_benchmark import evaluation_coverage, score_gap, compare_native
from ranker_stability_v1.run_ranker_benchmark_full import load, train_frame, align, stability, quality

LINE = "PAPER_LTR_V1"
VARIANT = "LISTNET_DECILE_64"
YEARS = tuple(range(2017, 2027))
KEYS = ["signal_date", "ticker"]
PAIRS = ((1, 2), (1, 3), (2, 3))


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def write_result(out, result):
    # Sostituzione atomica: un'interruzione non deve troncare il checkpoint JSON.
    pending = out / "RESULT.pending.json"
    pending.write_text(json.dumps(result, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    pending.replace(out / "RESULT.json")


def annual_frames(panels, year):
    trains = {i: train_frame(panels[i], year) for i in (1, 2, 3)}
    tests = {}
    cutoff = pd.Timestamp(year, 1, 1)
    for i in (1, 2, 3):
        frame = panels[i]
        valid = frame[k.F2D_FEATURES].notna().sum(axis=1) >= 30
        tests[i] = frame[(frame.signal_date.dt.year == year) &
                         (frame.signal_date <= "2026-06-30") & valid].sort_values(KEYS).reset_index(drop=True)
        if tests[i].empty or trains[i].empty:
            raise ValueError(f"Coorte annuale vuota: anno {year}, acquisizione {i}")
        for role, part in (("training", trains[i]), ("inferenza", tests[i])):
            if part[KEYS].isna().any().any() or part.duplicated(KEYS).any():
                raise ValueError(f"Chiavi mancanti o duplicate nel {role}: {year}/{i}")
        if not ((trains[i].signal_date < cutoff) & (trains[i].exit_date_21 < cutoff)).all():
            raise ValueError(f"Maturazione annuale non rispettata: {year}/{i}")
    common = align([tests[i] for i in (1, 2, 3)])[1]
    if common.empty:
        raise ValueError(f"Supporto comune di inferenza vuoto: {year}")
    return trains, tests, common


def normalized_reference(frame, name):
    required = set(KEYS + ["vintage", "pred"])
    if not required.issubset(frame):
        raise ValueError(f"Colonne mancanti nel parquet BASE {name}")
    result = frame.copy()
    result["signal_date"] = pd.to_datetime(result.signal_date, errors="raise")
    result["vintage"] = result.vintage.astype(str)
    if result[KEYS + ["vintage"]].isna().any().any() or result.duplicated(KEYS + ["vintage"]).any():
        raise ValueError(f"Chiavi mancanti o duplicate nel parquet BASE {name}")
    if set(result.vintage) != {"1", "2", "3"} or set(result.signal_date.dt.year) != set(YEARS):
        raise ValueError(f"Acquisizioni o anni BASE incompleti: {name}")
    if not np.isfinite(result.pred.to_numpy(float)).all():
        raise ValueError(f"Predizioni BASE non finite: {name}")
    return result


def verify_rows(reference, expected, year, repeat, name, targets=False):
    actual = reference[(reference.signal_date.dt.year == year) &
                       (reference.vintage == str(repeat))].sort_values(KEYS).reset_index(drop=True)
    expected = expected.sort_values(KEYS).reset_index(drop=True)
    if not actual[KEYS].equals(expected[KEYS]):
        raise ValueError(f"Supporto BASE differente: {name}, {year}/{repeat}")
    if targets:
        for column in ("target_rank_21", "exit_date_21"):
            if column not in actual:
                raise ValueError(f"Target BASE assente: {column}")
            left = actual[column]
            right = expected[column]
            if column == "exit_date_21":
                left = pd.to_datetime(left, errors="raise")
                right = pd.to_datetime(right, errors="raise")
            if not left.equals(right):
                raise ValueError(f"Target BASE differente: {column}, {year}/{repeat}")
        if "fwd_ret_21" in expected:
            if "target_ret_21" not in actual or not actual.target_ret_21.equals(expected.fwd_ret_21):
                raise ValueError(f"Rendimento BASE differente: {year}/{repeat}")
    return len(actual)


def verified_baseline(directory, hashes, panels):
    path = Path(directory)
    result_path = path / "RESULT.json"
    baseline = json.loads(result_path.read_text(encoding="utf-8"))
    if (baseline.get("variant") != "BASE" or baseline.get("line") != "COMPACT21_PREDICTIVE_V2" or
            baseline.get("status") != "COMPACT21_PREDICTIVE_V2_COMPLETE" or
            baseline.get("years") != list(YEARS) or set(baseline.get("per_year", {})) != set(map(str, YEARS))):
        raise ValueError("Il riferimento deve essere il BASE predictive V2 completo sui dieci anni")
    if baseline.get("input_sha256") != hashes:
        raise ValueError("Hash dei tre input differenti dal BASE conservato")
    if baseline.get("ALL_DETERMINISM_PASS") is not True or baseline.get("LEGACY_PARITY_PASS") is not True:
        raise ValueError("Il BASE conservato non certifica determinismo e parità dei controlli")
    tables = {}
    for name in ("NATIVE_PREDICTIONS.parquet", "COMMON_PREDICTIONS.parquet"):
        if baseline.get("files_sha256", {}).get(name) != sha(path / name):
            raise ValueError(f"Hash del parquet BASE non corrispondente: {name}")
        tables[name] = normalized_reference(pd.read_parquet(path / name), name)
    native_count = common_count = 0
    for year in YEARS:
        trains, tests, common = annual_frames(panels, year)
        coverage = evaluation_coverage(trains, tests, common)
        if coverage != baseline["per_year"][str(year)].get("evaluation_coverage"):
            raise ValueError(f"Copertura di valutazione differente dal BASE: {year}")
        for i in (1, 2, 3):
            native_count += verify_rows(tables["NATIVE_PREDICTIONS.parquet"], tests[i], year, i, "native", True)
            common_count += verify_rows(tables["COMMON_PREDICTIONS.parquet"], common, year, i, "comune")
    if native_count != len(tables["NATIVE_PREDICTIONS.parquet"]) or common_count != len(tables["COMMON_PREDICTIONS.parquet"]):
        raise ValueError("Righe aggiuntive nei parquet BASE")
    audit = {"declared_source_run": "37229180477", "source_run_provenance": "origine dichiarata dal workflow; hash e contenuto verificati dal runner",
             "result_sha256": sha(result_path), "files_sha256": baseline["files_sha256"],
             "input_identity_PASS": True, "evaluation_coverage_PASS": True,
             "prediction_keys_and_native_targets_PASS": True, "baseline_fits_executed": 0}
    return baseline, audit


def checked_predictions(predictions, tests):
    if len(predictions) != len(tests):
        raise ValueError("Numero di vettori di predizione inatteso")
    values = []
    for prediction, test in zip(predictions, tests):
        p = np.asarray(prediction)
        if p.shape != (len(test),) or not np.isfinite(p).all():
            raise ValueError("Predizioni non finite o non allineate")
        values.append(p)
    return values


def main():
    parser = argparse.ArgumentParser(description="Fattibilità ListNet sui tre dataset congelati Original149")
    for i in (1, 2, 3):
        parser.add_argument(f"--r{i}", required=True)
    parser.add_argument("--out", required=True)
    parser.add_argument("--baseline", required=True)
    parser.add_argument("--years", default=",".join(map(str, YEARS)))
    args = parser.parse_args()
    if tuple(map(int, args.years.split(","))) != YEARS:
        raise ValueError("Sono richiesti esattamente gli anni ordinati 2017–2026")
    try:
        numeric = numerical_gate()
    except Exception as exc:
        raise ValueError("Controllo canonico dell'ambiente numerico non superato") from exc
    out = Path(args.out)
    if out.exists() and any(out.iterdir()):
        raise ValueError("La cartella di output deve essere nuova o vuota")
    inputs = {i: Path(getattr(args, f"r{i}")) for i in (1, 2, 3)}
    hashes = {str(i): sha(inputs[i] / "TI_COMPACT.parquet") for i in (1, 2, 3)}
    panels = {i: load(inputs[i]) for i in (1, 2, 3)}
    baseline, baseline_audit = verified_baseline(args.baseline, hashes, panels)
    # Import differito: nessun fit può precedere tutti i controlli sul BASE.
    from paper_ltr_v1.learner import fit
    out.mkdir(parents=True, exist_ok=True)
    model_dir = out / "models"
    model_dir.mkdir()
    sources = sorted(set(list((ROOT / "paper_ltr_v1").glob("*.py")) +
                         list((ROOT / "compact21_predictive_v2").glob("*.py")) +
                         list((ROOT / "compact21_learner_swap_v1").glob("*.py")) +
                         list((ROOT / "vendor/etf_trader_v2/src/etf_trader/source_only").glob("*.py")) +
                         [ROOT / "ranker_stability_v1/run_ranker_benchmark_full.py"]))
    result = {"status": "RUNNING", "line": LINE, "variant": VARIANT, "years": list(YEARS),
              "input_sha256": hashes, "input_contract": baseline["input_contract"],
              "baseline": baseline_audit, "per_year": {}, "python": sys.version,
              "environment": {n: importlib.metadata.version(n) for n in
                              ("numpy", "pandas", "scikit-learn", "xgboost", "lightgbm", "scipy", "pyarrow")},
              "numeric_contract": numeric, "sources": {p.relative_to(ROOT).as_posix(): sha(p) for p in sources},
              "preregistration_sha256": sha(ROOT / "paper_ltr_v1/PREREGISTRATION.md"),
              "negative_feedback_changed": False, "portfolio_evaluation": False, "production_adoption": False,
              "feasibility_only": True, "baseline_fits_executed": 0,
              "determinism_scope": "solo rifit indipendente Repeat2 del 2017; nessuna certificazione degli altri anni"}
    (out / "INPUT_CONTRACT.json").write_text(json.dumps(result, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    write_result(out, result)
    native_frames, common_frames, common_quality_frames = [], [], []
    try:
        for year in YEARS:
            trains, tests, common = annual_frames(panels, year)
            coverage = evaluation_coverage(trains, tests, common)
            pcs, pns, audits, times = {}, {}, {}, {}
            for i in (1, 2, 3):
                print(f"ListNet: avvio anno {year}, acquisizione {i}; checkpoint in models", flush=True)
                predictions, audit, _, seconds = fit(trains[i], [common, tests[i]], year, model_dir, f"{year}_{i}")
                pcs[i], pns[i] = checked_predictions(predictions, [common, tests[i]])
                audits[str(i)], times[str(i)] = audit, seconds
                native_frames.append(predictions_frame(tests[i], pns[i], i))
                cc = common[KEYS].copy()
                cc["pred"], cc["vintage"] = pcs[i], i
                common_frames.append(cc)
                common_quality_frames.append(predictions_frame(common, pcs[i], i))
            determinism = {"executed": False, "PASS": None, "scope": "non eseguito per questo anno"}
            if year == 2017:
                print("ListNet: controllo indipendente Repeat2 anno 2017", flush=True)
                repeated, repeated_audit, _, repeated_seconds = fit(trains[2], [common, tests[2]], year, model_dir, "2017_2_det")
                repeated = checked_predictions(repeated, [common, tests[2]])
                equal = all(x.dtype == y.dtype and x.tobytes() == y.tobytes()
                            for x, y in zip(repeated, [pcs[2], pns[2]]))
                determinism = {"executed": True, "PASS": equal, "common_and_native_bytes_exact": equal,
                               "scope": "Repeat2 2017", "transforms": repeated_audit, "fit_seconds": repeated_seconds}
                if not equal:
                    result["determinism_2017_repeat2"] = determinism
                    raise ValueError("Il rifit indipendente Repeat2 2017 produce predizioni differenti")
            qualities = {}
            for i in (1, 2, 3):
                mask = (tests[i].target_rank_21.notna() & tests[i].exit_date_21.notna() &
                        (tests[i].exit_date_21 <= pd.Timestamp("2026-07-01"))).to_numpy()
                if not mask.any():
                    raise ValueError(f"Nessun esito maturo per {year}/{i}")
                qualities[str(i)] = quality(tests[i].loc[mask], pns[i][mask])
            result["per_year"][str(year)] = {
                "common_inference": {f"{i}-{j}": stability(common[KEYS], pcs[i], pcs[j]) for i, j in PAIRS},
                "native_inference": compare_native(tests, pns),
                "common_score_gap": {f"{i}-{j}": score_gap(common[KEYS], pcs[i], pcs[j]) for i, j in PAIRS},
                "quality": qualities, "evaluation_coverage": coverage, "transforms": audits,
                "fit_seconds": times, "determinism": determinism, "maturity_PASS": True,
                "baseline_coverage_PASS": coverage == baseline["per_year"][str(year)]["evaluation_coverage"]}
            pd.concat(native_frames, ignore_index=True).to_parquet(out / "NATIVE_PREDICTIONS.parquet", index=False)
            pd.concat(common_frames, ignore_index=True).to_parquet(out / "COMMON_PREDICTIONS.parquet", index=False)
            write_result(out, result)
            print(f"ListNet: anno {year} completato; predizioni e checkpoint conservati", flush=True)
        result["predictive"] = evaluate(pd.concat(native_frames, ignore_index=True), quality_exit_cutoff="2026-07-01")
        result["predictive_common_repeat2"] = evaluate(pd.concat(common_quality_frames, ignore_index=True), quality_exit_cutoff="2026-07-01")
        result["ALL_MATURITY_PASS"] = all(cell["maturity_PASS"] for cell in result["per_year"].values())
        result["DETERMINISM_2017_REPEAT2_PASS"] = result["per_year"]["2017"]["determinism"]["PASS"]
        result["files_sha256"] = {p.name: sha(p) for p in sorted(out.glob("*.parquet"))}
        result["model_files_sha256"] = {p.relative_to(out).as_posix(): sha(p) for p in sorted(model_dir.rglob("*")) if p.is_file()}
        if not result["model_files_sha256"]:
            raise ValueError("Nessun checkpoint di modello conservato")
        result["status"] = LINE + "_COMPLETE"
        write_result(out, result)
        print("ListNet: fattibilità completata; adozione in produzione disabilitata", flush=True)
    except Exception as exc:
        result["status"] = LINE + "_FAILED"
        result["failure"] = {"message": "Esperimento interrotto; evidenza parziale e checkpoint conservati", "detail": str(exc)}
        write_result(out, result)
        print("ListNet: esperimento interrotto, consultare RESULT.json", flush=True)
        raise


if __name__ == "__main__":
    main()
