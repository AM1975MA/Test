"""Descriptive OLC110 comparisons; never changes or reruns a financial path.

The circular monthly block resampling is conditional on this already observed,
adaptively designed sample. It is not an untouched holdout or a correction for
model selection. The statistic is annualized mean log relative return, not a
difference between the published calendar-day CAGRs.
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "analysis"
ARMS = json.loads((ROOT / "docs/EXPERIMENT_FREEZE.json").read_text())["arms"]
SCENARIOS = ["BASE", "ZERO_COST", "DOUBLE_COST", "LAG1", "LAG2", "NEXT_CLOSE"]
CONTRASTS = [
    ("STATIC_HALF", "BASE", "Riduzione permanente al 50%"),
    ("STATIC_75", "BASE", "Riduzione permanente al 75%"),
    ("REFRESH_WEEKLY", "BASE", "Ranking settimanale"),
    ("EXIT21_MONTHLY", "BASE", "Uscita breve e attesa mensile"),
    ("EXIT21_SLOW", "EXIT21_MONTHLY", "Rientro lento anche inframese"),
    ("EXIT21_FAST", "EXIT21_SLOW", "Rientro veloce pieno"),
    ("EXIT21_STAGED", "EXIT21_FAST", "Rientro veloce graduale"),
    ("EXIT63_STAGED", "EXIT21_STAGED", "Uscita più lenta"),
    ("TRAIL15_STAGED", "EXIT21_STAGED", "Uscita da massimo precedente"),
    ("VOLTRAIL_STAGED", "TRAIL15_STAGED", "Soglia legata alla volatilità"),
    ("EXIT21_STAGED_FRESHW", "EXIT21_STAGED", "Opportunità nuove settimanali"),
    ("EXIT21_STAGED_FRESHD", "EXIT21_STAGED_FRESHW", "Opportunità nuove giornaliere"),
    ("EXIT21_STAGED_FRESHW", "BASE", "Ipotesi primaria contro OLC109"),
]


def main() -> None:
    score = pd.read_csv(ROOT / "results/SCORECARD.csv", float_precision="round_trip")
    annual = pd.read_csv(ROOT / "results/ANNUAL_RETURNS.csv", float_precision="round_trip")
    assert len(score) == 78 and not score[["arm", "scenario"]].duplicated().any()
    assert set(score.arm) == set(ARMS) and set(score.scenario) == set(SCENARIOS)
    assert len(annual) == 546 and len(annual[annual.year == 2024]) == 78
    indexed = score.set_index(["arm", "scenario"])
    monthly = {}
    monthly_rows = []
    for arm in ARMS:
        for scenario in SCENARIOS:
            daily = pd.read_csv(ROOT / f"results/{arm}__{scenario}/DAILY.csv.gz",
                                parse_dates=["date"], float_precision="round_trip")
            end = daily.set_index("date").nav_close.resample("ME").last()
            assert len(end) == 80 and end.notna().all() and (end > 0).all()
            log_returns = np.diff(np.log(np.r_[10000.0, end.to_numpy()]))
            expected_total = np.log(indexed.loc[(arm, scenario), "end_equity"] / 10000.0)
            assert abs(log_returns.sum() - expected_total) < 1e-12
            monthly[arm, scenario] = log_returns
            for date, log_return in zip(end.index, log_returns):
                monthly_rows.append({"arm": arm, "scenario": scenario,
                                     "month": str(date.date()),
                                     "log_return": float(log_return),
                                     "simple_return": float(np.expm1(log_return))})
    pd.DataFrame(monthly_rows).to_csv(OUT / "MONTHLY_RETURNS.csv", index=False)

    # Same resampled dates for each arm in each paired comparison.
    seed, draws, block, n = 110, 10000, 6, 80
    rng = np.random.default_rng(seed)
    starts = rng.integers(0, n, size=(draws, int(np.ceil(n / block))))
    samples = ((starts[..., None] + np.arange(block)) % n).reshape(draws, -1)[:, :n]
    rows = []
    for candidate, control, description in CONTRASTS:
        for scenario in SCENARIOS:
            a, b = indexed.loc[(candidate, scenario)], indexed.loc[(control, scenario)]
            relative_logs = monthly[candidate, scenario] - monthly[control, scenario]
            statistic = 12 * relative_logs.mean()
            resampled = 12 * relative_logs[samples].mean(axis=1)
            low, high = np.quantile(resampled, [0.025, 0.975])
            rows.append({
                "candidate": candidate, "control": control, "scenario": scenario,
                "description": description,
                "delta_cagr_pp": 100 * (a.cagr - b.cagr),
                "delta_dd_pp_positive_is_improvement": 100 * (a.maxdd_sampled - b.maxdd_sampled),
                "delta_mean_exposure_pp": 100 * (a.mean_exposure - b.mean_exposure),
                "annualized_mean_log_relative_pct": 100 * statistic,
                "descriptive_ci_2_5_log_pct": 100 * low,
                "descriptive_ci_97_5_log_pct": 100 * high,
                "resampled_fraction_positive_not_p_value": float((resampled > 0).mean()),
                "months": n, "block_months": block, "resamples": draws, "seed": seed,
            })
    comparisons = pd.DataFrame(rows)
    comparisons.to_csv(OUT / "PAIRED_COMPARISONS.csv", index=False)

    dominance = []
    for scenario in SCENARIOS:
        for arm in ARMS[4:]:
            row = indexed.loc[(arm, scenario)]
            for control in ["BASE", "STATIC_HALF", "STATIC_75"]:
                other = indexed.loc[(control, scenario)]
                dominated = bool(other.cagr >= row.cagr and
                                 other.maxdd_sampled >= row.maxdd_sampled and
                                 (other.cagr > row.cagr or other.maxdd_sampled > row.maxdd_sampled))
                dominance.append({"arm": arm, "scenario": scenario, "control": control,
                                  "dominated_on_cagr_and_sampled_dd": dominated,
                                  "control_minus_arm_cagr_pp": 100 * (other.cagr - row.cagr),
                                  "control_minus_arm_dd_pp": 100 * (other.maxdd_sampled - row.maxdd_sampled)})
    dominance = pd.DataFrame(dominance)
    dominance.to_csv(OUT / "CONTROL_DOMINANCE.csv", index=False)

    cost_rows = []
    for arm in ARMS:
        base, zero, double = (indexed.loc[(arm, x)] for x in ["BASE", "ZERO_COST", "DOUBLE_COST"])
        cost_rows.append({"arm": arm, "zero_minus_base_cagr_pp": 100 * (zero.cagr - base.cagr),
                          "base_minus_double_cagr_pp": 100 * (base.cagr - double.cagr),
                          "base_total_cost_eur": base.costs, "base_end_equity_eur": base.end_equity,
                          "base_orders": int(base.orders),
                          "base_trading_days_per_year": base.trading_days_per_year,
                          "base_two_sided_turnover_per_year": base.two_sided_turnover_per_year})
    pd.DataFrame(cost_rows).to_csv(OUT / "COST_AND_ACTIVITY.csv", index=False)
    score.pivot(index="arm", columns="scenario", values="cagr").reindex(
        index=ARMS, columns=SCENARIOS).to_csv(OUT / "CAGR_BY_SCENARIO.csv")
    annual[annual.scenario == "BASE"].pivot(index="year", columns="arm", values="annual_return").reindex(
        columns=ARMS).to_csv(OUT / "ANNUAL_BASE_ALL_ARMS.csv")

    primary = comparisons[(comparisons.candidate == "EXIT21_STAGED_FRESHW") &
                          (comparisons.control == "BASE") & (comparisons.scenario == "BASE")].iloc[0]
    dynamic_base = dominance[(dominance.scenario == "BASE") & (dominance.control == "STATIC_75")]
    assert len(dynamic_base) == 9 and dynamic_base.dominated_on_cagr_and_sampled_dd.all()
    summary = {
        "status": "COMPLETE_DESCRIPTIVE_ANALYSIS",
        "paths": len(score), "configurations": len(ARMS), "scenarios": len(SCENARIOS),
        "annual_rows": len(annual), "monthly_rows": len(monthly_rows),
        "primary_hypothesis": "EXIT21_STAGED_FRESHW", "primary_improved": False,
        "any_path_reaches_30pct_cagr": bool((score.cagr >= .30).any()),
        "best_dynamic_base_arm": str(score[(score.scenario == "BASE") & score.arm.isin(ARMS[4:])]
                                      .sort_values("cagr", ascending=False).iloc[0].arm),
        "all_9_dynamic_base_arms_dominated_by_static75": True,
        "primary_base_vs_baseline": primary.to_dict(),
        "bootstrap_scope": "Conditional descriptive paired circular 6-month blocks; 80 months; 10,000 draws; no multiplicity correction; no untouched holdout.",
        "drawdown_comparison_scope": "Only within a scenario: OPEN_CLOSE for five scenarios; CLOSE_PRE_POST_COST for NEXT_CLOSE.",
        "cost_difference_scope": "Separate full account paths: CAGR differences are not a linear subtraction of total fees.",
        "new_full_financial_paths_created": 0,
    }
    (OUT / "ANALYSIS_SUMMARY.json").write_text(json.dumps(summary, indent=2, ensure_ascii=False) + "\n")
    print(json.dumps(summary, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
