"""Results-only independent audit of OLC112 and its frozen OLC111 controls.

Reuses the independently tested accounting/date helpers; never refits or replays a
financial policy. The 12 new ledgers and six existing control ledgers are read.
"""
import argparse
import importlib.util
import json
from pathlib import Path

import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
AUDITOR_PATH = ROOT.parent / "olc111/src/analyze_results.py"
SPEC = importlib.util.spec_from_file_location("olc111_independent_audit", AUDITOR_PATH)
audit = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(audit)
ARMS = ("MEAN_ROTATION", "PRICE_ROTATION", "VIX_ROTATION", "TERM_ROTATION")
CONTROLS = ("BASE", "STATIC_75")


def compare_accounts(candidate, reference, *, start_idx=None):
    if not candidate[["k", "date"]].equals(reference[["k", "date"]]):
        raise ValueError("PAIRED_ACCOUNT_CALENDAR")
    left = audit.performance_window(candidate, start_idx=start_idx)
    right = audit.performance_window(reference, start_idx=start_idx)
    return dict(cagr_difference=left["cagr"]-right["cagr"],
        sampled_maxdd_difference=left["maxdd_sampled"]-right["maxdd_sampled"],
        log_growth_difference=left["log_growth"]-right["log_growth"],
        ending_relative_growth_ratio=float(np.exp(left["log_growth"]-right["log_growth"])),
        mean_exposure_difference=left["mean_exposure"]-right["mean_exposure"],
        full_cash_days_difference=left["full_cash_days"]-right["full_cash_days"])


def cash_spell_context(spells, daily, base):
    """Describe simultaneous observed account moves; make no causal attribution."""
    account = daily.set_index("k").nav_close
    benchmark = base.set_index("k").nav_close
    output = []
    for spell in spells:
        first, last = spell["start_idx"], spell["end_idx"]
        preceding = audit.performance_window(base, start_idx=first, end_idx=last)
        output.append(dict(**spell,
            account_return_first_to_last_cash_close=float(account.loc[last]/account.loc[first]-1),
            base_return_first_to_last_cash_close=float(benchmark.loc[last]/benchmark.loc[first]-1),
            base_return_preceding_close_to_last_cash_close=preceding["cumulative"],
            base_preceding_close_anchor_date=preceding["anchor_date"],
            comparison_is_causal_alpha=False,
            preceding_close_window_includes_liquidation_day=True,
            comparison_window="both_first_cash_close_and_preceding_close_through_last_full_cash_close"))
    return output


def run_audit(root=ROOT):
    root = Path(root).resolve()
    results, prior = root / "results", root.parent / "olc111/results"
    panel_path = root.parent / "olc110/source/data/XETRA_EUR_ETF.npz"
    with np.load(panel_path, allow_pickle=False) as source:
        panel = {key: source[key] for key in ("dates", "names", "C", "observed")}
    dates = np.asarray(panel["dates"], dtype="datetime64[D]")
    readiness = json.loads((results / "FIT_READINESS.json").read_text())
    source_readiness = json.loads((prior / "FIT_READINESS.json").read_text())
    if readiness != source_readiness:
        raise ValueError("READINESS_CHANGED_FROM_OLC111")
    manifest = json.loads((results / "RUN_MANIFEST.json").read_text())
    scores, prior_scores = audit._read_csv(results / "SCORES.csv"), audit._read_csv(prior / "SCORES.csv")
    expected = [f"{arm}__{scenario}" for arm in ARMS for scenario in audit.SCENARIOS]
    control_ids = [f"{arm}__{scenario}" for arm in CONTROLS for scenario in audit.SCENARIOS]
    if (manifest["completed_paths"] != 12 or set(manifest["completed_path_ids"]) != set(expected)
            or len(scores) != 12 or set(scores.path_id) != set(expected) or manifest["new_model_fits"] != 0):
        raise ValueError("INCOMPLETE_OR_REFITTED_ROTATION_MATRIX")
    ready, post_idx = int(readiness["all_heads_first_ready_idx"]), int(readiness["postwarmup_start_idx"])
    if (post_idx != ready+1 or str(dates[ready]) != readiness["all_heads_first_ready_date"]
            or str(dates[post_idx]) != readiness["postwarmup_start_date"]):
        raise ValueError("READINESS_CALENDAR_MISMATCH")
    if scores.start_idx.nunique() != 1 or scores.end_idx.nunique() != 1:
        raise ValueError("INCONSISTENT_RESULT_WINDOWS")
    begin, end = int(scores.start_idx.iloc[0]), int(scores.end_idx.iloc[0])
    if end != len(dates)-1:
        raise ValueError("RESULTS_DO_NOT_REACH_PANEL_END")
    freeze = json.loads((root / "docs/EXPERIMENT_FREEZE.json").read_text())
    frozen_hashes = {**freeze["code_hashes"], **freeze["input_hashes"],
                     "docs/DESIGN_AND_PROTOCOL.md": freeze["protocol_sha256"]}
    freeze_mismatches = [name for name, expected_hash in frozen_hashes.items()
                         if audit._sha256(root / name) != expected_hash]
    if freeze_mismatches:
        raise ValueError("FROZEN_INPUTS_OR_MODELS_CHANGED: "+", ".join(freeze_mismatches))
    hashes = {name: expected_hash for name, expected_hash in frozen_hashes.items()}
    for path in (Path(__file__), AUDITOR_PATH, panel_path, results / "FIT_READINESS.json",
                 results / "SCORES.csv", results / "RUN_MANIFEST.json"):
        hashes[str(path)] = audit._sha256(path)
    paths = {}
    for path_id in expected+control_ids:
        source = results if path_id in expected else prior
        folder, loaded = source / path_id, {}
        for key, filename in (("daily", "DAILY.csv.gz"), ("orders", "ORDERS.csv.gz"),
                              ("trace", "POLICY_TRACE.csv.gz"), ("instructions", "INSTRUCTIONS.csv.gz")):
            loaded[key] = audit._read_csv(folder / filename)
            hashes[str(folder / filename)] = audit._sha256(folder / filename)
        loaded["native"] = json.loads((folder / "METRICS.json").read_text())
        hashes[str(folder / "METRICS.json")] = audit._sha256(folder / "METRICS.json")
        audit.validate_result_calendar(loaded["daily"], dates, start_idx=begin, end_idx=end)
        paths[path_id] = loaded
    diagnostics, compact, cash_rows, events, violations, annual_rows = {}, [], [], [], [], []
    mean_base_replication = {}
    for path_id in expected+control_ids:
        arm, scenario = path_id.split("__")
        is_control = arm in CONTROLS
        loaded = paths[path_id]
        daily, orders, trace = loaded["daily"], loaded["orders"], loaded["trace"]
        whole, post = audit.performance_window(daily), audit.performance_window(daily, start_idx=post_idx)
        years = whole["days"]/audit.YEAR_DAYS
        nav_at_execution = daily.set_index("date").nav_open.loc[orders.date].to_numpy()
        whole.update(orders=len(orders), costs=float(orders.cost.sum()), trading_days=int(orders.date.nunique()),
            instructions=len(loaded["instructions"]), trading_days_per_year=float(orders.date.nunique()/years),
            two_sided_turnover_per_year=float((orders.notional.to_numpy()/nav_at_execution).sum()/years))
        matrix = prior_scores if is_control else scores
        recorded = matrix.loc[matrix.path_id == path_id].iloc[0].to_dict()
        parity = dict(metrics_whole=audit.metric_parity(whole, loaded["native"]),
            metrics_post=audit.metric_parity(post, loaded["native"], prefix="post_"),
            scores_whole=audit.metric_parity(whole, recorded),
            scores_post=audit.metric_parity(post, recorded, prefix="post_"))
        base = paths[f"BASE__{scenario}"]["daily"]
        warmup = None if is_control else audit.warmup_replication(base, daily, ready_idx=ready)
        actions, event_table = audit.intervention_summary(trace, orders, last_idx=end)
        held, issue_table = audit.held_mark_audit(daily, orders, panel)
        spells = cash_spell_context(audit.cash_spells(daily), daily, base)
        trace_summary = audit.trace_diagnostics(trace, ready_idx=ready)
        comparisons = {}
        if not is_control:
            for reference in CONTROLS+(arm.removesuffix("_ROTATION"),):
                ref_path_id = f"{reference}__{scenario}"
                reference_file = prior / ref_path_id / "DAILY.csv.gz"
                reference_daily = paths[ref_path_id]["daily"] if ref_path_id in paths else audit._read_csv(reference_file)
                hashes[str(reference_file)] = audit._sha256(reference_file)
                comparisons[f"OLC111_{reference}"] = dict(
                    whole=compare_accounts(daily, reference_daily),
                    post=compare_accounts(daily, reference_daily, start_idx=post_idx))
        if arm == "MEAN_ROTATION":
            mean_base_replication[scenario] = audit.warmup_replication(base, daily, ready_idx=end)
            base_orders = paths[f"BASE__{scenario}"]["orders"]
            mean_base_replication[scenario].update(order_ledger_exact_match=orders.equals(base_orders),
                order_rows=len(orders), base_order_rows=len(base_orders))
        diagnostics[path_id] = dict(arm=arm, scenario=scenario, source_study="OLC111" if is_control else "OLC112",
            whole=whole, post=post, metric_parity=parity, warmup_against_same_scenario_base=warmup,
            interventions=actions, held_marks=held, cash_spells=spells,
            longest_cash_spell_sessions=max((row["cash_sessions"] for row in spells), default=0),
            trace=trace_summary, comparisons=comparisons, promotion_eligible=False)
        compact.append(dict(path_id=path_id, source_study="OLC111" if is_control else "OLC112", arm=arm, scenario=scenario,
            cagr=whole["cagr"], sampled_maxdd=whole["maxdd_sampled"], end_equity=whole["end_equity"],
            post_cagr=post["cagr"], post_sampled_maxdd=post["maxdd_sampled"],
            post_anchor_nav=post["initial_nav"], post_anchor_date=post["anchor_date"], post_start_date=post["start_date"],
            mean_exposure=whole["mean_exposure"], post_mean_exposure=post["mean_exposure"], full_cash_days=whole["full_cash_days"],
            longest_cash_spell_sessions=max((row["cash_sessions"] for row in spells), default=0),
            orders=whole["orders"], costs=whole["costs"],
            two_sided_turnover_per_year=whole["two_sided_turnover_per_year"],
            **{f"{head.lower()}_filled_instructions": actions[head]["realized_instructions"] for head in audit.ACTIONS},
            **{f"{head.lower()}_separated_completed21": actions[head]["separated_completed21_episodes"] for head in audit.ACTIONS},
            max_continuous_holding_age_sessions=held["max_continuous_holding_age_sessions"],
            max_source_age_calendar_days=held["max_source_age_calendar_days"],
            stale_held_asset_closes=held["stale_held_asset_closes"], valuation_support_pass=held["valuation_support_pass"],
            ledger_reconciliation_pass=held["ledger_reconciliation_pass"],
            max_nav_reconstruction_error=held["max_nav_reconstruction_error"],
            whole_post_metric_parity=all(row["pass_all"] for row in parity.values()),
            exact_learned_warmup=None if warmup is None else warmup["exact_match"]))
        for frame, destination in ((event_table, events), (issue_table, violations)):
            frame.insert(0, "path_id", path_id)
            destination.append(frame)
        cash_rows.extend(dict(path_id=path_id, **spell) for spell in spells)
        years_in_path = pd.to_datetime(daily.date).dt.year
        for year in sorted(years_in_path.unique()):
            indices = daily.loc[years_in_path == year, "k"]
            metrics = audit.performance_window(daily, start_idx=int(indices.min()), end_idx=int(indices.max()))
            annual_rows.append(dict(path_id=path_id, year=int(year), annual_return=metrics["cumulative"],
                log_growth=metrics["log_growth"], sampled_maxdd_in_year=metrics["maxdd_sampled"],
                initial_nav=metrics["initial_nav"], end_equity=metrics["end_equity"],
                start_date=metrics["start_date"], end_date=metrics["end_date"]))
    checks = dict(complete12_new_paths_and6_existing_controls=True, unchanged_frozen_inputs_and_models=not freeze_mismatches,
        identical_complete_daily_calendars=True,
        whole_post_metric_parity=all(row["pass_all"] for path in diagnostics.values() for row in path["metric_parity"].values()),
        exact_warmup_all12_learned_paths=all(path["warmup_against_same_scenario_base"]["exact_match"]
            for path in diagnostics.values() if path["warmup_against_same_scenario_base"] is not None),
        mean_rotation_exact_base_replication_all_scenarios=all(row["exact_match"] and row["order_ledger_exact_match"]
            for row in mean_base_replication.values()),
        account_reconstruction_all18_paths=all(path["held_marks"]["ledger_reconciliation_pass"] for path in diagnostics.values()),
        held_quote_support_all18_paths=all(path["held_marks"]["valuation_support_pass"] for path in diagnostics.values()))
    report = dict(study="OLC112", audit="independent_results_only_v1", readiness=readiness, checks=checks,
        paths=diagnostics, mean_base_replication=mean_base_replication, source_sha256=hashes,
        primary_arm="PRICE_ROTATION", adaptive_after_olc111=True, pristine_holdout=False,
        performance_modified=False, new_financial_paths_run=False, models_refit=False, discovered_alpha=False,
        promotion_eligible=False,
        conclusion="Primary PRICE_ROTATION fails to improve BASE. TERM_ROTATION is a secondary historical tradeoff, not a validated promotion.",
        limitations=["This single mechanism ablation was designed after viewing OLC111 outcomes.",
            "The OLC111 forecast information test remains negative and is not replaced by this account comparison.",
            "Contemporaneous BASE returns during cash spells are descriptive comparisons, not causal alpha attribution.",
            "Completed separated action counts establish temporal support only; none of these counts creates independent validation.",
            "Native panel catalog, survivorship, adjustment-vintage and Open-executability limitations remain."])
    (results / "INDEPENDENT_DIAGNOSTICS.json").write_text(json.dumps(audit._jsonable(report), indent=2, allow_nan=False)+"\n")
    pd.DataFrame(compact).to_csv(results / "INDEPENDENT_SCORES.csv", index=False)
    pd.DataFrame(cash_rows).to_csv(results / "INDEPENDENT_CASH_SPELLS.csv", index=False)
    pd.DataFrame(cash_rows)[["path_id", "start_date", "last_cash_close_date", "cash_sessions",
        "base_preceding_close_anchor_date", "base_return_preceding_close_to_last_cash_close",
        "base_return_first_to_last_cash_close", "comparison_is_causal_alpha",
        "preceding_close_window_includes_liquidation_day"]].to_csv(results / "INDEPENDENT_CASH_CONTEXT.csv", index=False)
    nonempty_events = [frame for frame in events if len(frame)]
    (pd.concat(nonempty_events, ignore_index=True) if nonempty_events else events[0]).to_csv(results / "INDEPENDENT_INTERVENTIONS.csv", index=False)
    pd.concat(violations, ignore_index=True).to_csv(results / "INDEPENDENT_HELD_MARK_VIOLATIONS.csv.gz", index=False,
        compression={"method": "gzip", "mtime": 0})
    pd.DataFrame(annual_rows).to_csv(results / "INDEPENDENT_ANNUAL_RETURNS.csv", index=False)
    audit.plot_primary(paths, readiness, results / "INDEPENDENT_PRIMARY_POSTWARMUP.png", postwarmup=True,
        arms=("BASE", "STATIC_75", "PRICE_ROTATION", "TERM_ROTATION"), study="OLC112", locale="it")
    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=ROOT)
    arguments = parser.parse_args()
    report = run_audit(arguments.root)
    print(json.dumps(dict(checks=report["checks"], primary_arm=report["primary_arm"],
                          discovered_alpha=report["discovered_alpha"], promotion_eligible=False), indent=2))
    if not all(report["checks"].values()):
        raise SystemExit(1)
