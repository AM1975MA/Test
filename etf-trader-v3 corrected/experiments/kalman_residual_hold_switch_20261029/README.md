# ETF Trader — EU155 Kalman / residual / hold-vs-switch research, 2026-10-29

**Research-only, not production.** Original B0, USA149, V2 and V3 unchanged.

## Experiment and checks
- Frozen original EU155 source (155 ISIN), 101 as-of monthly signals, 2076 trading sessions 2018-02-01 to 2026-07-01, same LIQ50 eligibility/next-open/0.10% per traded side.
- Three fully executed experiment families:
  1. 10 fixed no-training Top5 selectors from Momentum252/63/21, Kalman one-sided relative trend, group trend, idiosyncratic state, innovation20 and hold buffer.
  2. 3 *annual mature-label* Ridge models (2021–26) predicting cross-sectional next-21-day ranks, momentum alone vs momentum+Kalman, plus rank no-trade variant.
  3. 2 *annual mature-label* Ridge models (2021–26) predicting 21-day relative future return, plus economic cost-only and cost+training-residual-uncertainty HOLD/SWITCH.
- Kalman local linear trend: state [level,slope], phi=.98, qlevel=1e-5, qslope=5e-8, meas=4e-4, one-sided filtered state. Filter prefix equality tested at 2020-06-30. **No smoothing with future bars**. Group is only six coarse original EU categories and cannot be interpreted as real bank-vs-tech factor.
- All annual fits must obey `max_train_label_exit < Jan1(fit_year)`. Six years 2021–26 fit audit passed. No new positions at missing Open, 1–3 zero-reported-volume trades; vendor data execution risk remains.
- Frozen B0 NAV versus reconstructed source sim max absolute discrepancy **0.002351**, and the three replay implementations yielded exactly identical B0 output to each other. This is *not* exact original NAV parity.
- Historical universe defined in 2026, 2018–26 heavily mined in past research, no pristine holdout, dividend total returns/spread not certified.

## A. Fixed as-of trend selectors: 2018–24 / full 2018–July 2026 annual CAGR
- MOM252 **2.60% / 8.81%**, whole max DD −35.28%.
- MOM63 −1.96% / 3.84%.
- MOM21 −2.82% / 6.33%.
- MOM_MULTI 1.10% / 7.06%.
- KALMAN_REL −0.58% / 6.13%.
- KALMAN_GROUP −0.74% / 4.84%.
- KALMAN_IDIO **1.55% / 7.93%**.
- KALMAN_INNOVATION 0.62% / 8.56%.
No tested variant beats frozen MOM252 CAGR. Bank ETF positions in 2025: MOM252 4.75/5, KALMAN_GROUP 0.42/5; coarse classification suppresses real economic bank cluster.

## B. Annual walk-forward ranking Ridge (2021–24 / 2021–July 2026 annual CAGR)
- MOM252 **8.64% / 17.16%**.
- ML_MOM −0.64% / 4.16%.
- ML_MOM_KALMAN 1.03% / 6.13%.
- ML_KALMAN_HOLD 2.64% / 5.65%.
Mean monthly 2021–24 IC: ML_MOM .0145; ML_MOM_KALMAN .0162; economically negligible.

## C. Annual walk-forward relative-return Ridge and HOLD/SWITCH (2021–24 / 2021–July 2026)
- MOM252 **8.64% / 17.16%**, DD −28.34%.
- RET_MOM 2.68% / 4.01%.
- RET_KALMAN −0.71% / 1.88%.
- RET_KALMAN_HOLD_COST 0.96% / 2.56%.
- RET_KALMAN_HOLD_COST_UNCERT **2.55% / 4.66%**, DD −22.47%, cumulative turnover 40.96 capital vs MOM252 60.84.
Train-only uncertainty = +0.25 * prior-train RMSE of relative 21-day returns above expected round-trip 0.20% cost. Reduces switching and drawdown, but not net CAGR. Monthly 6mo block bootstrapped annual-log-difference vs MOM252 for risk-aware return-target guard 2021–26: −12.06 pp, nominal CI [−23.24,−1.50] pp; multiple comparisons already performed => exploratory.

## V2/V3 parallel status
Prior EU165 native **2025-only** V2 Hybrid24 16.54%, V3 Pair25 18.88%, MOM252/Top2 42.23%; do NOT compare these figures to the new EU155 Top5 full-window or relabel the current Ridge fits V2/V3. Native multi-year source-only V2/V3 remains pending.

**Decision: reject direct Kalman add-ons as validated return engines; preserve Kalman group/idio as research features if economically labelled PIT sector data become available. Refocus on 21/63-day incremental HOLD vs SWITCH utility, proper sector taxonomy, uncertainty calibration, and multi-year native V2/V3 fairness.**

The complete executable code and original frozen source archive are packaged in the user-visible downloadable conversation artifact `ETF_TRADER_KALMAN_RESIDUI_HOLD_SWITCH_TEST_20261029.zip`, SHA256 `57a1f69a57523b06ba9bd5fe6580dc1bfec28dca97e7370fd69ea5bd47e1b6dc`. GitHub stores methodology and compact results only.
