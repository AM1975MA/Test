# Titanium Live — Compact target redesign

Experiment date: 18 August 2026  
Evaluation path: 1 February 2017 – 1 July 2026  
Decision: **retain `CONSENSUS_MULTI` as the leading challenger; do not promote yet.**

## Question

Can Titanium become more effective and robust under live retraining by changing only the Compact training target, without changing features, model parameters, TailMix, macro, portfolio construction or risk controls?

## Controlled design

The following components were fixed for every variant:

- identical current OHLC snapshot and point-in-time feature code;
- identical Compact feature set and XGBRanker parameters;
- seeds 101, 202 and 303, 360 trees per annual expanding refit;
- TailMix, macro model and 70/30 Compact/TailMix blend;
- official 500 baskets and all 12,000 memberships;
- 12% concentration threshold, 75/25 fallback, governor and transaction costs;
- 113 signal dates and the same final date of 1 July 2026.

Multi-horizon targets were admitted to a training fold only when the 63-session label was fully mature before the annual cutoff. The baseline used the original 21-session maturity rule.

## Targets tested

| Variant | Compact target |
|---|---|
| `BASELINE_21` | Cross-sectional forward-return rank at 21 sessions |
| `TARGET_42` | Rank at 42 sessions |
| `MULTI_45_35_20` | 45% rank21 + 35% rank42 + 20% rank63 |
| `CONSENSUS_MULTI` | 35% rank21 + 30% rank42 + 20% rank63 + 15% worst rank across horizons |
| `DOWNSIDE_UTILITY` | Multi-horizon return penalized by 50% of the worst negative horizon return, then ranked |

## Full-period daily scorecard

| Variant | Mean CAGR | Mean MaxDD | Mean Sharpe | CAGR vs baseline | MaxDD vs baseline |
|---|---:|---:|---:|---:|---:|
| `CONSENSUS_MULTI` | **20.4636%** | **-34.9159%** | **0.8342** | **+1.6246 pp** | **+6.3675 pp** |
| `MULTI_45_35_20` | 19.7677% | -37.1367% | 0.7962 | +0.9287 pp | +4.1467 pp |
| `BASELINE_21` | 18.8389% | -41.2835% | 0.7489 | — | — |
| `DOWNSIDE_UTILITY` | 16.9243% | -39.6477% | 0.7031 | -1.9147 pp | +1.6357 pp |
| `TARGET_42` | 14.8328% | -43.6023% | 0.6345 | -4.0061 pp | -2.3188 pp |

`CONSENSUS_MULTI` also improves the bottom of the basket distribution: full-period P10 CAGR rises from 6.18% to 11.61%.

The frozen official V2 remains a reference, not the optimization target: 21.6541% CAGR, -33.9351% MaxDD and 0.8681 Sharpe.

## Period robustness

| Period | Baseline CAGR | Multi 45/35/20 | Consensus multi | Consensus minus baseline |
|---|---:|---:|---:|---:|
| 2017–2019 | 10.4168% | 10.4502% | 10.4286% | +0.0118 pp |
| 2020–2022 | **27.0443%** | 23.6036% | 22.5032% | **-4.5411 pp** |
| 2023–2026 | 21.1069% | 25.5919% | **28.6182%** | **+7.5113 pp** |

The consensus target is materially better in the recent holdout and improves risk over the full period, but it gives back substantial alpha in 2020–2022. This prevents immediate promotion.

On the authenticated-label yearly attribution check, `CONSENSUS_MULTI` beats the baseline in 6 of 10 calendar years; `MULTI_45_35_20` does so in 7 of 10. Both are weak in 2022, and both lose in 2025.

## Predictive information and training stability

| Diagnostic | Baseline | Multi 45/35/20 | Consensus multi |
|---|---:|---:|---:|
| Mean rank IC 21d | 0.0676 | 0.0844 | **0.0935** |
| Mean rank IC 42d | 0.0860 | 0.1111 | **0.1185** |
| Mean rank IC 63d | 0.1026 | 0.1391 | **0.1452** |
| Pairwise seed rank correlation | 0.9242 | **0.9301** | 0.9275 |
| Pairwise unrestricted top-1 agreement | 32.45% | 39.53% | 39.53% |
| Pairwise basket top-1 agreement | **54.63%** | 55.89% | 54.32% |
| Mean monthly turnover | 66.05% | 65.77% | **65.15%** |
| 100% concentration frequency | 7.09% | 8.72% | 10.51% |

Changing the target increases predictive IC at every horizon. It improves unrestricted top-1 agreement across seeds, but does not materially solve basket-level top-1 instability by itself.

## Paired and bootstrap validation

Using the same authenticated `fwd_ret_21` labels and identical monthly cost treatment:

- `CONSENSUS_MULTI` improves mean basket CAGR by 3.17 percentage points and improves 67.0% of baskets;
- `MULTI_45_35_20` improves mean basket CAGR by 2.31 points and improves 62.4% of baskets.

A 10,000-sample paired circular block bootstrap, with 12-month blocks and the 500-basket mean collapsed before resampling, gives:

| Challenger | Probability of positive CAGR gap | 95% interval |
|---|---:|---:|
| `CONSENSUS_MULTI` | 78.15% | -3.68 to +8.24 pp |
| `MULTI_45_35_20` | 77.81% | -2.86 to +7.09 pp |

The direction is favorable but not statistically conclusive because both intervals include zero.

## Validation assessment

**Share with caveats.** The experiment is causal in the engineering sense that only the Compact target was changed, and the baseline was reproduced exactly: maximum difference in Compact raw score, Compact rank and final Titanium score was `0.0`. All variants use fully matured labels and the same daily simulation.

The evidence does not yet support promotion because:

1. the 2020–2022 block deteriorates;
2. the time-block bootstrap remains inconclusive;
3. target changes do not materially improve basket-level seed agreement;
4. candidates were inspected on the recent holdout, so further target-weight tuning on the same period would introduce model-selection overfitting.

## Recommendation

Freeze `CONSENSUS_MULTI` as the primary target challenger and `MULTI_45_35_20` as the conservative secondary challenger. Reject `TARGET_42` and the tested `DOWNSIDE_UTILITY` formulation.

The next valid test should not optimize the target weights again on this same history. It should subject the two surviving targets to independent retraining perturbations: price-vintage changes, cutoff shifts, ticker dropout and rolling/expanding training windows. Promotion should require that the performance and risk advantage persists across those retraining states, especially through a 2022-like regime.
