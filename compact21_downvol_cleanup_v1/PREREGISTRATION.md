# COMPACT21_DOWNVOL_CLEANUP_V1 — first-stage source-data QA (2026-10-09)

## User priority: clean first, THEN test three frozen acquisitions
Do not train a hybrid model, run new ranker training or compare the three consecutive Yahoo downloads until a single-source quality and causality audit is completed. Production Etf_trader remains completely unchanged. Use `Test` research branch and a draft PR.

## Established code pathology
Canonical `kernel.rolling_downvol(ret,h)` is `ret.where(ret < 0).rolling(h,min_periods=max(10,h//2)).std(ddof=0)*sqrt(252)`. In particular for h=63 the feature `downvol63` requires **31 negative-return observations** inside a 63-session window, not just a complete 63-session price history. A tiny sign/count variation can flip between NaN and finite values, propagating to `_pct` and `_dev`. Previous `DOWNVOL9` masking failed joint stability and quality gates; deleting the whole family is not an established remedy. The source formula proves a threshold discontinuity; quantify its actual empirical frequency before attributing any share of model instability.

## Isolated alternative data definition
Use full-window, zero-target downside semideviation calculated on *log returns*, preserving the annualization convention: `sqrt(252 * rolling_mean(min(log_return, 0)^2, h))` with exactly `min_periods=h` for h=21,63,126. Positive returns contribute zero (NOT a missing value); a missing return or insufficient full-window history means NaN, never forward/back fill. Replace **all** rows of each raw `downvol21/63/126` with this single consistent semantic definition, and **recompute** the corresponding `_pct` and `_dev` on the same cross-section. Do not replace only originally missing cells: mixing conditional negative-only standard deviations and unconditional downside RMS in the same column is prohibited.

This is a meaningful *feature-definition change*, not a mere neutral `fillna`; never call it a proven fix, and do not inject it into the canonical vendor file. All other 116 Compact21 features, timestamp/ticker keys, targets, eligibility, raw OHLCV, tail, Compact63, strategy logic and source files remain unchanged.

## First QA on acquisition 1 only
Download ORIGINAL run 37121749852 `yfinance-repeatability-v1-raw`, read only `_repeat1` source files; download exactly original run 37150436612 `titanium-internal-fixed-repeat-1` as panel parity authority. Validate exactly the frozen Repeat1 SHA256 for `TI_COMPACT.parquet`; source raw file integrity/contract, date/ticker uniqueness, raw positive OHLC, volume nonnegative, finite individual bars. Compare the directly recomputed old feature formula to retained Repeat1 panel `downvol` raw columns on all matched dates/ETF to prove correct end-to-end lineage, with strict missing mask and finite-value equality (float tolerance <=1e-12 solely for identical arithmetic).

On Original149 eligible 2017-01-31 through 2026-06-30 monthly query rows, report for all horizons:
- original and proposed NaN counts for raw feature and its percentile/deviation variants, year-by-year and total;
- number of full valid rolling log-return windows with **legacy NaN**, negative-return count and share of such missing values demonstrably due to count threshold;
- unexpected new NA, partial raw-return histories and natural cold-start NA separately, zeros in the corrected series, raw OHLC quality evidence;
- exact preservation of all other 116 Compact21 features, all labels and dates, evaluation-row counts, and original `>=30` available-feature eligibility before/after;
- reconstructed source hashes, code/contract SHA, examples by date/ticker of legitimate finite-after-clean missing before, and cold-start exclusions.

If parity fails, output QA failure and do not proceed to model training. Record qualitative caveat: preserving other columns alone does not prove Compact63/Tail/portfolio outcome invariance after future source integration; separately check in later full raw replays.

## Scientific order / stopping
1. Unit tests and canonical source gate; inspect full-window vs source-threshold behavior on synthetic price returns. Fail on future-state leakage, raw missing returns, duplicate keys, non-downvol mutation, raw parsing discrepancies.
2. Complete and publish this acquisition-1-only QA. No three-download performance testing here.
3. Independently approve whether the full semantic redesign is acceptable, then freeze a *new* explicit model experiment using the same data cleaning algorithm for each acquisition, with exact BASE controls, no other changed variables, and original maturity gates.
4. Run three acquisition repeatability and predictive-quality metrics, before any complete raw replay. Only a stability/quality-conserving candidate can advance to a three-source CAGR/MaxDD/turnover replay; independent future/universe validation is mandatory.

No tuning or reward optimization based on Original149. Do not claim a CAGR at this diagnostic step.
