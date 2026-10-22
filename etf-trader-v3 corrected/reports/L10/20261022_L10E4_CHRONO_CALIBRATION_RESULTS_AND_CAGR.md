# ETF Trader V3 Corrected — L10.E4 strictly chronological calibration and cost-matched CAGR

**Date:** 22 October 2026. **Status: completed, exploratory / NOT promoted.** Corrected Pairwise127 general ETF rankings frozen; only a probabilistic post-ML exception check on *already-selected* E1-flagged ETF trajectories versus their specific next-ranked ML successor. Original V2, all frozen V3 model references and earlier tests unchanged.

## Immutable reference, one preregistered intervention

- Preregistered: [E4 protocol](./20261022_L10E4_CHRONO_CALIBRATION_PREREG.md), written before E4 outcome inspection. The only variable versus E3 is an expanding **Platt probability calibration** trained each January 1 on earlier E3 **out-of-time** historical predicted probabilities whose corresponding next-open +21D labels had fully matured *strictly before* that January 1.
- E3 original pair classifier, its 7 features, candidates and frozen probabilities **not retrained**. Use sigmoid logistic C=1 with its only input the logit of E3's historic pair probability; two classes, >=8 prior matured OOT signal months and >=300 distinct prior pair observations, otherwise abstain. Negative fitted slope abstains. Preserve original E3 70% approval threshold now applied to the *calibrated* probability, not a threshold optimized to this period.
- Original raw ETF OHLCV Actions run **39482809691**; original frozen CORRECTED OOS scores run **39700865721**; E3 pair probabilities Actions run **39752940429**, archive 39753447149. Same 149 ETFs, exact SHA256 36a45916b5d8191f3ccd206f39bf3fd3f1ed4bcaffd474e352b69c598f2b6a5e for the 500 original overlapping baskets of 24, and 101 fully 21D-matured OOS signal dates from 2018-01-31 to 2026-05-29.
- Successful [E4 evaluation 39828627036](https://github.com/AM1975MA/Test/actions/runs/39828627036), artifact **12446848962**, durable archive success [39829016417](https://github.com/AM1975MA/Test/actions/runs/39829016417); 18,218 original distinct E3 proposed pair/date records reconstructed and verified exactly, original BASE/E1/E3 functional metrics reproduced. Source [evaluate_e4.py](../../experiments/l10_postrank_trajectory/evaluate_e4.py).
- Annual matured-only calibration first trains for 2021 (2020 had 2,330 fully-matured E3 OOT pairs across 11 monthly signal dates); 2022–2026 refits also pass. No calibrator for 2018–2020. E3 raw classifier and original ML ranking remain unchanged.

## Calibrator diagnostics

Across 64 monthly calibration-evaluable signal dates, simple **equal-calendar-month-mean** Brier loss is 0.252455 for E4 calibrated probabilities versus 0.258747 for the original E3 probabilities on exactly those same pair populations: exploratory improvement of ~0.00629. **Not monotonic annually**: calibration improves this metric in 2021, 2023, 2024 and 2025, but worsens it in 2022 and 2026. Monthwise averaging is reported explicitly and is not equivalent to pooled distinct-pair weighting.

Calendar-year calibration slope (on past OOT log-odds) remains positive but shrinks as historical samples accumulate: 2021 ~0.440, 2022 ~0.261, 2023 ~0.221, 2024 ~0.258, 2025 ~0.243, 2026 ~0.093. These low slopes compress overconfident raw probability estimates towards historical baselines. This explains why the reviewer rarely approves a replacement after 2021.

**Important concentration**: all **158** original basket/slot E4 replacements occur in **2021 only**, across 8 monthly signal dates. They represent **64 distinct (month, incumbent ETF, challenger ETF) pairs**: 87.5% of those pairs achieve next-open-to-21D challenger advantage >=1 percentage point, with mean relative realized return +9.20 percentage points. Mean calibrated model probability for those acted-on distinct pairs is ~74.03%, mean original uncalibrated E3 score about higher. This is **not 158 independent opportunities nor 9.20% portfolio return**: the 500 baskets are correlated, and many are exposed to the same candidate/replacement. No E4 decisions are executed on 2018–2020 or **2022–2026**; hence all apparent E4 profits/protection came from 2021. Conditioning on this rare 2021 subset is an exploratory selection result, not evidence of a general calibrated forecasting ability.

## 101-month functional comparison, same frozen Top3 50/30/20

| Metric | Frozen ML BASE | E3 uncalibrated | E4 OOT calibrated |
|---|---:|---:|---:|
| Basket future-best ETF selected in Top3 | 35.4713% | 35.3327% | **35.4713%** |
| Capital weight on future-best basket ETF | 12.5818% | 12.5202% | **12.5816%** |
| Capital weight on next21D severe losers (<=−10%) | 8.4861% | 8.4026% | **8.4279%** |
| Weighted future rank (larger better) | 0.524852 | 0.524932 | **0.525152** |
| Mean weighted next21D forward return | 1.3560% | 1.3698% | **1.3654%** |
| Weighted oracle regret21 (smaller better) | 0.105470 | 0.105332 | 0.105375 |
| Basket/slot replacements in 500x101 evaluations | 0 | 965 | **158** |
| Fraction of baskets changed | 0% | 1.8634% | **0.3129%** |

E4 minus BASE, paired bootstrap on 101 monthly **aggregated 500-basket** observations, 6000 circular 6-calendar-month draws:
- Future-best ETF Top3 hit: delta 0.0000, 95% CI [−0.000198,+0.000178].
- Future-best invested weight: delta −0.000002, CI [−0.000050,+0.000040].
- Severe future loss capital weight: delta −0.000582 (−0.0582 pp), CI [−0.001717,0.000000]. The zero bound shows the small and concentrated action support, not conclusive risk skill.
- Weighted future-rank: +0.000299, CI [−0.000014,+0.000902].
- Weighted 21D forward return: +0.000095 (+0.0095 pp), CI [−0.000007,+0.000290]; not conclusive.
All periods 2018–26 have been researched repeatedly; these intervals must not be represented as virgin independent validation.

## Exploratory 10bp fee-aware next-open CAGR, exact same source L07 executor

This additional analysis was conducted because the fixed E4 rule yielded good actual selected-pair precision, almost no winner displacement and modest risk-weight improvement. It was **not** selected by a CAGR grid-search. The [economic run 39829232588](https://github.com/AM1975MA/Test/actions/runs/39829232588) completed successfully (artifact **12447777963**), with exact E3 economic reference parity to historical run **39753426512** to tolerance 1e-10. Source [economic_e4.py](../../experiments/l10_postrank_trajectory/economic_e4.py).

Same self-financing original L07 next-open executor, 10bp cost *per one-way dollar traded*, original Top3 slot weights 50%/30%/20%, same 149 ticker prices, same 500 dependent baskets and identical positions unless one of 965 original E3 or 158 E4 archived exceptions is applied. Matched last fully labeled signal May29, 2026, economic end June1, 2026; no invented June30 trading signals.

| Period / aggregate NAV CAGR (500 baskets) | Frozen CORRECTED | E3 | E4 |
|---|---:|---:|---:|
| 2018-02-01 to 2026-06-01 | **15.6504%** | 15.6132% | **15.6997%** |
| 2022-02-01 to 2026-06-01 | **21.4346%** | 20.9823% | **21.4346%** |

**Full aggregate CAGR uplift E4−BASE = +0.04925 percentage points**, and **recent CAGR uplift E4−BASE = exactly zero** because 2022–2026 E4 never intervenes. These are aggregate NAV CAGRs, not mean individual-basket CAGR nor golden/full V2 performance.

Long-window aggregate max drawdown: BASE **−38.4188%**, E4 **−38.4188%** (exactly unchanged at shown precision). 2022+ aggregate max drawdown BASE=E4 **−19.4571%**. The equal recent CAGR and DD are expected from identical actions in that time span, not a new successful risk filter.

Paired annualized log-alpha, averaged across dependent baskets **by common trading day** before resampling, 21-session circular calendar bootstrap 3,000 draws: E4−BASE on 2018–26 **+0.001119** annualized log return (~+0.1119 pp/year), CI95 **[−0.000321,+0.003554]**. Recent E4−BASE annualized paired log-alpha **0.000000** CI95 [0,0]. Paired annualized log-alpha is **not** the same estimand as difference between aggregated NAV CAGRs.

Raw data permanently archived by [economic archival run 39829477302](https://github.com/AM1975MA/Test/actions/runs/39829477302) in [economics_run_39829232588](./economics_run_39829232588/). For each of BASE/E3/E4, full daily NAV/turnover, scorecards including per-basket mean CAGR and aggregate maxDD, calendar-year NAV returns, paired bootstrap, manifest.

## Decision — do not promote E4 to production or frozen V3 ranking

**E4 is the strongest preservation-of-winners behavior among the tested L10.E1–E4 controls, but its observed economic incremental value is weak and 2021-only.** Probability calibration partly improves forecast scoring and reduces the overconfident E3 action volume, while preserving the ML's chosen winners. Even so, observed aggregate CAGR improvement is only +0.049 pp in the long window, no gain at all 2022–2026, and confidence intervals on log-alpha overlap zero. All acted-on decisions cluster on eight 2021 dates, limiting any inference across regimes.

Reject E4 as an automatic deployable veto: **research only**. Freeze the original ML ranker and the E4 record. No threshold retuning to force later interventions; this would test-fit to already explored years. If continuing, demand an independent never-before-used future prediction vintage and a held-out pre-calibration protocol focused on contemporaneous calibration, regime transfer and *incremental utility of each specific ML replacement*, not general universe reranking. Retraining entire ML on original features or choosing CAGR winners would violate the original investigation design.

## Full files and reproducibility

- [Frozen E4 preregistration](./20261022_L10E4_CHRONO_CALIBRATION_PREREG.md)
- [E4 fully archived 101-month predictive output](./data_run_39828627036/): 18,218 source pair checks, OOT monthly calibration, annual coefficients/maturity, 158 individual actual replacements, summaries, monthly/yearly, bootstrap, manifest.
- [E4 fee-aware daily portfolio economics, full cost and NAV](./economics_run_39829232588/).
- [E4 evaluation code](../../experiments/l10_postrank_trajectory/evaluate_e4.py) and [three-arm economic replay](../../experiments/l10_postrank_trajectory/economic_e4.py).
