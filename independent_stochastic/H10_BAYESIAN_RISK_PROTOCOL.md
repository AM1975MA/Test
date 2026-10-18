# H10 — Independent D1 Bayesian regime vs Student-t tail-control (post-selected exploratory)
Frozen 2026-10-18, **after** seeing D1 emerge as the highest standalone independent Sharpe among nine models. This second-stage risk-only experiment is post-selected and cannot establish independent alpha.

## Exact objective
Keep the **same five ETF names and base weights** at every month from the completed independent price-only stochastic `D1_ROBUST_STATE` run 39119879600. DO NOT reuse any Return-Rank, Hybrid, XGB/LGBM signal. Compare controls on those frozen names/weights without changing their selection. No performance-driven threshold optimization. Execute next-common-open monthly, 10bp one-way fee and 0%-yield EUR-cash placeholder.

## Predeclared risk-only arms
1. `C0_D1_FULL` 100% original independent D1, exact full-ledger CAGR parity required (9.185988173%).
2. `C1_D1_STATIC90` permanent 90% original D1, 10% 0%-yield cash.
3. `C2_D1_HMM`: common-market synthetic as-of daily log-return index; Gaussian two-state volatility HMM with online filtering (not smoothed). Calibration anchor trailing 252-daily-observations realized σ, fixed σ_low = 0.75σ and σ_high = 2.25σ. Fixed transition probability 0.98 from low to low, 0.91 from high to high. Start P(high)=0.2. At monthly signal, filter the trailing 252 returns and if P(high)>0.6, target 50% D1 equity, else 100%. No path-dependent historical labels, no EM fitted to future.
4. `C3_D1_T5_CVAR`: unconditional multivariate monthly scenario distribution from as-of trailing 252 daily log returns on D1 *names*, empirical mean shrunk 50% to zero, covariance 65% sample and 35% diagonal, 384 seeded correlated Student-t(5) common-scale samples. Estimate worst 10%-scenario mean loss L10 = -E[log(wealth)] on lowest decile. Scale equity to clip(0.10/max(L10,.01),.5,1); this is an explicit 10% one-month loss-budget, not fitted from historical outcomes. Cash zero yield, no borrow.
5. `C4_D1_HMM_T5`: two control envelopes act together: risky exposure = minimum of HMM and T5 suggested scales; tests combination without changing selection or underlying forecasts.

Risk gate derives from closes <= signal only. Use saved prior-month holdings `D1_ROBUST_STATE` and underlying OHLC history; never use historical outcomes to choose exposure. Verify exact full-exposure D1 economic parity against original source. Report all rows, T5 tail-risk forecast and filtered high-state probability, proportion of months defensive, MaxDD, CAGR, monthly Sharpe, ES5, paired 12m blocks vs C0, time slices.

A true method gain would improve Sharpe and tail risk relative to both C0 and permanent 90% cash, across periods, with justified stress calibration. If no improvement, reject risk overlay; do not tune 0.6, 10% or 0.5 afterward.

## Evaluation bias
Unchanged historical EUR60 survivors and old 113 monthly intervals; this is retrospective, with already-seen 2024-26 returns and post-selection D1 base. No independence claim. Even significant old-panel paired CIs are exploratory. Need real forward 2026+ point-in-time verified EUR ETF set, adjusted prices, spreads and EUR actual cash benchmark before deployment.
