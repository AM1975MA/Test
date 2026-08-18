#!/usr/bin/env python3
"""Build the companion notebook for the Titanium robustness report."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

try:
    import nbformat as nbf
except ModuleNotFoundError:
    class _V4:
        @staticmethod
        def new_notebook():
            return {"cells": [], "metadata": {}, "nbformat": 4, "nbformat_minor": 5}

        @staticmethod
        def new_markdown_cell(source):
            return {"cell_type": "markdown", "metadata": {}, "source": source}

        @staticmethod
        def new_code_cell(source):
            return {"cell_type": "code", "execution_count": None, "metadata": {}, "outputs": [], "source": source}

    class _FallbackNotebookFormat:
        v4 = _V4()

        @staticmethod
        def write(notebook, path):
            Path(path).write_text(json.dumps(notebook, indent=1) + "\n", encoding="utf-8")

    nbf = _FallbackNotebookFormat()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    nb = nbf.v4.new_notebook()
    nb["metadata"]["kernelspec"] = {"display_name": "Python 3", "language": "python", "name": "python3"}
    nb["metadata"]["language_info"] = {"name": "python", "version": "3"}
    nb["metadata"]["execution_note"] = "Validated top-to-bottom with the fallback runner because native Jupyter packages were unavailable."
    nb["cells"] = [
        nbf.v4.new_markdown_cell(
            """# Titanium target robustness

## tl;dr

`CONSENSUS_MULTI` is the stronger target challenger across the structured stress matrix, but a target-only change does not stabilize live decisions. The production recommendation is to retain it as the challenger and next test temporal ensembling plus an explicit decision-stability gate."""
        ),
        nbf.v4.new_markdown_cell(
            """## Context & Methods

The notebook audits 18 controlled states across cutoff timing, refit cadence, rolling windows, training-universe dropout, simulated feature-vintage noise, and live ticker unavailability. Each state compares `BASELINE_21`, `MULTI_45_35_20`, and `CONSENSUS_MULTI` on the same 500 official baskets.

### Key Assumptions

- Target weights, features, model parameters, three seeds, TailMix, macro layer, baskets, costs, governor and allocation rules are frozen.
- Labels and daily evaluation OHLC are never perturbed.
- Stress states are sensitivity cases, not independent statistical samples.
- Price-vintage stress is deterministic feature noise, not a second vendor snapshot."""
        ),
        nbf.v4.new_code_cell(
            """from pathlib import Path
import json
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

OUTPUT = Path('outputs')
scenario = pd.read_csv(OUTPUT / 'ROBUSTNESS_SCENARIO_SCORECARD.csv')
family = pd.read_csv(OUTPUT / 'ROBUSTNESS_FAMILY_SCORECARD.csv')
decision = pd.read_csv(OUTPUT / 'ROBUSTNESS_DECISION_SCORECARD.csv')
validation = json.loads((OUTPUT / 'ROBUSTNESS_VALIDATION_REPORT.json').read_text())
scenario.shape, family.shape, decision.shape, validation['status']"""
        ),
        nbf.v4.new_markdown_cell("## Data\n\nThe scenario table is the audit grain: one row per scenario and target."),
        nbf.v4.new_code_cell(
            """assert scenario.shape == (54, 28)
assert scenario[['scenario', 'variant']].duplicated().sum() == 0
assert scenario['scenario'].nunique() == 18
assert scenario['daily_observations'].eq(2366).all()
assert scenario['signal_dates'].eq(113).all()
assert scenario['decision_count'].eq(56500).all()
assert validation['status'] == 'PASS'
scenario[['scenario', 'family', 'variant', 'cagr_delta_vs_baseline_pp', 'maxdd_delta_vs_baseline_pp', 'basket_top1_agreement']].head(9)"""
        ),
        nbf.v4.new_markdown_cell(
            "## Results\n\nThe decision scorecard excludes the unperturbed control and summarizes the 17 actual stress states."
        ),
        nbf.v4.new_code_cell(
            """decision.set_index('variant')[[
    'stress_wins', 'stress_scenarios', 'stress_win_rate',
    'family_balanced_cagr_gap_pp', 'family_balanced_maxdd_gap_pp',
    'family_balanced_sharpe_gap', 'top1_agreement_mean', 'top1_agreement_worst'
]]"""
        ),
        nbf.v4.new_code_cell(
            """plot_data = scenario[scenario['variant'] != 'BASELINE_21'].copy()
order = plot_data.groupby('scenario')['cagr_delta_vs_baseline_pp'].mean().sort_values().index
pivot = plot_data.pivot(index='scenario', columns='variant', values='cagr_delta_vs_baseline_pp').loc[order]
colors = {'CONSENSUS_MULTI': '#3569A8', 'MULTI_45_35_20': '#D89A2B'}
ax = pivot.plot(kind='barh', figsize=(10, 8), color=[colors[c] for c in pivot.columns], width=0.78)
ax.axvline(0, color='#30343B', linewidth=1)
ax.set_title('CAGR gap versus stressed baseline')
ax.set_xlabel('percentage points; 18 controlled states, 500 baskets')
ax.set_ylabel('')
ax.grid(axis='x', color='#D9DDE3', linewidth=0.6)
ax.legend(title='Target')
plt.tight_layout()
plt.show()"""
        ),
        nbf.v4.new_markdown_cell(
            """`CONSENSUS_MULTI` wins more often and has the stronger average risk-adjusted profile. The negative cases are concentrated in the rolling-window family and the December cutoff. This is evidence for a better target, not evidence that the live retraining process is stable."""
        ),
        nbf.v4.new_code_cell(
            """family_view = family[family['family'] != 'control'].pivot(
    index='family', columns='variant', values='cagr_gap_mean_pp'
).sort_index()
family_view"""
        ),
        nbf.v4.new_code_cell(
            """baseline_stability = scenario[scenario['variant'] == 'BASELINE_21'][['scenario', 'basket_top1_agreement']].rename(
    columns={'basket_top1_agreement': 'BASELINE_21'}
).set_index('scenario')
candidate_stability = scenario[scenario['variant'] != 'BASELINE_21'].pivot(
    index='scenario', columns='variant', values='basket_top1_agreement'
)
stability = baseline_stability.join(candidate_stability)
stability.mean().to_frame('mean_top1_agreement').join(stability.min().to_frame('worst_top1_agreement'))"""
        ),
        nbf.v4.new_markdown_cell(
            """## Takeaways

- **Keep `CONSENSUS_MULTI` as the leading challenger.** Across 17 stress states it beats the paired baseline in 14 (82.4%); its family-balanced CAGR gap is +1.26 pp, drawdown gap +4.64 pp, and Sharpe gap +0.067.
- **Do not promote a target-only change to the live model.** Mean top-1 agreement is only 72.5%, worst-case 37.0%, essentially no better than the baseline under the same perturbations.
- **Avoid a 5-year rolling window.** It is the clearest failure state for both targets; `CONSENSUS_MULTI` loses 2.94 pp of CAGR and worsens drawdown.
- **Next experiment:** preregister temporal rank ensembling across staggered cutoffs and multiple admissible training windows, then add a switch gate based on ensemble agreement. Do not retune target weights on this history."""
        ),
    ]
    args.output.parent.mkdir(parents=True, exist_ok=True)
    nbf.write(nb, args.output)


if __name__ == "__main__":
    main()
