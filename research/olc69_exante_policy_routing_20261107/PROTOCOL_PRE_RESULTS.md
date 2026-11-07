# OLC69 — Prequential route of independent allocation and execution decisions
**Protocol frozen 7 Nov 2026 before OLC69 route results. Research-only; no original OLC19/main mutation.** Fully mined 2019–2026; any results are retrospective and cannot establish independent alpha. This is not a 50/50 average of two policies.

## Source fixed
- Original OLC67 zip SHA256 `dbfb2cec587fa7b1a118209856d474236707692b6f7ed68fa99c1c27df9661c4`; contains the 32 native daily accounting paths, original OLC19 engine and original OLC56 weights.
- OLC68 `OLC68_PRESIGNAL_EVENT_DIAGNOSTIC.csv` SHA256 `b7911d1346f6d78a19513547fd4b91b8a68a1806b2332f3a95815fcaf2caf330`; 82 eligible months per market with pre-event asof features and observed relative policy outcomes.
- Keys are market × signal_month. Outcomes in log-bp from identical fee=.001 and FAST_LOCK3 paths. Label months trainable only when **two full monthly events older** than the current signal, which avoids using the current/previous incomplete next-opening outcome.
- Original OLC19 FULL/native rows and risk states for EU and USA are unmodified.

## Fixed approach
At each signal, forecast the relative economic value of: A=50/50+IMMEDIATE (baseline), B=MINVAR63+IMMEDIATE (weight-only), C=50/50+DELAY3 (timing-only), D=MINVAR63+DELAY3. Each candidate B,C,D is fit independently with a market-specific expanding ridge regression of its **net paired next-event log return** relative to A, using only prior mature months; no current-month future labels. Targets: B = weightonly_logbp; C=timingonly_logbp; D=paired_logbp. Three regressions per market-month. Model: StandardScaler and Ridge(alpha=25, fit_intercept=True), no feature or hyperparameter search.
Features fixed to `universe_breadth_63`, `pair_avg_mom63`, `pair_prior_mom_weighted_tilt`, `pair_corr63`; these represent market breadth, strength of the selected opportunity, whether min-var tilts toward/away from recent strength, and diversification. No ETF/ticker identity, year, month id, future label or ex-post rally flags.
Minimum 24 complete, mature observations in **the same market**; before that fallback A. For later months, choose argmax(0, forecast B, forecast C, forecast D) with a *fixed* +5 log-bp monthly edge over A required to leave A. Ties select A/B/C/D in this order. No dynamic retraining on the target event.
- Native execution: choose weights and lag at each monthly event in ONE OLC19 simulation. Event-specific lag 1 vs 3 must maintain pending target updates, exposures, emergency V6, stop, cash and lock states; NO monthly stitching or independent-sleeve averaging. Verify adaptive engine bitwise parity to original A and D when fixed choices, for both markets on all seven OLC19 arrays.
- Risk FIXED FAST_LOCK3, stop_friction .001; fee .001 primary and fee .003 stress. No risk parameter tuning.

## Primary gates
- Compare CAGR and FULL MaxDD vs A (OLC19) and D (OLC67), in MAIN 2021–24, 2024, 2025, 2026 (partial) and FULL Feb2019–first open Jul2026; export monthly selection and realized relative outcome for diagnostics.
- Hold no claim of prospectivity: historical prior data itself has been explored many times. Evaluate *prequential regression skill* against simple chronological training-mean rule on the same times; no tuning.
- If either market has worse FULL MaxDD by >3 pp than A, or FULL CAGR lower than A, do not promote (research only regardless). No post-result threshold/feature/model search.
- Verify deterministic scripts, source hashes, opportunity data as-of dates strictly before event and no label maturity leakage, paired dates, fair fee costs, annual CAGR arithmetic from daily logs.
