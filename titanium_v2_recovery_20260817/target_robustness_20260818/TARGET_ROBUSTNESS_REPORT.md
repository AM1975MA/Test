# Titanium target robustness — 18 controlled stress states

## Technical summary

`CONSENSUS_MULTI` is the strongest target challenger, but changing the target alone does **not** solve the live-instability problem.

- Across the 17 actual stress states (excluding the exact-control run), `CONSENSUS_MULTI` beats the paired 21-day baseline in **14/17 (82.4%)**. `MULTI_45_35_20` wins **12/17 (70.6%)**.
- Giving each stress family equal weight, `CONSENSUS_MULTI` adds **+1.26 percentage points of CAGR**, improves mean MaxDD by **+4.64 pp**, and adds **+0.067 Sharpe** versus the baseline. `MULTI_45_35_20` adds only **+0.30 pp CAGR**, **+2.22 pp MaxDD**, and **+0.022 Sharpe**.
- The negative tail remains material: worst paired CAGR gap is **−2.94 pp** for `CONSENSUS_MULTI` and **−3.00 pp** for `MULTI_45_35_20`.
- Decision stability does not materially improve. Across stress states, mean official-basket top-1 agreement with each target's canonical fit is **72.5%** for `CONSENSUS_MULTI`, **72.3%** for `MULTI_45_35_20`, and approximately **72%** for the baseline; worst cases fall to **37.0%**, **36.2%**, and **40.0%**, respectively.

**Decision:** retain `CONSENSUS_MULTI` as the leading challenger, reject a target-only production promotion, and move to temporal ensembling plus an explicit stability gate. Do not tune the target weights again on this same history.

## The control reconstructs the prior experiment exactly

The unperturbed annual expanding fit reproduces all three prior panels with maximum score delta `0.0`, 100% top-1/top-2/regime agreement across **56,500** official basket-date decisions, and identical daily metrics through the official final date of 1 July 2026.

| Target | Mean CAGR | Mean MaxDD | Mean Sharpe |
|---|---:|---:|---:|
| `BASELINE_21` | 18.84% | −41.28% | 0.749 |
| `MULTI_45_35_20` | 19.77% | −37.14% | 0.796 |
| `CONSENSUS_MULTI` | 20.46% | −34.92% | 0.834 |

This exact reconstruction is the validity gate for every perturbation result below.

## What was stressed and what stayed frozen

The matrix contains 18 states across six families:

- control: annual January expanding window;
- cutoff/cadence: annual December, annual February, and quarterly refit;
- rolling windows: 5, 7, and 10 years;
- training-universe dropout: 5% and 10% of tickers removed from training only;
- price-vintage proxy: 0.5%, 1%, and 2% deterministic feature noise;
- live availability: 5% and 10% of tickers unavailable at selection time, with three independent ticker lists per level.

Every state keeps fixed: target weights, feature list, XGBRanker hyperparameters, three seeds, TailMix, macro layer, 70/30 blend, the 500 official baskets, governor, costs, allocation rule, unperturbed labels, daily evaluation OHLC, and final date. Multi-horizon labels must mature strictly before each cutoff.

The price-vintage cases are a controlled proxy, not a second vendor snapshot. Labels and evaluation returns are never perturbed.

## `CONSENSUS_MULTI` leads economically across stress families

| Stress family | States | CONSENSUS CAGR gap | MULTI CAGR gap | CONSENSUS win rate | MULTI win rate |
|---|---:|---:|---:|---:|---:|
| Cutoff/cadence | 3 | +0.88 pp | +0.05 pp | 66.7% | 66.7% |
| Price-vintage proxy | 3 | +2.88 pp | +0.86 pp | 100% | 100% |
| Live ticker availability | 6 | +1.91 pp | +1.01 pp | 100% | 66.7% |
| Training ticker dropout | 2 | +1.67 pp | +0.58 pp | 100% | 100% |
| Rolling window | 3 | −1.05 pp | −1.03 pp | 33.3% | 33.3% |

The strongest positive evidence for `CONSENSUS_MULTI` is its behavior under quarterly refitting (+3.20 pp CAGR, +7.89 pp MaxDD, +0.136 Sharpe), feature-vintage perturbations (+2.73 to +3.16 pp CAGR), and ticker unavailability. The clearest failures are the 5-year rolling window (−2.94 pp CAGR and worse drawdown) and the December cutoff (−1.92 pp CAGR).

## The unresolved problem is temporal sample sensitivity

Changing only the annual cutoff from December to February reverses the direction of the target advantage:

| Refit policy | CONSENSUS gap | MULTI gap |
|---|---:|---:|
| Annual December | −1.92 pp | −1.21 pp |
| Annual February | +1.36 pp | +1.21 pp |
| Quarterly | +3.20 pp | +0.17 pp |

Likewise, rolling windows disagree sharply: `CONSENSUS_MULTI` is weak at 5–7 years but positive at 10 years, while `MULTI_45_35_20` is slightly positive at 7 years and loses 3.00 pp at 10 years. This is not random-seed nondeterminism—the control is exactly deterministic. It is sensitivity to which historical regimes enter each fit and when labels become available.

High score correlations do not remove the issue. Small rank changes near the top of each 24-ticker basket are sufficient to change the selected instruments and materially alter the path.

## Production decision and next experiment

`CONSENSUS_MULTI` passes the economic-direction test but fails the decision-stability and worst-case gates. A target-only promotion would improve average robustness while leaving the original operational concern unresolved.

The next experiment should be preregistered before it is run:

1. Train `CONSENSUS_MULTI` over several admissible temporal views: staggered annual cutoffs and multiple longer windows.
2. Aggregate **ranks**, not raw XGBoost scores, across these fits.
3. Require cross-fit agreement before changing the live top-1; otherwise retain the incumbent or use the stable top-2 allocation.
4. Evaluate the ensemble with the same 18-state harness, with hard gates: positive result in every stress family, worst CAGR gap better than −1 pp, mean top-1 agreement above 80%, and no deterioration in drawdown.
5. Then shadow-run on genuinely new monthly vintages. Do not further tune target weights on the already inspected 2017–2026 history.

## Validation and limitations

The independent validation pass reconciles every scenario-level CAGR/MaxDD/Sharpe to the 500 basket paths, rechecks all baseline gaps, confirms 113 signal dates and 2,366 daily observations per state, and verifies the exact control panel. All checks pass.

The 18 states are structured sensitivities rather than independent statistical draws, and the 500 baskets overlap. Therefore scenario win rates and basket fractions are descriptive robustness measures, not p-values. A real second price-vendor snapshot and future unseen monthly vintages remain required before production promotion.
