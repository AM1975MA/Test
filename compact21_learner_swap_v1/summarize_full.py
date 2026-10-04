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
REQUIRED_CONTROLS = {"BASE", "RIDGE", "LGBM_LAMBDARANK"}
METRICS = ("cagr", "maxdd", "sharpe", "annualized_turnover")


from compact21_learner_swap_v1.summarize import read_json, YEARS, LINE


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
        match = re.fullmatch(r"(?:compact21-swap-|learner-)?full-(.+)-r([123])", parent.name)
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
        if contract.get("line") != LINE or result.get("line") != LINE: raise ValueError("Unexpected experiment line")
        if contract.get("variant") != variant or result.get("stability", {}).get("variant") != variant:
            raise ValueError(f"Result/contract variant mismatch: {identity}")
        for name in METRICS:
            value = result.get("v2_full_universe", {}).get(name)
            if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
                raise ValueError(f"Invalid {name}: {identity}")
        semantic = verify_retained_evidence(path, result)
        results[identity] = {"result": result, "semantic": semantic, "evidence_files_verified": True, "contract": contract, "leaders": leaders(leader_path),
                             "files": {"result": str(path), "result_sha256": sha256(path),
                                       "leaders_sha256": sha256(leader_path), "contract_sha256": sha256(contract_path)}}
    variants = {v for v, _ in results}
    if variants != REQUIRED_CONTROLS:
        raise ValueError(f"Missing or unexpected controls: {variants}")
    for variant in variants:
        if {r for v, r in results if v == variant} != {1, 2, 3}:
            raise ValueError(f"Incomplete three-snapshot replay: {variant}")
    return results, sorted(variants)


def environment_equal(left, right):
    required = ("python", "machine", "numpy", "pandas", "scipy", "sklearn", "execution_env", "numpy_build_config")
    return isinstance(left, dict) and isinstance(right, dict) and all(left.get(k) is not None and left.get(k) == right.get(k) for k in required)


def ma3_comparison_valid(result, contract):
    reference = result.get("ma3_semantic_reference", {})
    if reference.get("passed") is not True or reference.get("reference_contract_sha256") != contract.get("ma3_reference_contract_sha256"):
        return False
    for kind in ("panel", "clusters"):
        comparison = reference.get(kind, {})
        if any(comparison.get(k) is not True for k in ("exact_equal", "schema_equal", "key_equal", "index_equal")):
            return False
        if comparison.get("diagnostic_tolerance_used_for_gate") is not False or comparison.get("mismatched_columns") != [] or comparison.get("max_abs_diff") != 0:
            return False
        own = comparison.get("own_sha256")
        if not isinstance(own, str) or not re.fullmatch("[a-f0-9]{64}", own) or own != comparison.get("reference_sha256"):
            return False
    embedded = contract.get("ma3_reference_contract", {})
    return (embedded.get("line") == LINE and embedded.get("purpose") == "independent_ma3_reference"
            and embedded.get("historical_outputs_consumed") is False and embedded.get("titanium_scores_consumed") is False
            and embedded.get("must_not_replace_replay_generated_panel") is True
            and embedded.get("repeat_verification", {}).get("requested") is True
            and embedded.get("repeat_verification", {}).get("passed") is True
            and embedded.get("raw_files_sha256") == contract.get("raw_files_sha256")
            and environment_equal(contract.get("environment"), embedded.get("environment"))
            and embedded.get("ma3_panel_semantic_sha256") == reference["panel"]["reference_sha256"]
            and embedded.get("cluster_membership_semantic_sha256") == reference["clusters"]["reference_sha256"])


def verify_retained_evidence(path, result):
    """Check bytes, then independently reconstruct exact MA3 semantic signatures."""
    evidence = path.parent / "evidence"
    manifest = result.get("evidence_files_sha256", {})
    if not manifest or not evidence.is_dir(): raise ValueError("Missing retained replay evidence")
    actual = {str(p.relative_to(evidence)): sha256(p) for p in evidence.rglob('*') if p.is_file()}
    if actual != manifest: raise ValueError("Replay evidence file manifest mismatch")
    from compact21_learner_swap_v1.integrity import dataframe_fingerprint
    import pandas as pd
    panel = dataframe_fingerprint(pd.read_pickle(evidence / "ma3" / "RAW_FEATURE_PANEL.pkl"))
    clusters = dataframe_fingerprint(pd.read_csv(evidence / "ma3" / "DYNAMIC_CLUSTER_MEMBERSHIP.csv"))
    saved = read_json(evidence / "ma3" / "SEMANTIC_FINGERPRINT.json")
    if saved.get("panel") != panel or saved.get("clusters") != clusters:
        raise ValueError("Retained MA3 semantic signature inconsistent with actual panel/cluster data")
    if any(result.get("ma3_semantic_reference", {}).get(kind, {}).get("own_sha256") != fp["sha256"]
           for kind, fp in (("panel", panel), ("clusters", clusters))):
        raise ValueError("MA3 reported own signature inconsistent with actual retained data")
    return {"panel": panel["sha256"], "clusters": clusters["sha256"]}


def load_references(root):
    if root is None: raise ValueError("Missing independent MA3 preflight artifact inputs")
    from compact21_learner_swap_v1.integrity import dataframe_fingerprint
    import pandas as pd
    references = {}
    for path in Path(root).rglob("INPUT_CONTRACT.json"):
        match = next((re.fullmatch(r"learner-ma3-reference-r([123])", p.name) for p in path.parents
                      if re.fullmatch(r"learner-ma3-reference-r([123])", p.name)), None)
        if not match: raise ValueError(f"Unexpected preflight artifact identity: {path}")
        repeat = int(match.group(1))
        if repeat in references: raise ValueError("Duplicate independent MA3 preflight")
        contract = read_json(path)
        panel = dataframe_fingerprint(pd.read_pickle(path.with_name("RAW_FEATURE_PANEL.pkl")))
        clusters = dataframe_fingerprint(pd.read_csv(path.with_name("DYNAMIC_CLUSTER_MEMBERSHIP.csv")))
        saved = read_json(path.with_name("SEMANTIC_FINGERPRINT.json"))
        if saved.get("panel") != panel or saved.get("clusters") != clusters:
            raise ValueError("Preflight semantic signature differs from actual retained data")
        if contract.get("ma3_panel_semantic_sha256") != panel["sha256"] or contract.get("cluster_membership_semantic_sha256") != clusters["sha256"]:
            raise ValueError("Preflight contract semantic digest mismatch")
        repeat_proof = contract.get("repeat_verification", {})
        if repeat_proof.get("requested") is not True or repeat_proof.get("passed") is not True:
            raise ValueError("Missing exact independent preflight repeat proof")
        repeat_dir = path.parent / "repeat_rebuild"
        for kind, name in (("panel", "RAW_FEATURE_PANEL.pkl"), ("clusters", "DYNAMIC_CLUSTER_MEMBERSHIP.csv")):
            frame = pd.read_pickle(repeat_dir / name) if kind == "panel" else pd.read_csv(repeat_dir / name)
            fp = dataframe_fingerprint(frame)
            original = panel if kind == "panel" else clusters
            if fp != original: raise ValueError("Independent preflight repeat data differs semantically")
            report = repeat_proof.get(kind, {})
            if report.get("exact_equal") is not True or report.get("own_sha256") != fp["sha256"] or report.get("reference_sha256") != original["sha256"]:
                raise ValueError("Preflight repeated-build comparison proof mismatch")
        references[repeat] = {"contract": contract, "contract_sha256": sha256(path),
                              "semantic": {"panel": panel["sha256"], "clusters": clusters["sha256"]}}
    if set(references) != {1, 2, 3}: raise ValueError("Incomplete independent MA3 preflight artifacts")
    return references


def retained_maturity(path):
    """Audit the canonical Tail/macro and hybrid fits from retained evidence."""
    import pandas as pd
    evidence = Path(path).parent / "evidence"
    ok = True
    for year in YEARS:
        audit_path = evidence / "annual_models" / f"fit_audit_{year}.json"
        if not audit_path.exists(): return False
        audit = read_json(audit_path)
        if not isinstance(audit, list) or {a.get("model") for a in audit} != {"compact21", "compact63", "tail", "macro"} or len(audit) != 4:
            return False
        for row in audit:
            try:
                cutoff = datetime.fromisoformat(row["fit_date"])
                max_exit = datetime.fromisoformat(row["max_exit"])
                ok = ok and row.get("year") == year and cutoff == datetime(year,1,1) and max_exit < cutoff
            except (KeyError, TypeError, ValueError): return False
    audit_path = evidence / "ENSEMBLE_FIT_AUDIT.csv"
    if not audit_path.exists(): return False
    hybrid = pd.read_csv(audit_path)
    required = {"year", "n_train", "n_predict", "max_train_signal", "max_train_exit63", "cutoff", "maturity_ok"}
    if not required.issubset(hybrid) or hybrid.empty or set(hybrid.year) != set(YEARS) or hybrid.year.duplicated().any(): return False
    for row in hybrid.to_dict("records"):
        try:
            cutoff = datetime.fromisoformat(row["cutoff"])
            ok = (ok and row["maturity_ok"] is True and cutoff == datetime(int(row["year"]),1,1)
                  and datetime.fromisoformat(row["max_train_signal"]) < cutoff
                  and datetime.fromisoformat(row["max_train_exit63"]) < cutoff
                  and row["n_train"] > 0 and row["n_predict"] > 0)
        except (KeyError, TypeError, ValueError): return False
    return bool(ok)


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
    preserved63 = (
        stability.get("compact63_mean_prediction_sha256") == base_result.get("stability", {}).get("compact63_mean_prediction_sha256")
        and bool(stability.get("compact63_mean_prediction_sha256")))
    source_contract = all(contract.get(key) is not None and contract.get(key) == base_contract.get(key)
                          for key in ("canonical_models_sha256", "canonical_compare_sha256", "raw_files_sha256"))
    return {"maturity_audits": bool(maturity), "fit_years_unique": len(years) == len(set(years)),
            "fit_years_match_base": years == [t["year"] for t in base_result.get("stability", {}).get("transforms", [])],
            "source_only_regeneration": bool(source_only), "same_raw_and_canonical_source_as_base": source_contract,
            "negative_feedback_unchanged": contract.get("negative_feedback_changed") is False and stability.get("negative_feedback_changed") is False,
            "no_CAGR_selection": contract.get("CAGR_used_for_selection") is False,
            "compact63_preserved": bool(preserved63) and all(
                transform.get("horizons", {}).get("63") == base_transform.get("horizons", {}).get("63")
                for transform, base_transform in zip(transforms, base_result.get("stability", {}).get("transforms", []))),
            "canonical_annual_folds": years == YEARS,
            "environment_and_execution_equal_base": all(contract.get(k) is not None and contract.get(k) == base_contract.get(k)
                for k in ("execution_control", "runner_sha256", "intervention_sources_sha256", "reference_infrastructure_sha256")) and environment_equal(contract.get("environment"), base_contract.get("environment")),
            "ma3_exact_semantic_preflight": ma3_comparison_valid(result, contract),
            "ma3_exact_semantic_same_repeat_base": all(result.get("ma3_semantic_reference", {}).get(kind, {}).get("own_sha256") ==
                base_result.get("ma3_semantic_reference", {}).get(kind, {}).get("own_sha256") for kind in ("panel", "clusters")),
            "evidence_files_verified": row.get("evidence_files_verified") is True,
            "independent_preflight_artifact_verified": row.get("preflight_verified") is True,
            "canonical_tail_macro_hybrid_maturity": retained_maturity(row["files"]["result"])}


def summarize(root, historical_q4=None, benchmark_summary=None, ma3_reference_inputs=None):
    results, variants = load_results(root)
    if benchmark_summary is None: raise ValueError("Missing frozen benchmark summary")
    benchmark = read_json(benchmark_summary)
    if benchmark.get("status") != LINE + "_BENCHMARK_SUMMARY": raise ValueError("Unexpected benchmark summary status")
    if {r.get("variant") for r in benchmark.get("ranking", [])} != REQUIRED_CONTROLS or len(benchmark["ranking"]) != 3:
        raise ValueError("Incomplete benchmark gate table")
    references = load_references(ma3_reference_inputs)
    if benchmark:
        expected = {(cell["variant"], int(cell["repeat"])) for cell in benchmark["full_matrix"]["include"]}
        if set(results) != expected:
            raise ValueError("Full results do not match frozen benchmark advancement matrix")
    reference_dates = set(results[("BASE", 1)]["leaders"])
    for (variant, repeat), row in results.items():
        base = results[("BASE", repeat)]["result"]
        reference = references[repeat]
        row["preflight_verified"] = (row["semantic"] == reference["semantic"]
            and row["contract"].get("ma3_reference_contract_sha256") == reference["contract_sha256"]
            and row["contract"].get("ma3_reference_contract") == reference["contract"])
        if row["result"].get("candidate_count") is None or row["result"].get("completed_signals") is None:
            raise ValueError("Missing replay scope counts")
        dates = sorted(row["leaders"])
        if str(row["result"].get("start"))[:10] != dates[0] or str(row["result"].get("end"))[:10] != dates[-1]:
            raise ValueError("Leader scope dates mismatch")
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
    from compact21_learner_swap_v1.integrity import dataframe_fingerprint
    import pandas as pd
    tail_signatures = {}; annual_signatures = {}
    for identity, row in results.items():
        evidence = Path(row["files"]["result"]).parent / "evidence"
        pred = pd.read_csv(evidence / "ENSEMBLE_TAIL_OOS.csv", float_precision="round_trip")
        cols = ["signal_date", "ticker", "ET_TAIL", "XGB_TAIL", "TAIL_HYBRID"]
        if not set(cols).issubset(pred.columns): raise ValueError("Missing invariant Tail prediction columns")
        if pred.duplicated(["signal_date", "ticker"]).any(): raise ValueError("Duplicate Tail prediction keys")
        tail_signatures[identity] = dataframe_fingerprint(pred[cols])["sha256"]
        annual = pd.read_csv(evidence / "ANNUAL_PREDICTIONS.csv", float_precision="round_trip")
        if not {"signal_date", "ticker", "compact21", "compact63", "tail"}.issubset(annual.columns) or annual.duplicated(["signal_date", "ticker"]).any():
            raise ValueError("Missing or duplicate canonical annual prediction evidence")
        annual_signatures[identity] = dataframe_fingerprint(annual.drop(columns=["compact21"]))["sha256"]
    for variant, model in models.items():
        for repeat in (1,2,3):
            model["evidence_checks"][str(repeat)]["all_annual_components_except_compact21_preserved"] = annual_signatures[(variant,repeat)] == annual_signatures[("BASE",repeat)]
            model["evidence_checks"][str(repeat)]["canonical_tail_predictions_preserved"] = tail_signatures[(variant,repeat)] == tail_signatures[("BASE",repeat)]
        model["ALL_EVIDENCE_PASS"] = all(all(c.values()) for c in model["evidence_checks"].values())
    base = models["BASE"]
    benchmark_pass = {row["variant"]: row.get("ADVANCE_FULL_REPLAY") is True for row in benchmark.get("ranking", [])} if benchmark else {}
    for variant, model in models.items():
        comparison = {"span_le75pct_base": model["cagr_span_pp"] <= .75 * base["cagr_span_pp"],
                      "top1_not_worse_than_base": model["mean_top1_disagreement"] <= base["mean_top1_disagreement"],
                      "mean_CAGR_ge95pct_base": model["cagr_mean"] >= .95 * base["cagr_mean"],
                      "mean_MaxDD_not_worse_by_more_than2pp": model["metric_means"]["maxdd"] >= base["metric_means"]["maxdd"] - .02,
                      "mean_turnover_le110pct_base": model["metric_means"]["annualized_turnover"] <= 1.10 * base["metric_means"]["annualized_turnover"],
                      "all_source_and_maturity_evidence": model["ALL_EVIDENCE_PASS"]}
        model["comparison_to_new_BASE"] = {"cagr_mean_delta_pp": 100 * (model["cagr_mean"] - base["cagr_mean"]),
                                            "span_reduction_pct": 100 * (1 - model["cagr_span_pp"] / base["cagr_span_pp"]) if base["cagr_span_pp"] else None,
                                            "top1_disagreement_delta_pp": 100 * (model["mean_top1_disagreement"] - base["mean_top1_disagreement"]),
                                            "checks": comparison,
                                            "ECONOMIC_ROBUSTNESS_GATE_PASS": variant != "BASE" and all(comparison.values())}
        economic_pass = model["comparison_to_new_BASE"]["ECONOMIC_ROBUSTNESS_GATE_PASS"]
        model["BENCHMARK_GATE_PASS"] = benchmark_pass.get(variant, False)
        model["RESEARCH_CANDIDATE_PASS"] = variant != "BASE" and economic_pass and model["BENCHMARK_GATE_PASS"]
        model["conclusion"] = ("Qualified development research candidate; independent evidence still required." if model["RESEARCH_CANDIDATE_PASS"] else
            "Benchmark stable/quality-qualified, but full economic robustness failed." if model["BENCHMARK_GATE_PASS"] and not economic_pass else
            "Benchmark gate failed; diagnostic full economics cannot rescue this candidate." if variant != "BASE" else "Fresh canonical control.")
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
    return {"status": LINE + "_FULL_SUMMARY_COMPLETE", "variants": variants, "models": models,
            "historical_Q4_reference": historical,
            "benchmark_matrix_checked": benchmark is not None,
            "gate_definition": "Span <=75% new BASE; daily Top1 disagreement <=BASE; mean CAGR >=95% BASE; mean MaxDD >=BASE minus 2pp; mean turnover <=110% BASE; all source, maturity, Compact63 and exact MA3 semantic evidence PASS. Joint candidate also requires benchmark gate.",
            "interpretation": "All preregistered outcomes retained. Gates are research diagnostics; no production adoption. Three snapshots do not estimate population variance or independent investment performance.",
            "production_adoption": False}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--inputs", required=True)
    parser.add_argument("--out", required=True)
    parser.add_argument("--benchmark-summary", required=True)
    parser.add_argument("--ma3-reference-inputs", required=True)
    parser.add_argument("--historical-q4")
    args = parser.parse_args()
    result = summarize(args.inputs, args.historical_q4, args.benchmark_summary, args.ma3_reference_inputs)
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(result, indent=2, allow_nan=False) + "\n")
    print(json.dumps({v: {"mean_CAGR": q["cagr_mean"], "span_pp": q["cagr_span_pp"],
                          "top1_disagreement": q["mean_top1_disagreement"],
                          "gate": q["comparison_to_new_BASE"]["ECONOMIC_ROBUSTNESS_GATE_PASS"]}
                      for v, q in result["models"].items()}, indent=2, allow_nan=False))


if __name__ == "__main__":
    main()
