# ETF Trader V5 — EU165 hierarchical factor/ETF expected-return model, first executable study

**Date 2026-10-31. Research-only; original B0/V2/V3/USA149 and main unchanged.**

This is the **first causal multi-horizon V5 prototype**, **not** the full planned regime-aware distributional optimizer/HOLD-SWITCH decision engine. It explicitly predicts factor future returns and ETF residual future returns at 21, 42, 63 sessions from only historical observations. Original source-native V2/V3 scores are input features, **not blended ranking votes**.

Data: EU165 European-listed UCITS survivor-curated 2026 universe, 159 ticker histories with enough data, 9,706 ETF-month causal feature rows, 89 monthly dates 2019–26. Factor basis daily EXSA Europe, SXR8 minus EXSA for US tilt, EXX1 minus EXSA for banking tilt, LYQ2 euro sovereign; trailing 126-day regularized beta exposures. Yearly expanding/strict mature-label fit in each 2021–26 and 21/42/63 horizon. Factor expected returns via Ridge; alpha via Ridge or matched complexity LightGBM with vs without original V2/V3/Tail native predictor scores. Counterfactual selection uses the same PIT monthly union-of-500 24-ETF basket pool, next genuine Open, 10bps each side, persistent capital, and same half-EXSA-MA200 risk overlay across controls.

**Matched 2021–24 outcomes (CAGR / maximum drawdown / yearly gross turnover):**
- Native V3 Pair25 Full with MA200: **15.67% / -16.51% / 13.24×**
- V5 factor-only 21d: **20.99% / -23.02% / 7.24×**
- V5 factor plus basic history LightGBM 21d, **NO V2/V3:** **22.06% / -20.82% / 7.49×**
- V5 factor plus V2/V3 native score features LightGBM 21d: **22.03% / -20.73% / 6.99×**
- V5 factor plus experts Ridge 21d: **15.04% / -21.95% / 5.79×**
- V5 experts LightGBM using 21/42/63 weighted monthly normalized forecasts: **17.62% / -19.04%**; with buffer Top7 **17.00% / -17.89%**; with additional invvol **16.39% / -16.57%**.

**Most important ablation:** V2/V3 score features add **NO measurable portfolio benefit** within same LightGBM estimator on this history: expert vs non-expert annualized log return difference **-0.032 percentage points** with 6-month block bootstrap 95% CI **[-0.764,+0.698]**, same-month Top5 ticker overlap **91.7%**, rank Spearman 0.979. Relative to frozen V3 protected: V5 expert GBM +5.45pp annualized log, CI **[-2.49,+13.50]pp**, includes 0. Do **not** credit the 22% to V2/V3 or declare proven alpha.

**Unstable regimes:** 2021–22 V5 expert GBM **1.44% CAGR** vs V3 protected **6.50%**; 2023–24 **43.96%** vs V3 **24.11%**; 2025 V5 **20.02%** vs V3 **36.24%** (2025 already extensively mined). At 30bps each side, V5 experts GBM 2021–24 CAGR **20.40%**, V3 protected **12.73%**.

**Forecast skill not strong:** pre2025 2021–24 mean monthly cross-sectional Spearman rank IC for V5 expert GBM = **+.0158, -.0255, -.0152** for 21,42,63 trading days; residual alpha rank IC **-.0133,-.0064,-.0012**. A preliminary naive 80% predictive band covered only ~55% at 21d. A properly past-OOS-error-only 24-month rolling calibration test 2023–24 gets **89.9%** for nominal 80% band at 21d (overconservative). Predicted P(beat EXSA after 20bp) 21d Brier **0.2489**, past-only base-rate **0.2486**, AUC ~0.516. **Calibrated HOLD/SWITCH is not validated.**

**Execution parity**: exact 3 frozen native V3 daily NAV references on 1,539 days, max error **6.66×10^-16**. 18 yearly-horizon training gates all require label exit strictly earlier than next annual fit. No future labels in features or score-based trades. Price-only feed/dividends and real spreads unverified; 2026-based survivors, stale Close ffill valuation possible; extreme hypothesis reuse on 2018-2026 and no pristine holdout means findings cannot support prospective performance claims.

Full 209-entry standalone executable ZIP `ETF_TRADER_V5_GERARCHICA_EU165_20261031.zip` (31,989,538 bytes), SHA256 **333286dc00398f39ebcebec984919b3c0bdb2234024f12595d24b7997048b465**. Original 165 raw price histories, native per-ticker scores, PIT basket pool and historical V4 benchmark replay engine included with V5 source scripts, all OOS predictions, sample data, NAV/trade ledgers, bootstrap, uncertainty calibration and Italian report. ZIP CRC and script compilation verified; replay executed FROM portable package with exit 0.

**NO PROMOTION**. Next gate is point-in-time factor data, meaningful distributional/conditional expected uplift of candidate vs endogenous incumbent and passive benchmark, plus as-yet-unseen chronological data; do not retune parameters based on best 2023–24 CAGR. 
