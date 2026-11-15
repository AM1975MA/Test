"""Independently replay the matched-state branches without production imports."""
from pathlib import Path
import hashlib
import json
import numpy as np
import pandas as pd
from account_reference import prepare_panel, expected_execution


def replay(panel, units, cash, target, signal, terminal, lag, forced, prior):
    held = np.array(units, dtype=float, copy=True)
    available = float(cash)
    due, pending, costs, count = signal + 1 + lag, True, 0., 0
    grouped = {int(k): rows for k, rows in prior.groupby("execution_idx")}
    for day in range(signal + 1, terminal + 1):
        if day < due:
            for trade in grouped.get(day, pd.DataFrame()).itertuples(index=False):
                assert trade.signal_idx < signal and trade.due_idx <= day
                j = int(trade.j)
                if trade.side == "BUY":
                    held[j] += trade.quantity
                    available -= trade.notional + trade.cost
                else:
                    assert trade.side == "SELL"
                    held[j] -= trade.quantity
                    available += trade.notional - trade.cost
                costs += trade.cost
                count += 1
            held = np.maximum(held, 0.)
            available = max(available, 0.)
            continue
        if not pending:
            continue
        opening = np.where(panel["valid_o"][day], panel["O"][day], np.nan)
        marks = np.where(np.isfinite(opening), opening, panel["C"][day - 1])
        unavailable = ((held > 1e-10) | (target > 0)) & ~np.isfinite(opening)
        trades = expected_execution(held, available, opening, marks, target, 1., .0015, forced)
        for trade in trades:
            j = trade["j"]
            assert day >= due and panel["valid_o"][day, j]
            if trade["side"] == "BUY":
                held[j] += trade["quantity"]
                available -= trade["notional"] + trade["cost"]
            else:
                held[j] -= trade["quantity"]
                available += trade["notional"] - trade["cost"]
            costs += trade["cost"]
            count += 1
        held = np.maximum(held, 0.)
        available = max(available, 0.)
        pending = bool(unavailable.any())
    terminal_nav = float(available + np.nansum(held * panel["C"][terminal]))
    return terminal_nav, float(costs), int(count)


def run(root):
    root = Path(root)
    with np.load(root / "source/data/XETRA_EUR_ETF.npz", allow_pickle=False) as z:
        panel = prepare_panel({key: z[key] for key in z.files})
    rows = pd.read_csv(root / "analysis/MATCHED_STATE_INTERVALS.csv", float_precision="round_trip")
    assert len(rows) == 160 and set(rows.scenario) == {"BASE", "LAG2"}
    checks, maxima = [], dict(nav_error=0., cost_error=0., bps_error=0., start_nav_error=0.)
    for scenario, lag in (("BASE", 0), ("LAG2", 2)):
        actual_path = root / "results_stage2" / f"DEDUP_DUAL_TREND_OPP__{scenario}"
        control_path = root / "results_stage2" / f"DEDUP_DUAL21__{scenario}"
        with np.load(actual_path / "DECISIONS.npz", allow_pickle=False) as z:
            actual = {key: z[key] for key in z.files}
        with np.load(control_path / "DECISIONS.npz", allow_pickle=False) as z:
            control = {int(k): z["raw_weights"][i].copy() for i, k in enumerate(z["k"])}
        orders = pd.read_csv(actual_path / "ORDERS.csv.gz", float_precision="round_trip")
        published = rows[rows.scenario == scenario].set_index("signal_idx")
        assert len(published) == 80
        for i, signal in enumerate(actual["k"]):
            signal = int(signal)
            row = published.loc[signal]
            terminal = int(row.end_idx)
            if i + 1 < len(actual["k"]):
                assert terminal == int(actual["k"][i + 1])
            else:
                assert terminal == len(panel["dates"]) - 1
            units, cash = actual["units"][i], float(actual["cash"][i])
            start_nav = float(cash + np.nansum(units * panel["C"][signal]))
            maxima["start_nav_error"] = max(maxima["start_nav_error"], abs(start_nav - row.start_nav))
            assert np.isclose(start_nav, row.start_nav, rtol=0, atol=1e-8)
            assert bool(row.targets_differ) == bool(np.any(actual["raw_weights"][i] != control[signal]))
            prior = orders[(orders.execution_idx > signal) & (orders.execution_idx < signal + 1 + lag)]
            assert len(prior) == row.prior_common_orders
            actual_nav, actual_cost, _ = replay(panel, units, cash, actual["raw_weights"][i], signal, terminal, lag, i == 0, prior)
            control_nav, control_cost, _ = replay(panel, units, cash, control[signal], signal, terminal, lag, i == 0, prior)
            for calculated, reported, kind in ((actual_nav, row.actual_terminal_nav, "nav_error"),
                                                (control_nav, row.control_terminal_nav, "nav_error"),
                                                (actual_cost, row.actual_costs, "cost_error"),
                                                (control_cost, row.control_costs, "cost_error")):
                error = abs(calculated - reported)
                assert error < 1e-6, ("INDEPENDENT_MATCHED_REPLAY", scenario, signal, kind, calculated, reported)
                maxima[kind] = max(maxima[kind], error)
            bps = 10000 * (actual_nav - control_nav) / start_nav
            error = abs(bps - row.increment_bps)
            assert error < 1e-6
            maxima["bps_error"] = max(maxima["bps_error"], error)
            checks.append(dict(scenario=scenario, signal_idx=signal, targets_differ=bool(row.targets_differ),
                               actual_terminal_nav=actual_nav, control_terminal_nav=control_nav,
                               increment_bps=bps, prior_common_orders=len(prior)))
    checked = pd.DataFrame(checks)
    summaries = []
    for scenario, group in checked.groupby("scenario"):
        changed = group[group.targets_differ]
        delta = changed.increment_bps.to_numpy()
        summaries.append(dict(scenario=scenario, intervals=len(group), changed_intervals=len(changed),
                              wins=int((delta > 1e-8).sum()), losses=int((delta < -1e-8).sum()),
                              ties=int((np.abs(delta) <= 1e-8).sum()), mean_increment_bps=float(delta.mean()),
                              median_increment_bps=float(np.median(delta))))
    result = dict(status="PASS_INDEPENDENT_MATCHED_STATE_REPLAY", intervals=160, branch_replays=320,
                  counterfactual_compounding=False, imports_production_code=False,
                  target_source="Frozen raw target vectors from independently audited DEDUP_DUAL_TREND_OPP and DEDUP_DUAL21 decisions.",
                  starting_state="Actual candidate units and cash are restored separately for every interval and both branches.",
                  independently_derived_trade_sizes=True, common_prior_fills=int(checked.prior_common_orders.sum()),
                  maximum_errors=maxima, changed_interval_summaries=summaries,
                  interpretation=[
                      "Positive increments mean candidate outperformance of the no-gate branch; they are not counts of profitable trades.",
                      "Each bps difference uses the same actual signal-close NAV as denominator.",
                      "Intervals end at the next decision Close before that decision becomes executable.",
                      "No pre-due pending fills occurred in these data; the handling is logically correct but that branch is not empirically exercised here.",
                      "Means and medians are descriptive, not CAGR, additive annual contributions, independent observations, or a new compounded strategy.",
                      "The candidate and intervention were selected after observing the research results."] ,
                  production_script_sha256=hashlib.sha256((root / "analysis/matched_state_trend_gate.py").read_bytes()).hexdigest(),
                  protocol_sha256=hashlib.sha256((root / "analysis/MATCHED_STATE_PROTOCOL.md").read_bytes()).hexdigest())
    (root / "validation/MATCHED_STATE_REVIEW.json").write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result, indent=2))
    return result


if __name__ == "__main__":
    run(Path(__file__).resolve().parents[1])
