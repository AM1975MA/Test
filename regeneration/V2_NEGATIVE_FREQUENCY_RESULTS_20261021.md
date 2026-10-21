# V2 127-leaf XGBoost — Negative-session frequency ablation

**21 October 2026. Experimental run complete. Decision: DO NOT PROMOTE CORRECTED_PLUS_FREQ.**

## Exact provenance

- Frozen 149-ETF adjusted OHLCV input: successful source run [39482809691](https://github.com/AM1975MA/Test/actions/runs/39482809691), artifact `12292840548`.
- Original and mathematically corrected **125-feature** annual retrains were already completed and frozen in [39515716383](https://github.com/AM1975MA/Test/actions/runs/39515716383), complete artifact `12307848715`. The historical `LEGACY` score previously matched the official V2 127-leaf original on all 15,198 ETF-month scores, with zero discrepancy.
- 128-feature, **CORRECTED_PLUS_FREQ**, was newly refitted from scratch, annual chronological expanding-window, in [39557244268](https://github.com/AM1975MA/Test/actions/runs/39557244268). Its three independent training jobs all passed, and each produced its source and OOS score artifacts. The initial combined step failed because prior months were serialized with midnight timestamps and new records with date-only strings (same logical dates). Timestamp normalization fixed the artifact stage without changing any predictions or retraining.
- Fully successful OOS aggregation + economic replay: [39558214003](https://github.com/AM1975MA/Test/actions/runs/39558214003), artifact `12326367485` `v2-negative-frequency-final-results`.

No model or production-repo default branch has been changed. Original seed, 500 fixed baskets of 24, snapshot, label/eligibility mask, target, and training years are shared across arms. Risk/Tail/Macro are disabled.

## Predeclared features

The new inputs are three full-window and strictly past-looking measures:

`negative_day_fraction_h = rolling_mean( log(Close_t/Close_{t-1}) < 0 )`

for `h in [21,63,126]`. A true missing daily return remains NaN, not a nonnegative session. Only a complete observed window yields a numeric fraction.

Feature diagnostic over the full extracted input panel: missing fraction approx 1.93% (21-day), 2.99% (63-day) and 4.60% (126-day), mostly warm-up and authentic missing histories. No new feature is all-NaN. Data are generated at each signal month-end and never use future returns.

`CORRECTED_PLUS_FREQ` has **128** features: corrected 125 plus exactly these 3. Controls are `CORRECTED` (125) and historical `LEGACY` (125). All test dates and test members use the same original legacy 30-of-125 nonmissing eligibility criterion. Training uses `XGBRanker(rank:pairwise, 127 leaves, 360 estimators, 3 seeds 101/202/303)`.

## OOS predictive performance

101 matured monthly 21-day targets, 2018 through May 2026, the same 149 ETF universe and 500 canonical baskets:

| Metric | LEGACY 125 | CORRECTED 125 | CORRECTED_PLUS_FREQ 128 |
|---|---:|---:|---:|
| Universe monthly Spearman IC | **0.042796** | 0.038536 | 0.033962 |
| Universe Top-1 capture | 6.931% | **8.911%** | **8.911%** |
| Universe Top-3 capture | 13.861% | **16.832%** | 14.851% |
| Basket Top-1 capture | **15.087%** | 14.553% | 14.515% |
| Basket Top-3 capture | **35.745%** | 35.471% | 35.071% |
| Mean basket regret per 21D | **10.208%** | 10.412% | 10.487% |
| Mean selected excess return per 21D (basket) | **0.916%** | 0.712% | 0.637% |

Changes in CORRECTED_PLUS_FREQ vs CORRECTED:
- Basket Top-3 **-0.400 percentage points**. Paired circular 6-month block bootstrap (n=101, 6000 replications) exploratory 95% CI **[-1.610,+0.806] pp**.
- Universe IC **-0.004574**. Bootstrap CI **[-0.010816,+0.001396]**.
- Mean basket regret **+0.0753 percentage points per 21D**, CI **[-0.1515,+0.3133] pp**.
- Against LEGACY, basket Top-3 **-0.673 pp**, CI **[-1.933,+0.556] pp**.

The 500 overlapping baskets are first aggregated by month; **they are not treated as 500 independent trials**. Previously analysed years are NOT an untouched holdout.

### Monthly Top-3 capture by calendar year: evidence of heterogeneous response

| Year | CORRECTED | CORRECTED_PLUS_FREQ | Change (percentage points) |
| --- | ---: | ---: | ---: |
| 2018 | 31.017% | 28.350% | -2.667 |
| 2019 | 29.500% | 31.067% | +1.567 |
| 2020 | 27.617% | 25.517% | -2.100 |
| 2021 | 37.450% | 34.967% | -2.483 |
| 2022 | 45.500% | 47.583% | +2.083 |
| 2023 | 42.483% | 43.283% | +0.800 |
| 2024 | 29.317% | 30.183% | +0.867 |
| 2025 | 37.417% | 37.750% | +0.333 |
| 2026 (5 matured months) | 43.800% | 39.560% | -4.240 |

The extra feature group helps some years and hurts others; **these are descriptive post hoc regime differences**, not evidence that a live regime-switching rule would work. In particular, 2022 improvement is not a robust reason to engineer an after-the-fact market classifier without unseen-data evaluation.

## Next-open economic simulation — XGBoost only

500 canonical overlapping balanced 24-ETF baskets, 2018-02-02 through 2026-07-01. At month-end choose the highest score using same-day relative percentile. Next adjusted open fills; 10 bp cost on actually traded notional; 75%/25% Top-2 unless difference between score percentiles >= 0.12 then fully Top-1. No Tail, Macro, stops, risk overlays.

| Metric | LEGACY 125 | CORRECTED 125 | CORRECTED_PLUS_FREQ 128 |
| --- | ---: | ---: | ---: |
| Mean basket CAGR | **13.297%** | 12.057% | 10.688% |
| Median basket CAGR | **14.470%** | 13.554% | 11.551% |
| Aggregated NAV CAGR | **15.941%** | 14.729% | 12.720% |
| Mean basket MaxDD | -51.289% | **-50.341%** | -50.418% |
| Aggregated NAV MaxDD | -40.517% | -39.077% | **-39.004%** |
| Mean Sharpe, RF=0 | **0.557** | 0.524 | 0.486 |
| Mean yearly gross turnover | 17.094 | 16.983 | 16.912 |

21-trading-day paired block bootstrap of cross-basket mean daily log-return differences, 4000 resamples:
- CORRECTED_PLUS_FREQ minus CORRECTED: annual log-return difference **-1.118 pp**, exploratory 95% CI **[-3.431,+1.261] pp**.
- CORRECTED_PLUS_FREQ minus LEGACY: annual log-return difference **-2.241 pp**, exploratory 95% CI **[-5.096,+0.457] pp**.

No statistically compelling upside, and economically worse point estimates.

## Recommendation and interpretation

**Reject unconditional addition of these three frequency signals to the current 127-leaf V2 ranker.** This does not disprove regime information's value. In the historical implementation, the old downside-volatility missingness encoded a thresholded regime interaction, not simply a continuous negative-day ratio. XGBoost can make different missing-value routing decisions; supplying a continuous count separately need not recreate the same decision boundaries. A future explicit regime-interaction or two-expert design requires preregistration, event-based and temporal controls, genuinely separate confirmation, and accounting for multiple exploration attempts. Do not tune a gate to the 2022 success and 2026 failure ex post.

Keep the mathematically corrected feature formulas as a separate research branch. Keep `Etf_trader` draft PR #2 unmerged pending any full-stack/production certification. **Do not interpret XGB-only CAGR here as the entire production ETF strategy's CAGR.**
