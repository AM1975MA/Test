#!/usr/bin/env python3
"""Aggregate every preregistered full replay; fail closed on missing evidence."""
from __future__ import annotations

import argparse
import csv
from datetime import datetime
import hashlib
import json
import math
from pathlib import Path
import re
from statistics import mean

PAIRS = ((1, 2), (1, 3), (2, 3))
REQUIRED_CONTROLS = {"BASE", "Q4", "Q4_LEGACY"}
METRICS = ("cagr", "maxdd", "sharpe", "annualized_turnover")


def read_json(path):
    def reject(value):
        raise ValueError(f"Nonfinite JSON value {value} in {path}")
    return json.loads(Path(path).read_text(), parse_constant=reject)


def sha256(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def leaders(path):
    with Path(path).open(newline="") as stream:
        reader = csv.DictReader(stream)
        if not {"date", "top1", "top2"}.issubset(reader.fieldnames or ()):
            raise ValueError(f"Missing leader columns: {path}")
        rows = {}
        for row in reader:
            date = datetime.fromisoformat(row["date"]).date().isoformat()
            if date in rows or not row["top1"] or not row["top2"]:
                raise ValueError(f"Duplicate date or missing leader: {path}, {date}")
            rows[date] = (row["top1"], row["top2"])
    if not rows:
        raise ValueError(f"Empty leaders: {path}")
    return rows


def disagreement(left, right):
    dates = sorted(set(left) & set(right))
    if not dates:
        raise ValueError("No common leader dates")
    if set(left) != set(right):
        raise ValueError("Leader date coverage mismatch; no silent inner-join loss")
    top1 = [left[d][0] != right[d][0] for d in dates]
    top2 = [left[d][1] != right[d][1] for d in dates]
    return {"top1_disagreement": mean(top1), "top2_disagreement": mean(top2),
            "either_disagreement": mean(a or b for a, b in zip(top1, top2)),
            "common_dates": len(dates), "left_dates": len(left), "right_dates": len(right),
            "coverage": 1.0, "start": dates[0], "end": dates[-1]}


def artifact_identity(path, root):
    for parent in (path.parent, *path.parents):
        match = re.fullmatch(r"(?:compact21-)?full-(.+)-r([123])", parent.name)
        if match:
            return match.group(1), int(match.group(2))
        if parent == root:
            break
    raise ValueError(f"Result must be under full-<variant>-r<repeat>: {path}")


def load_results(root):
    root = Path(root).resolve()
    results = {}
    for path in sorted(root.rglob("RESULT_*.json")):
        variant, repeat = artifact_identity(path, root)
        if path.name != f"RESULT_{variant}.json":
            raise ValueError(f"Artifact/result variant mismatch: {path}")
        identity = (variant, repeat)
        if identity in results:
            raise ValueError(f"Duplicate result: {identity}")
        leader_path = path.with_name(f"DAILY_LEADERS_{variant}.csv")
        contract_path = path.with_name("INPUT_CONTRACT.json")
        if not leader_path.exists() or not contract_path.exists():
            raise ValueError(f"Missing leaders or input contract beside {path}")
        result, contract = read_json(path), read_json(contract_path)
        if contract.get("variant") != variant or result.get("stability", {}).get("variant") != variant:
            raise ValueError(f"Result/contract variant mismatch: {identity}")
        for name in METRICS:
            value = result.get("v2_full_universe", {}).get(name)
            if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
                raise ValueError(f"Invalid {name}: {identity}")
        results[identity] = {"result": result, "contract": contract, "leaders": leaders(leader_path),
                             "files": {"result": str(path), "result_sha256": sha256(path),
                                       "leaders_sha256": sha256(leader_path), "contract_sha256": sha256(contract_path)}}
    variants = {v for v, _ in results}
    if not REQUIRED_CONTROLS.issubset(variants):
        raise ValueError(f"Missing controls: {REQUIRED_CONTROLS - variants}")
    for variant in variants:
        if {r for v, r in results if v == variant} != {1, 2, 3}:
            raise ValueError(f"Incomplete three-snapshot replay: {variant}")
    return results, sorted(variants)


def evidence_checks(row, baseline, variant):
    result, contract = row["result"], row["contract"]
    base_result, base_contract = baseline["result"], baseline["contract"]
    stability = result.get("stability", {})
    transforms = stability.get("transforms", [])
    maturity = bool(transforms) and stability.get("maturity_all") is True
    years = []
    for transform in transforms:
        years.append(transform["year"])
        for horizon in ("21", "63"):
            audit = transform.get("horizons", {}).get(horizon, {})
            try:
                cutoff = datetime.fromisoformat(audit["fit_cutoff"])
                max_signal = datetime.fromisoformat(audit["max_signal"])
                max_exit = datetime.fromisoformat(audit["max_exit"])
                maturity = maturity and audit.get("maturity_ok") is True and max_signal < cutoff and max_exit < cutoff
            except (KeyError, TypeError, ValueError):
                maturity = False
    source = result.get("source_only", {})
    hashes = ("titanium_full_sha256", "titanium_candidates_sha256", "predictions_sha256", "ma3_panel_sha256")
    source_only = (source.get("historical_scores_consumed") is False
                   and source.get("historical_paths_consumed") is False
                   and all(isinstance(source.get(key), str) and re.fullmatch(r"[a-f0-9]{64}", source[key]) for key in hashes))
    preserved63 = variant == "Q4_LEGACY" or (
        stability.get("compact63_mean_prediction_sha256") == base_result.get("stability", {}).get("compact63_mean_prediction_sha256")
        and bool(stability.get("compact63_mean_prediction_sha256")))
    source_contract = all(contract.get(key) is not None and contract.get(key) == base_contract.get(key)
                          for key in ("canonical_models_sha256", "canonical_compare_sha256", "raw_files_sha256"))
    return {"maturity_audits": bool(maturity), "fit_years_unique": len(years) == len(set(years)),
            "fit_years_match_base": years == [t["year"] for t in base_result.get("stability", {}).get("transforms", [])],
            "source_only_regeneration": bool(source_only), "same_raw_and_canonical_source_as_base": source_contract,
            "negative_feedback_unchanged": contract.get("negative_feedback_changed") is False and stability.get("negative_feedback_changed") is False,
            "no_CAGR_selection": contract.get("CAGR_used_for_selection") is False,
            "compact63_preserved_or_explicit_legacy": bool(preserved63),
            "ma3_features_preserved": source.get("ma3_panel_sha256") == base_result.get("source_only", {}).get("ma3_panel_sha256")}


def summarize(root, historical_q4=None, benchmark_summary=None):
    results, variants = load_results(root)
    benchmark = read_json(benchmark_summary) if benchmark_summary else None
    if benchmark:
        expected = {(cell["variant"], int(cell["repeat"])) for cell in benchmark["full_matrix"]["include"]}
        if set(results) != expected:
            raise ValueError("Full results do not match frozen benchmark advancement matrix")
    reference_dates = set(results[("BASE", 1)]["leaders"])
    for (variant, repeat), row in results.items():
        base = results[("BASE", repeat)]["result"]
        if set(row["leaders"]) != reference_dates:
            raise ValueError(f"Date coverage differs from BASE: {variant}, repeat {repeat}")
        for key in ("sessions", "start", "end", "candidate_count", "completed_signals"):
            if row["result"].get(key) != base.get(key):
                raise ValueError(f"Replay scope {key} mismatch: {variant}, repeat {repeat}")
        if row["result"].get("sessions") != len(row["leaders"]):
            raise ValueError(f"Session/leader coverage mismatch: {variant}, repeat {repeat}")
    models = {}
    for variant in variants:
        metrics = {str(i): results[(variant, i)]["result"]["v2_full_universe"] for i in (1, 2, 3)}
        pairs = {f"{i}-{j}": disagreement(results[(variant, i)]["leaders"], results[(variant, j)]["leaders"]) for i, j in PAIRS}
        checks = {str(i): evidence_checks(results[(variant, i)], results[("BASE", i)], variant) for i in (1, 2, 3)}
        cagr = [metrics[str(i)]["cagr"] for i in (1, 2, 3)]
        models[variant] = {"raw_metrics": metrics, "metric_means": {key: mean(metrics[str(i)][key] for i in (1, 2, 3)) for key in METRICS},
                           "cagr_span_pp": 100 * (max(cagr) - min(cagr)), "cagr_mean": mean(cagr), "pairs": pairs,
                           "mean_top1_disagreement": mean(p["top1_disagreement"] for p in pairs.values()),
                           "mean_top2_disagreement": mean(p["top2_disagreement"] for p in pairs.values()),
                           "mean_either_disagreement": mean(p["either_disagreement"] for p in pairs.values()),
                           "evidence_checks": checks, "ALL_EVIDENCE_PASS": all(all(c.values()) for c in checks.values()),
                           "files": {str(i): results[(variant, i)]["files"] for i in (1, 2, 3)}}
    base = models["BASE"]
    for variant, model in models.items():
        comparison = {"span_le75pct_base": model["cagr_span_pp"] <= .75 * base["cagr_span_pp"],
                      "top1_not_worse_than_base": model["mean_top1_disagreement"] <= base["mean_top1_disagreement"],
                      "mean_CAGR_ge95pct_base": model["cagr_mean"] >= .95 * base["cagr_mean"],
                      "all_source_and_maturity_evidence": model["ALL_EVIDENCE_PASS"]}
        model["comparison_to_new_BASE"] = {"cagr_mean_delta_pp": 100 * (model["cagr_mean"] - base["cagr_mean"]),
                                            "span_reduction_pct": 100 * (1 - model["cagr_span_pp"] / base["cagr_span_pp"]) if base["cagr_span_pp"] else None,
                                            "top1_disagreement_delta_pp": 100 * (model["mean_top1_disagreement"] - base["mean_top1_disagreement"]),
                                            "checks": comparison,
                                            "ECONOMIC_ROBUSTNESS_GATE_PASS": variant != "BASE" and all(comparison.values())}
        model["same_repeat_changes_vs_BASE"] = {str(i): disagreement(results[(variant, i)]["leaders"], results[("BASE", i)]["leaders"]) for i in (1, 2, 3)}
    historical = None
    if historical_q4:
        old = read_json(historical_q4)
        historical = {"source": str(historical_q4), "source_sha256": sha256(historical_q4),
                      "q4_span_pp": old["q4_cagr_span_pp"], "native_span_pp": old["baseline_cagr_span_pp"],
                      "span_reduction_pct": old["cagr_span_reduction_pct"], "q4_mean_CAGR": old["mean_q4_cagr"],
                      "q4_mean_top1_disagreement": old["mean_q4_top1_disagreement"],
                      "caution": "Three-snapshot development evidence; old global Q4 also rounded inactive Compact63. Threading/runtime differences can affect parity. New BASE is the gate comparator; historical Q4 is not used for promotion."}
        for variant, model in models.items():
            model["comparison_to_historical_Q4_diagnostic_only"] = {
                "cagr_mean_delta_pp": 100 * (model["cagr_mean"] - old["mean_q4_cagr"]),
                "span_delta_pp": model["cagr_span_pp"] - old["q4_cagr_span_pp"],
                "top1_disagreement_delta_pp": 100 * (model["mean_top1_disagreement"] - old["mean_q4_top1_disagreement"])}
    return {"status": "COMPACT21_STABILITY_V1_FULL_SUMMARY_COMPLETE", "variants": variants, "models": models,
            "historical_Q4_reference": historical,
            "benchmark_matrix_checked": benchmark is not None,
            "gate_definition": "Span <=75% new BASE; Top1 disagreement <=new BASE; mean CAGR >=95% new BASE; source/maturity controls PASS.",
            "interpretation": "All preregistered outcomes retained. Gates are research diagnostics; no production adoption. Three snapshots do not estimate population variance or independent investment performance.",
            "production_adoption": False}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--inputs", required=True)
    parser.add_argument("--out", required=True)
    parser.add_argument("--benchmark-summary")
    parser.add_argument("--historical-q4", default=str(Path(__file__).resolve().parents[1] / "forensics_v1/results/FEATURE_QUANTIZATION_FULL_Q4_V1.json"))
    args = parser.parse_args()
    result = summarize(args.inputs, args.historical_q4, args.benchmark_summary)
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(result, indent=2, allow_nan=False) + "\n")
    print(json.dumps({v: {"mean_CAGR": q["cagr_mean"], "span_pp": q["cagr_span_pp"],
                          "top1_disagreement": q["mean_top1_disagreement"],
                          "gate": q["comparison_to_new_BASE"]["ECONOMIC_ROBUSTNESS_GATE_PASS"]}
                      for v, q in result["models"].items()}, indent=2, allow_nan=False))


if __name__ == "__main__":
    main()
