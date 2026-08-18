#!/usr/bin/env python3
"""Independent QA and decision summaries for the Titanium robustness matrix."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd


CANDIDATES = ("CONSENSUS_MULTI", "MULTI_45_35_20")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    score_path = args.output_dir / "ROBUSTNESS_SCENARIO_SCORECARD.csv"
    basket_path = args.output_dir / "ROBUSTNESS_BASKET_METRICS.csv.gz"
    aggregate_path = args.output_dir / "ROBUSTNESS_AGGREGATE.csv"
    score = pd.read_csv(score_path)
    baskets = pd.read_csv(basket_path)
    supplied_aggregate = pd.read_csv(aggregate_path).sort_values("variant").reset_index(drop=True)

    checks: dict[str, object] = {}
    checks["scenario_rows_18x3"] = bool(len(score) == 54)
    checks["unique_scenario_variant"] = bool(not score.duplicated(["scenario", "variant"]).any())
    checks["scenario_count_18"] = bool(score["scenario"].nunique() == 18)
    checks["variants_exact"] = bool(set(score["variant"]) == {"BASELINE_21", *CANDIDATES})
    checks["daily_observations_fixed"] = bool(score["daily_observations"].eq(2366).all())
    checks["signal_dates_fixed"] = bool(score["signal_dates"].eq(113).all())
    checks["decision_count_fixed"] = bool(score["decision_count"].eq(56500).all())
    checks["finite_headline_metrics"] = bool(
        np.isfinite(score[["cagr_mean", "maxdd_mean", "sharpe_mean"]].to_numpy(float)).all()
    )

    control = score.loc[score["scenario"].eq("CONTROL_ANNUAL_EXPANDING")]
    checks["control_three_variants"] = bool(len(control) == 3)
    checks["control_keys_exact"] = bool(control["score_keys_identical"].astype(bool).all())
    checks["control_score_delta_zero"] = bool(control["max_abs_score_delta"].abs().le(1e-15).all())
    checks["control_top1_exact"] = bool(control["basket_top1_agreement"].eq(1.0).all())
    checks["control_decision_regime_exact"] = bool(control["concentration_regime_agreement"].eq(1.0).all())

    basket_recomputed = baskets.groupby(["scenario", "variant"], as_index=False).agg(
        cagr_mean_check=("cagr", "mean"),
        maxdd_mean_check=("maxdd", "mean"),
        sharpe_mean_check=("sharpe", "mean"),
    )
    joined = score.merge(basket_recomputed, on=["scenario", "variant"], validate="one_to_one")
    checks["basket_cagr_reconciles"] = bool(
        np.allclose(joined["cagr_mean"], joined["cagr_mean_check"], atol=1e-12, rtol=0.0)
    )
    checks["basket_maxdd_reconciles"] = bool(
        np.allclose(joined["maxdd_mean"], joined["maxdd_mean_check"], atol=1e-12, rtol=0.0)
    )
    checks["basket_sharpe_reconciles"] = bool(
        np.allclose(joined["sharpe_mean"], joined["sharpe_mean_check"], atol=1e-12, rtol=0.0)
    )

    baseline = score.loc[score["variant"].eq("BASELINE_21"), ["scenario", "cagr_mean", "maxdd_mean", "sharpe_mean"]].rename(
        columns={"cagr_mean": "baseline_cagr", "maxdd_mean": "baseline_maxdd", "sharpe_mean": "baseline_sharpe"}
    )
    candidate = score.loc[score["variant"].isin(CANDIDATES)].merge(baseline, on="scenario", validate="many_to_one")
    checks["cagr_deltas_reconcile"] = bool(
        np.allclose(
            candidate["cagr_delta_vs_baseline_pp"],
            100.0 * (candidate["cagr_mean"] - candidate["baseline_cagr"]),
            atol=1e-12,
            rtol=0.0,
        )
    )
    checks["maxdd_deltas_reconcile"] = bool(
        np.allclose(
            candidate["maxdd_delta_vs_baseline_pp"],
            100.0 * (candidate["maxdd_mean"] - candidate["baseline_maxdd"]),
            atol=1e-12,
            rtol=0.0,
        )
    )

    recomputed = candidate.groupby("variant").agg(
        scenarios=("scenario", "nunique"),
        mean_cagr=("cagr_mean", "mean"),
        worst_cagr=("cagr_mean", "min"),
        mean_cagr_delta_vs_baseline_pp=("cagr_delta_vs_baseline_pp", "mean"),
        worst_cagr_delta_vs_baseline_pp=("cagr_delta_vs_baseline_pp", "min"),
        scenarios_beating_baseline=("cagr_delta_vs_baseline_pp", lambda values: int(values.gt(0.0).sum())),
        mean_maxdd=("maxdd_mean", "mean"),
        worst_maxdd=("maxdd_mean", "min"),
        mean_sharpe=("sharpe_mean", "mean"),
        worst_sharpe=("sharpe_mean", "min"),
        mean_score_correlation=("monthly_score_rank_correlation", "mean"),
        worst_score_correlation=("monthly_score_rank_correlation", "min"),
        mean_basket_top1_agreement=("basket_top1_agreement", "mean"),
        worst_basket_top1_agreement=("basket_top1_agreement", "min"),
        mean_fraction_baskets_beating_baseline=("fraction_baskets_beating_baseline", "mean"),
    ).reset_index()
    recomputed["scenario_win_rate_vs_baseline"] = recomputed["scenarios_beating_baseline"] / recomputed["scenarios"]
    numeric_columns = [column for column in supplied_aggregate.columns if column != "variant"]
    recomputed = recomputed[supplied_aggregate.columns].sort_values("variant").reset_index(drop=True)
    checks["aggregate_reconciles"] = bool(
        supplied_aggregate["variant"].equals(recomputed["variant"])
        and np.allclose(supplied_aggregate[numeric_columns], recomputed[numeric_columns], atol=1e-12, rtol=0.0)
    )

    family = candidate.groupby(["variant", "family"], as_index=False).agg(
        scenarios=("scenario", "nunique"),
        cagr_gap_mean_pp=("cagr_delta_vs_baseline_pp", "mean"),
        cagr_gap_worst_pp=("cagr_delta_vs_baseline_pp", "min"),
        cagr_win_rate=("cagr_delta_vs_baseline_pp", lambda values: float(values.gt(0.0).mean())),
        maxdd_gap_mean_pp=("maxdd_delta_vs_baseline_pp", "mean"),
        sharpe_gap_mean=("sharpe_delta_vs_baseline", "mean"),
        top1_agreement_mean=("basket_top1_agreement", "mean"),
        baskets_beating_baseline_mean=("fraction_baskets_beating_baseline", "mean"),
    )
    family.to_csv(args.output_dir / "ROBUSTNESS_FAMILY_SCORECARD.csv", index=False)

    stress = candidate.loc[candidate["family"].ne("control")]
    stress_summary = stress.groupby("variant").agg(
        stress_scenarios=("scenario", "nunique"),
        stress_wins=("cagr_delta_vs_baseline_pp", lambda values: int(values.gt(0.0).sum())),
        cagr_gap_mean_pp=("cagr_delta_vs_baseline_pp", "mean"),
        cagr_gap_median_pp=("cagr_delta_vs_baseline_pp", "median"),
        cagr_gap_worst_pp=("cagr_delta_vs_baseline_pp", "min"),
        drawdown_improvement_scenarios=("maxdd_delta_vs_baseline_pp", lambda values: int(values.gt(0.0).sum())),
        sharpe_improvement_scenarios=("sharpe_delta_vs_baseline", lambda values: int(values.gt(0.0).sum())),
        top1_agreement_mean=("basket_top1_agreement", "mean"),
        top1_agreement_worst=("basket_top1_agreement", "min"),
    ).reset_index()
    stress_summary["stress_win_rate"] = stress_summary["stress_wins"] / stress_summary["stress_scenarios"]
    family_stress = family.loc[family["family"].ne("control")]
    balanced = family_stress.groupby("variant").agg(
        stress_families=("family", "nunique"),
        family_balanced_cagr_gap_pp=("cagr_gap_mean_pp", "mean"),
        family_balanced_maxdd_gap_pp=("maxdd_gap_mean_pp", "mean"),
        family_balanced_sharpe_gap=("sharpe_gap_mean", "mean"),
    ).reset_index()
    decision = stress_summary.merge(balanced, on="variant", validate="one_to_one")
    decision.to_csv(args.output_dir / "ROBUSTNESS_DECISION_SCORECARD.csv", index=False)

    checks["all_checks_pass"] = bool(all(bool(value) for value in checks.values()))
    report = {
        "status": "PASS" if checks["all_checks_pass"] else "FAIL",
        "checks": checks,
        "decision_scorecard": decision.to_dict(orient="records"),
        "interpretation": {
            "economic_robustness": "CONSENSUS_MULTI leads the stress matrix on win rate, family-balanced CAGR gap, drawdown and Sharpe.",
            "selection_stability": "Neither changed target materially stabilizes top-1 choices versus BASELINE_21; rolling windows are the weakest family.",
            "production_gate": "Do not promote a target-only change as the final solution. Carry CONSENSUS_MULTI into temporal ensembling and explicit stability regularization tests.",
        },
        "limitations": [
            "The 18 stress states are structured sensitivity cases, not independent statistical draws.",
            "Ticker baskets overlap, so basket counts are not independent observations.",
            "Price-vintage stress uses feature noise rather than a second vendor snapshot.",
            "The same historical interval has now informed model selection; no further target-weight tuning should use it.",
        ],
    }
    (args.output_dir / "ROBUSTNESS_VALIDATION_REPORT.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
