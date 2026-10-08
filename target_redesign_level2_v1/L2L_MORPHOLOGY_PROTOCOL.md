# L2-L — Audit scientifico del fattore di forma (no nuove strategie, no tuning)

**Congelato 8 ottobre 2026 prima dell'analisi numerica L2-L.** Unico repository ammesso: `AM1975MA/Test`, branch `research/target-redesign-level2-v1`; `Etf_trader` non modificato. User hypothesis: trend shape, homogeneity/persistence, acceleration, regularity, variance and volatility regimes might preserve original V2 full-pipeline CAGR while reducing poor retraining reproducibility. This is a **diagnostic feature audit**, not an attempt to certify a 43% backtest; Original149 development history is burned.

## Scope and data
Use exact frozen Yahoo Repeat2 149 ETF adjusted prices and baseline `XGB_NATIVE_PREDICTIONS` Repeat2, 113 mature monthly signal dates, horizon 21 next-open; the same source files used in L2-D/L2-K. No fit, no hyperparameter search, no strategy transaction backtest or PnL changes. For every ETF and date, only price history through the signal date is allowed. Validate equal (signal_date,ticker) support, zero duplicate, exact chronology and missingness. Use 2026 adjusted-price snapshot only as a historical diagnostic, not genuine 2017 point-in-time data.

## Fixed metrics, all computed ONLY from last 64 closes ending at signal date (63 session returns)
1. `mom63`: log-price change 63 sessions.
2. `mom252_ex21`: past 252→21 session log-momentum control, if mature.
3. `trend_t_63`: OLS slope t statistic in log adjusted price over last 64 price dates; measures directed trend relative to roughness.
4. `trend_r2_signed_63`: signed slope × squared regression fit R², scaled by 63 (for directional regularity).
5. `path_eff_signed_63`: signed sum log daily returns divided by sum absolute returns.
6. `positive_day_share_63`: proportion strictly positive daily log returns.
7. `accel_21_vs_42`: mean log return last 21 sessions minus previous 42 sessions, annualization not necessary.
8. `vol_63`: daily log return standard deviation.
9. `vol_ratio_21_42`: recent 21 day daily return vol divided by previous 42.
10. `single_jump_share_63`: maximum absolute daily log return divided by sum absolute daily log returns.
11. `sign_change_rate_63`: frequency consecutive nonzero daily returns reverse sign.

These are *not* ten new optimizer proposals. They diagnose which aspects of the curve the canonical 125-Compact21 + 42-MA3 source features represent, especially explicit trend-fit consistency and jump concentration. Pre-existing features include `efficiency63`, `vol63`, `acc_mom_21_63`, `positive_frac63`, `autocorr1_63`, `slope_63_rank`, `jerk_rank`, `directional_energy_63_rank`. A high `trend_t` is partially an inverse-volatility momentum proxy; do not automatically label it new independent information.

## Univariate explanatory audit (NO fitting)
- Month-wise **Spearman cross-sectional IC** of each fixed feature versus realized 21-session next-open return across all ETFs, average equally over months.
- **Within-macro-category IC** by date: demean ranks within source-defined 2026 macro categories and compute within-date Spearman / correlation of demeaned ranks; fixed current category membership suffers historical survivorship bias.
- **Independence diagnostic**: mean same-date Spearman correlation of each shape feature to `mom63` and to frozen original `XGB` score; high association means likely redundant.
- Report sign and magnitude split 2017–2021 vs 2022–2026 and per-year to identify instability; do NOT rank or select a winner among the 11 features based on IC.
- 3-calendar-month moving-block bootstrap descriptive 95% intervals for **only three a priori mechanism contrasts** (trend_t vs mom63, positive_share vs mom63, acceleration vs mom63), 5,000 resamples with seed 20261008; all retrospective, multiple-comparison unadjusted, weak external validity.
- No portfolio CAGR or new candidate decision, and never infer >43% future from screening correlations. If results promising, the next stage first recovers exact 43% V2 baseline provenance and full Hybrid24 causal pipeline before any morphology-augmented learner.

## Four discipline checks
ML: longitudinal shape information and input representation vs 125-feature snapshot summary; no automatic deep model. Econophysics: persistence, volatility clustering, nonlinear shocks / jump domination, invariant changes of market volatility scale. Stats: 113 dates not ~17k independent observations, serial regime dependence, multiple testing. Execution/risk: actual 43% baseline cannot be reconciled to Titanium-only 13.8% proxy without identical portfolio policy, same membership, start/end, cost and stop source.

No simulated agents claimed unless independently invocable agent tools are actually available. No change to production selection parameters or rules.
