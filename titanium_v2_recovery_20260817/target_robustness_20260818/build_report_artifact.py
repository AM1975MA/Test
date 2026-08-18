#!/usr/bin/env python3
"""Build the canonical Data Analytics report artifact for Sites publishing."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd


def records(frame: pd.DataFrame) -> list[dict]:
    return json.loads(frame.to_json(orient="records"))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--artifact", type=Path, required=True)
    args = parser.parse_args()
    generated = datetime.now(timezone.utc).isoformat()
    scenario = pd.read_csv(args.output_dir / "ROBUSTNESS_SCENARIO_SCORECARD.csv")
    family = pd.read_csv(args.output_dir / "ROBUSTNESS_FAMILY_SCORECARD.csv")
    decision = pd.read_csv(args.output_dir / "ROBUSTNESS_DECISION_SCORECARD.csv")
    stress_family = family.loc[family["family"].ne("control")].copy()
    weakness = scenario.loc[
        scenario["variant"].ne("BASELINE_21") & scenario["cagr_delta_vs_baseline_pp"].lt(0),
        ["scenario", "family", "variant", "cagr_delta_vs_baseline_pp", "maxdd_delta_vs_baseline_pp", "basket_top1_agreement"],
    ].sort_values("cagr_delta_vs_baseline_pp")
    source = {
        "id": "robustness_matrix",
        "label": "Titanium target robustness matrix",
        "path": "target_robustness_20260818/outputs/ROBUSTNESS_SCENARIO_SCORECARD.csv",
        "query": {
            "description": "Controlled retraining and live-availability stress matrix on 500 official Titanium baskets.",
            "language": "sql",
            "engine": "duckdb",
            "sql": (
                "SELECT family, variant, COUNT(DISTINCT scenario) AS scenarios, "
                "AVG(cagr_delta_vs_baseline_pp) AS cagr_gap_mean_pp, "
                "MIN(cagr_delta_vs_baseline_pp) AS cagr_gap_worst_pp, "
                "AVG(maxdd_delta_vs_baseline_pp) AS maxdd_gap_mean_pp, "
                "AVG(sharpe_delta_vs_baseline) AS sharpe_gap_mean "
                "FROM read_csv_auto('ROBUSTNESS_SCENARIO_SCORECARD.csv') "
                "WHERE variant <> 'BASELINE_21' AND family <> 'control' "
                "GROUP BY family, variant ORDER BY family, variant"
            ),
            "executed_at": generated,
            "tables_used": [
                "ROBUSTNESS_SCENARIO_SCORECARD.csv",
                "ROBUSTNESS_BASKET_METRICS.csv.gz",
                "ROBUSTNESS_FAMILY_SCORECARD.csv",
            ],
            "filters": [
                "Official 500 baskets",
                "113 signal dates",
                "Daily path through 2026-07-01",
                "Target weights and downstream strategy rules frozen",
            ],
            "metric_definitions": {
                "CAGR gap": "Candidate mean basket CAGR minus BASELINE_21 mean basket CAGR within the same stress state, in percentage points.",
                "MaxDD gap": "Candidate mean basket maximum drawdown minus BASELINE_21; positive values are improvements.",
                "Top-1 agreement": "Share of official basket-date decisions whose top-ranked ticker matches the target's canonical fit.",
            },
        },
    }
    manifest = {
        "version": 1,
        "surface": "report",
        "title": "Titanium target robustness",
        "description": "Decision report for the Compact target redesign under live retraining stress.",
        "generatedAt": generated,
        "sources": [source],
        "blocks": [
            {"id": "title", "type": "markdown", "body": "# Titanium target robustness"},
            {
                "id": "technical-summary",
                "type": "markdown",
                "body": (
                    "## Technical summary\n\n"
                    "**`CONSENSUS_MULTI` is the stronger target challenger, but a target-only change does not solve live instability.** "
                    "Across 17 actual stress states it beats the paired 21-day baseline in 14 (82.4%). Giving each stress family equal weight, "
                    "it adds 1.26 percentage points of CAGR, improves mean MaxDD by 4.64 pp, and adds 0.067 Sharpe. "
                    "However, mean top-1 agreement is only 72.5% and the worst case is 37.0%, essentially no better than the baseline under the same perturbations."
                ),
                "source": source,
            },
            {
                "id": "decision-section",
                "type": "markdown",
                "body": (
                    "## The target improves economics, not decision stability\n\n"
                    "`CONSENSUS_MULTI` leads `MULTI_45_35_20` on stress win rate, family-balanced return, drawdown and Sharpe. "
                    "Its worst paired CAGR gap remains -2.94 pp, so it fails a reasonable production worst-case gate. "
                    "The result supports keeping it as a challenger, not promoting it directly to live."
                ),
                "source": source,
            },
            {"id": "decision-table-block", "type": "table", "tableId": "decision-table"},
            {
                "id": "family-section",
                "type": "markdown",
                "body": (
                    "## Rolling windows remain the failure mode\n\n"
                    "The multi-horizon targets are robust to simulated feature-vintage noise and ticker dropout, while the rolling-window family is negative on average. "
                    "The 5-year window is the clearest failure: `CONSENSUS_MULTI` loses 2.94 pp of CAGR and worsens drawdown. "
                    "Cutoff timing also matters: December is negative, February positive, and quarterly refitting strongly favors `CONSENSUS_MULTI`."
                ),
                "source": source,
            },
            {"id": "family-chart-block", "type": "chart", "chartId": "family-cagr-gap"},
            {
                "id": "weakness-section",
                "type": "markdown",
                "body": (
                    "## Negative states prevent production promotion\n\n"
                    "The table lists every state in which a candidate loses to the paired baseline. These are not discarded outliers; they define the present production risk."
                ),
                "source": source,
            },
            {"id": "weakness-table-block", "type": "table", "tableId": "weakness-table"},
            {
                "id": "scope-section",
                "type": "markdown",
                "body": (
                    "## Scope, definitions and validation\n\n"
                    "The matrix uses 18 controlled states, 500 official baskets, 113 signal dates and 2,366 daily observations per state. "
                    "Target weights, 125 features, XGBRanker parameters, three seeds, TailMix, macro layer, 70/30 blend, baskets, governor, costs, allocation rule, labels and evaluation OHLC stay fixed. "
                    "The exact control has maximum score delta 0 and 100% decision agreement. Independent QA reconciles all scenario metrics to basket paths."
                ),
                "source": source,
            },
            {
                "id": "limitations-section",
                "type": "markdown",
                "body": (
                    "## Limitations and next step\n\n"
                    "The stress states are structured sensitivities, not independent statistical draws; baskets overlap; and price-vintage stress is feature noise rather than a second vendor snapshot. "
                    "Next, preregister temporal rank ensembling across staggered cutoffs and longer admissible windows, then require cross-fit agreement before switching the live top-1. "
                    "Do not retune target weights on the already inspected 2017-2026 history."
                ),
            },
        ],
        "charts": [
            {
                "id": "family-cagr-gap",
                "title": "Mean CAGR gap versus baseline by stress family",
                "description": "Five stress families; percentage-point gap, equal weight within each family.",
                "type": "bar",
                "dataset": "family_gaps",
                "encodings": {
                    "x": {"field": "family", "type": "nominal", "title": "Stress family"},
                    "y": {"field": "cagr_gap_mean_pp", "type": "quantitative", "title": "CAGR gap (pp)"},
                    "color": {"field": "variant", "type": "nominal", "title": "Target"},
                },
                "options": {"grouping": "grouped", "legend": {"show": True}},
                "source": source,
            }
        ],
        "tables": [
            {
                "id": "decision-table",
                "title": "Stress decision scorecard",
                "description": "17 actual stress states; the exact control is excluded.",
                "dataset": "decision_scorecard",
                "columns": [
                    {"field": "variant", "label": "Target"},
                    {"field": "stress_wins", "label": "Wins"},
                    {"field": "stress_scenarios", "label": "States"},
                    {"field": "stress_win_rate", "label": "Win rate", "format": "percent"},
                    {"field": "family_balanced_cagr_gap_pp", "label": "CAGR gap (pp)", "format": "number", "movement": True},
                    {"field": "family_balanced_maxdd_gap_pp", "label": "MaxDD gap (pp)", "format": "number", "movement": True},
                    {"field": "family_balanced_sharpe_gap", "label": "Sharpe gap", "format": "number", "movement": True},
                    {"field": "top1_agreement_mean", "label": "Top-1 agreement", "format": "percent"},
                    {"field": "top1_agreement_worst", "label": "Worst top-1", "format": "percent"},
                ],
                "defaultSort": {"field": "family_balanced_cagr_gap_pp", "direction": "desc"},
                "source": source,
            },
            {
                "id": "weakness-table",
                "title": "Candidate losses versus paired baseline",
                "description": "All negative CAGR-gap states; positive MaxDD gap means smaller drawdown.",
                "dataset": "negative_states",
                "columns": [
                    {"field": "scenario", "label": "Scenario"},
                    {"field": "family", "label": "Family"},
                    {"field": "variant", "label": "Target"},
                    {"field": "cagr_delta_vs_baseline_pp", "label": "CAGR gap (pp)", "format": "number", "movement": True},
                    {"field": "maxdd_delta_vs_baseline_pp", "label": "MaxDD gap (pp)", "format": "number", "movement": True},
                    {"field": "basket_top1_agreement", "label": "Top-1 agreement", "format": "percent"},
                ],
                "defaultSort": {"field": "cagr_delta_vs_baseline_pp", "direction": "asc"},
                "source": source,
            },
        ],
    }
    artifact = {
        "surface": "report",
        "manifest": manifest,
        "snapshot": {
            "version": 1,
            "status": "ready",
            "generatedAt": generated,
            "datasets": {
                "family_gaps": records(stress_family),
                "decision_scorecard": records(decision),
                "negative_states": records(weakness),
            },
        },
        "sources": [source],
        "package_info": {"report_kind": "technical", "snapshot_note": "Published snapshot, not a live connector."},
    }
    args.artifact.parent.mkdir(parents=True, exist_ok=True)
    args.artifact.write_text(json.dumps(artifact, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"status": "PASS", "artifact": str(args.artifact), "datasets": {key: len(value) for key, value in artifact["snapshot"]["datasets"].items()}}))


if __name__ == "__main__":
    main()
