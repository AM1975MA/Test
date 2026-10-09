# R0-Q — REAL 149 ETF feature-stability result: continuous downside semideviation (Data audit)
**2026-10-09 | Research only | AM1975MA/Test | research/v2-xgb-immutable-checkpoints-20261008**

## Summary and decision

**REAL FEATURE-LEVEL MECHANISM SUPPORTED; NO MODEL PROMOTION.** Using the original frozen Yahoo Repeat1 and Repeat3 adjusted Close for 149 ETFs over 270 monthly signals (Feb 2004–July 2026), replacing the *research-only computed* discontinuous negative-only conditional standard deviation with a **parameter-free continuous lower-partial-moment / semideviation** reduces dramatic normalized-feature movements under tiny historical price revisions. This **does not** demonstrate annual XGB/MA3 training stability, preservation of extreme ETF winners, or a full V2 CAGR improvement, because the new formula changes feature meaning and availability dramatically.

Pre-registered before running experiment: [R0-Q preregistration](2026-10-09-r0q-continuous-downside-feature-prereg.md), commit `eb264758c65087d54b205e3f20bf72bcea64522c`. No ETF or synthetic models were fitted, no financial backtest and no production file modified.

## Exact formulas and sample

- Native source `vendor/etf_trader_v2/src/etf_trader/source_only/kernel.py::rolling_downvol`: `r.where(r<0).rolling(h,min_periods=max(10,h//2)).std(ddof=0)*sqrt(252)`.
- Fixed research challenger: `sqrt(rolling_mean( min(log_return,0)^2, window=h, min_periods=h ))*sqrt(252)`. Includes all valid trading days, with nonnegative days contributing **zero risk**, rather than missing negative-only observations; continuous in log return around zero, no epsilon tunable parameter.
- Both source-native and challenger outputs use the **same** per-signal cross-sectional median/MAD normalization `(v-median)/(1.4826*MAD)`, clipped at ±8. The new feature has **different mathematical meaning**: lower partial standard deviation about zero vs original conditional standard deviation of negative days; not interchangeable.
- Fixed 149 ETF, 270 SPY month-end dates, horizons **21, 63, 126**; Yahoo Repeat1/Repeat3 frozen `yfinance-repeatability-v1-raw.zip` SHA256 `fcc02918b3a42c3fecde273c4639ca4eed1b5f31e4b8c32aeea4c2a8e4c00f86`. No future features, train labels or selection targets.

## Real-world findings (source R0-P baseline independently reproduced first)

| Lookback | Original max absolute normalized feature revision | Continuous challenger max revision | Max-gap reduction factor | Original cells >0.1 | Continuous cells >0.1 | Comparable original cells → continuous cells |
|---|---:|---:|---:|---:|---:|---|
| 21 sessions | **0.9110133** | **0.0023024** | **395.7×** | 44 | **0** | 18,416 → 35,025 |
| 63 sessions | **0.3615786** | **0.0012990** | **278.4×** | 18 | **0** | 12,747 → 34,735 |
| 126 sessions | **0.9676467** | **0.0004144** | **2,335.0×** | 4 | **0** | 8,689 → 34,285 |

**Important comparability warning:** the original and continuous columns do NOT have the same nonmissing support. The new formula increases observations **1.90×, 2.72×, 3.95×** and would significantly change annual fit matrix availability. It is therefore incorrect to claim the same trained model would automatically improve or to compare missingness-blind mean absolute error as a pure numerical effect.

On the **fixed original anomaly cells** >0.1 under original revision:
- 21d: all 44 remain comparable with new feature; new variation <0.01 in each.
- 63d: of 18 original anomaly cells, 16 have valid new comparable values; none changed >0.01.
- 126d: all 4 remain comparable; none changed >0.01.

**Meaning/predictive risk within the same Yahoo vintage:**

| Lookback | Median per-date Spearman native vs challenger *raw downside-risk ranking* | Mean intersection of each feature's 10 highest-risk ETFs |
|---|---:|---:|
| 21d | 0.945515 | **83.16%** |
| 63d | 0.968577 | **89.50%** |
| 126d | 0.976893 | **93.27%** |

This is informative similarity but substantial change in feature ordering. With original min-periods counting **negative days**, eligibility is sensitive to the sign of individual ~zero returns (confirmed using a signed 1e−12 numerical test). Changing to zero-target semideviation avoids that numerical discontinuity at the cost of changing training population and feature scale. Downside-risk raw, percentile, and normalized deviation entries in Compact21 and features reaching Tail/MA3 may differ.

## Data-independent QA and test evidence

- Frozen original R0-P benchmark **reproduced exactly** in all 3 horizons: original pairwise vintage common-finite, availability discordances and max abs normalized values. No silent missing-month or ticker-universe adjustment.
- **6/6 TDD tests PASS**, including source negative-day minimum crossing from finite to NaN under tiny ±1e−12 return, alternative continuity/no future leakage, strict date/ticker alignment; Python `compileall` PASS.
- An independently coded **Data reviewer** `data_independent_audit.py` evaluates all 3 horizons against the frozen source R0-P benchmarks and asserts all of the following: source parity, new zero revision differences >0.01, missingness changes NOT hidden, realistic lower native-vs-new top10 overlap, and exact original anomaly counts. **AUDIT_PASS**.
- Exact executed source code, test logs, raw analytic JSON and checksummed manifest are in the conversation artifact `ETF_Trader_V2_R0Q_Continuous_Downside_Data.zip` (ZIP CRC and all listed source SHA-256 contents verified locally). The 75 MB input data ZIP deliberately not replicated. **These source Python scripts are in the conversation ZIP, not claimed to have been committed to GitHub**.

## Scope and next economically meaningful gate

1. **DO NOT PROMOTE R0-Q** or swap a new formula into a saved old Booster: different feature schema semantics, data availability, eligibility and cross-sectional ranking.
2. This result *does* justify a **single pre-registered future point-in-time feature-construction challenger** (continuous LPM2) if a genuinely independent as-of dataset and audit of the old model's feature imputation/cohort contract are available. Test **feature-X side** with same mature labels, annual cutoff, seeds 101/202/303, both 21/63 horizons and canonical 360 rounds. Distinguish old vs new schema/model IDs and do not call it historical parity.
3. Only if the new candidate preserves realized positive-tail ETF capture and cross-vintage economically material decisions under held-out as-of data, consider a **matched full V2 2,366-day-equivalent** daily engine comparison *on a genuinely new evaluation period*, with fees, MA3, clusters, stop/governor and risk unchanged. A short future window does not warrant a precise annualized CAGR assertion.
4. If the original feature's eligibility is essential for predictive skill, reject LPM2 or design a new candidate under a separate preregistered mathematical mechanism. Do **not** tune an epsilon (R0-P's epsilon 1e−6 was post hoc) or round count/leaf count/margin on repeatedly burned Original149.
5. A label-only confidence-margin fix and native topk5 fit already **FAILED** joint synthetic gates (R0-M and R0-O); do not rerun those or overwrite annual V2.

**Bottom line:** We have located a concrete and preventable *input numerical discontinuity* with large cross-vintage amplification in the actual ETF source feature. We have not proven that removing this discontinuity improves the economic objective. Real missingness and feature-rank changes make prospective predictive and full-V2 validation mandatory.

## Additional source-code eligibility QA

The source-only `models.py` does **not** require every feature to be present: it defines `valid = frame[k.F2D_FEATURES].notna().sum(axis=1) >= 30`, and each annual `Xtr` retains its remaining per-feature NaNs for `QuantileDMatrix`. Therefore **a feature's available cell count is not the same thing as the number of training rows**. R0-Q proves large changes to the *downvol feature availability*, but **does not measure whether any canonical ETF training row enters/leaves the actual >=30-feature cohort**. Such a conclusion requires the full 125-feature point-in-time panel. The new feature is not a drop-in replacement even if the selected train-row cohort happens to remain identical, because NaN routing, ranks and values change.

## Post-run Data matched-support review (quality-control only, not a new test-selected threshold)

The first attempt to compare on the original native support **failed**, because 4/23/13 cells (21/63/126 sessions) originally finite across Repeat1/Repeat3 were *not* finite under the challenger (for example early incomplete lookbacks). This must not be hidden. We therefore used the **four-way intersection** of both formulas and both price vintages:

| Window | Four-way valid cells | Original valid cells excluded | Max original delta on these cells | Max LPM2 delta on exactly same cells | Cells >0.1 native→LPM2 | Mean delta reduction |
|---|---:|---:|---:|---:|---:|---:|
| 21 | 18,412 | 4 | 0.911013 | 0.002302 | 44→**0** | **23.2×** |
| 63 | 12,724 | 23 | 0.235884 | 0.000656 | 16→**0** | **44.0×** |
| 126 | 8,676 | 13 | 0.967647 | 0.000404 | 4→**0** | **24.2×** |

Thus a material feature-stability advantage remains on *exactly matched ETF/date support*, even when the differing missingness is excluded from both arms. The earlier headline 396×/278×/2,335× max gap reduction compared each formula's *own* valid support, so those ratios are **not** matched-support causal comparisons; use the new table for any like-for-like conclusion. QA metrics came from `matched_support_audit.py`, which belongs to the checked conversation ZIP `ETF_Trader_V2_R0Q_Continuous_Downside_Data.zip` (15 files).

**Source-level row eligibility caveat:** `models.py::fit_predict` applies `frame[k.F2D_FEATURES].notna().sum(axis=1)>=30`. Therefore a change in *one feature's* observed-cell count does not prove a change in the number of *training rows*: annual train rows may remain the same and only missing-value routing change. The complete 125-feature panel is required to quantify cohort changes.

**Final QA:** 6 focused tests GREEN, `compileall` PASS, Data audit PASS, matched-support audit PASS, ZIP manifest hashes verified. No XGB fit and no portfolio backtest.
