# ETF Trader V3 Corrected — L10.C candidate-union controlled diagnostic

**22 October 2026. COMPLETE. RESEARCH ONLY — no model or portfolio promotion.**
Diagnostic [GitHub Actions 39703702242](https://github.com/AM1975MA/Test/actions/runs/39703702242) SUCCESS,
artifact 12394450375. Durable 101-month, yearly, bootstrap, manifest, and summary outputs:
[data_run_39703702242/](./data_run_39703702242/).
The archive job [39705218877](https://github.com/AM1975MA/Test/actions/runs/39705218877) succeeded.
Experiment source: [candidate_union.py](../../experiments/l10_pairwise_risk/candidate_union.py).

## One-variable test and exact control

Frozen 149 ETFs, 500 original baskets of 24, 101 mature signal months (Jan 2018 to May 2026).
Original basket membership SHA-256:
36a45916b5d8191f3ccd206f39bf3fd3f1ed4bcaffd474e352b69c598f2b6a5e.
Source predictions are exactly frozen L10 [run 39700865721](https://github.com/AM1975MA/Test/actions/runs/39700865721).
No model refit, price execution, future label input, CAGR optimization or weight modification.

BASE = three highest scored CORRECTED ETFs in each 24-name basket.
UNION = BASE plus any *distinct* names from the Top-3 of L10_TOP5_PAIR127.
MATCHED = BASE plus the *same number* of next-highest CORRECTED names, from ranks 4 onward.
Therefore UNION and MATCHED have identical candidate budgets in each basket/date;
the mean extra names is **1.192931**. "Top-5" in the model name refers to XGBoost
training pair sampling, NOT the candidate list length (which is three).

## Verified 101-month candidate retrieval

| Metric | BASE | MATCHED corrected-only | UNION Top5 proposals |
|---|---:|---:|---:|
| Basket's true future best ETF included | 35.4713% | 45.3782% | **50.6000%** |
| Additional ETF slots per basket | 0 | 1.1929 | 1.1929 |

Paired six-calendar-month circular bootstrap, 6,000 replications, with the
500 overlapping baskets averaged within each month before resampling months:
**UNION minus MATCHED +5.2218 percentage points**, exploratory 95% CI
**[+3.2712,+7.1447] pp**. UNION minus BASE +15.1287 pp,
CI [+12.7641,+17.3664] pp. This is an *oracle coverage upper bound*,
not an investable selection-return gain.

## Incremental candidate quality / danger

Averages calculated in baskets with at least one novel name; the conditioning
and candidate counts are identical for UNION and MATCHED.

| Property of added ETF names | New Top5 names | Next CORRECTED names | Difference (95% calendar-block CI) |
|---|---:|---:|---|
| Fraction losing at least 10% in 21 trading days | 10.4828% | **7.1751%** | **+3.3077 pp** [+2.1302,+4.5527] |
| Fraction in basket's three worst realized ETF returns | 26.9887% | **20.2421%** | **+6.7467 pp** [+4.7374,+8.8241] |
| Mean realized rank quality [0,1] | 0.500851 | 0.509134 | -0.008283 [-0.028066,+0.011365] |
| Average future fractional 21D return | 0.009323 | 0.009408 | -0.000085 [-0.003871,+0.003760] |

The Top5 proposal list provides **more extreme winner candidates** at the same
number of extra places, but contains significantly more large losers and
bottom-three ETFs. Neither mean return nor mean rank quality improves.

### Year-by-year candidate recall (no live portfolio allocation)

| Signal year | BASE | MATCHED | UNION |
|---|---:|---:|---:|
| 2018 | 31.02% | 39.70% | 46.55% |
| 2019 | 29.50% | 40.90% | 46.78% |
| 2020 | 27.62% | 37.70% | 43.52% |
| 2021 | 37.45% | 45.45% | 45.65% |
| 2022 | 45.50% | 56.72% | 63.48% |
| 2023 | 42.48% | 52.32% | 55.50% |
| 2024 | 29.32% | 38.92% | 44.35% |
| 2025 | 37.42% | 48.47% | 58.58% |
| 2026 through May | 43.80% | **52.24%** | 51.52% |

## Consistency with the original L10 result and mechanism

L10 [predictions and economics](./20261022_PAIRWISE_RISK_RESULTS.md)
established Top5-alone winner Top3 42.35% vs baseline 35.47%
but IC 0.0115 vs 0.0385, regret 0.1111 vs 0.1041 and
10% severe-loss invested weight 10.93% vs 8.49% (fixed Top3 portfolio).
Its 10bps next-open backtest did NOT establish greater economic utility.

**Observed:** positive marginal candidate coverage, negative downside selection,
and no established improvement in average rank/mean return of additional names.
**Unproven mechanistic hypothesis:** concentrating pairwise training on predicted
high-score examples improves right-tail discovery but makes the selected names
more dispersed in realized outcomes. Do not present the mechanism as proven causal.

## Decision / next gate

**PASS retrieval complementarity ONLY; DO NOT PROMOTE a ranker or trading policy.**
Candidate UNION is not a 3-position portfolio and was never traded.
Re-ranking UNION by the unchanged CORRECTED scores would always select the
original baseline top three and therefore cannot realize any incremental proposal.

Next separate experiment would require a *pre-registered*, strictly chronological,
past-label-mature risk/alpha second-stage scorer to distinguish winners from
large-losers among the novel proposals without damaging baseline ordering.
One intervention at a time, compare with frozen BASE and equal-capacity MATCHED,
gate on winner weight, future-rank, severe-loss exposure and regret, and only
then replay identical next-open 10bps economics. Historical 2018–2026 dates
were repeatedly used and are NOT a virgin holdout.

Production V2 unchanged. Frozen V3 references unchanged.
Registry entry: l10-candidate-union-size-matched.
