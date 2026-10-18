# HYPOTHESIS H02 — Kalman as an independent uncertainty/risk observer
Date frozen: 2026-10-18. Research only; never merge into production without independent validation.

## Observation, not a success claim
Frozen evidence: `research_bayes_europe/results/RESULT.json`, Action 39087987551 (113 monthly 2017–2026 decisions on retrospective EUR60).
- Return-NDCG + Hybrid, fixed Top2 50/50: CAGR 9.978039%, monthly sampled MaxDD -26.6441%, monthly Sharpe 0.4906.
- ROBUST_KALMAN alone, same execution: CAGR 6.745238%, MaxDD -23.82097%, Sharpe 0.5885.
- MOMENTUM alone: CAGR -0.12684%, MaxDD -41.855%; mixed momentum + Kalman: CAGR 8.1262%, MaxDD -34.715%.
- Kalman mean chosen-Top1 return ~0.5338%/month, versus Return-Rank+Hybrid ~0.9823%, so it does NOT demonstrate superior standalone winner prediction.
- In the frozen 1,000-run random Top2 null, Kalman CAGR percentile 60.3% and Return-Rank+Hybrid 94.9%. Null is conditional on study universe, not a significance test.
- Block-bootstrap 12-month paired Kalman minus R_H monthly log-return difference -0.002486, 95% exploratory CI [-0.008117,+0.003184]. Includes zero.
- Severe limitation: the 60 ETFs were retrospectively filtered from a 2026-07 historical-price survivor universe, EUR quote currency not independently verified, multiple listings may duplicate an underlying fund, and all 2017–2026 months have been repeatedly explored. There is no valid independent prospective test or credible production alpha estimate.

## Hypothesis
**Retain R_H as the ETF *selection/ranking engine*; use Kalman's posterior dispersion, robust monthly volatility and latent-drift uncertainty as a statistically independent *risk state observer*, initially without allowing Kalman to select different tickers.** This may reduce exposure fragility, improve risk-adjusted return and/or reduce trade turnover even if Kalman is a weak winner predictor. A legitimate null is no benefit over simply equal-weighting the selected names or volatility weighting from raw historical returns.

Scientific analogy: a state observer in control engineering does not replace the controller's goal; it estimates hidden state/measurement uncertainty. Analogies are conceptual, not claims of conserved physical quantities.

## Causal falsification design — no tuning on burned EUR60
1. Freeze R_H scores/Top2 picks and next-common-open calendar unchanged; log realized daily/monthly returns with the *same* one-way 10bp turnover cost and a consistent post-entry rebalancing rule.
2. Four precommitted allocation arms, all on **identical R_H Top2 membership**:
   A: unchanged 50/50; B: plain training-only 63/126-day realized-volatility inverse-risk weights; C: Kalman posterior **variance only** inverse-risk weights; D: Kalman posterior **mean and variance** bounded tilt. Each alternative must have an explicit cap, effective price/uncertainty normalization, strict minimum history and deterministic all-risk-unavailable fallback. B separates generic volatility targeting from useful posterior Kalman information; C vs D separates uncertainty from directional prediction. No structural parameter grids or in-sample weight optimization.
3. Separately, only after a new forward protocol, test R_H unchanged selection vs R_H re-ranked by posterior downside probability under identical allocation. This is a *separate* hypothesis; do not bundle with sizing.
4. Compare monthly paired log returns, daily and monthly MaxDD, daily tail loss (expected shortfall at 95%), turnover, relative exposure, selection identity and model confidence calibration (prequential predictive log score and interval coverage).
5. Check changes under raw-price small perturbations using multiple dependent Yahoo vintages; treat those vintages as a robustness stress test, not 3 independent holdouts.
6. Benchmark against inverse-vol weights, Europe equity index buy-and-hold and a *realistically investable EUR-denominated defensive alternative* if any cash sleeve is introduced. Do not silently reuse US BIL/SHV for investable European portfolios. Clearly state risk-free/cash interest, quote currency, fees, slippage and missing prices.
7. Require point-in-time ETF existence/eligible UCITS, currency verified by venue, unique ISIN and delistings. Treat the previous frozen EUR60 as development-only. Reserve future data after model freeze for a truly untouched forward record. If prospective data are unavailable, remain exploratory.

## Acceptance standard
No claim based solely on CAGR or highest selected strategy from a search. A credible result needs (i) untouched selection and path parity for 50/50, (ii) reduced future log loss or calibrated downside risks versus simple realized volatility, (iii) consistent out-of-time economic risk improvement after costs, (iv) robust no-lookahead tests and confidence intervals, (v) generalization to a separately curated live/point-in-time roster. Failure on these gates rejects the observer as useful, not just a specific tuning constant.

## Non-goals and protection
Do not mutate `etf_trader`, existing historical evidence, 60-source snapshots or previous protocol. This document is a frozen *hypothesis*, not a completed backtest or a commitment that filters will improve future performance.
