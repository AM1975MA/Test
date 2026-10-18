# OASIS149 G3 — causal risk probability calibration (frozen before test)

Date 2026-10-18. Branch `research/oasis149-canonical-rebuild-20261018`. **No trading, no threshold tuning, no claims of new alpha**. The exact 149 original US ETFs and source hashes from `oasis149/results/MANIFEST_149.json` are fixed. The G1 score-quality gate failed; risk inference is independent of it.

## What is being predicted
At each 21-session non-overlapping entry opening t, snapshot an actually held ETF basket from the immutable R0 (two ETF concentrated) or R2 (one ETF per macro class) research ledger. Use equally weighted snapshot holdings only, ignoring later G2 rebalancing; these are **hypothetical 21-session constant-share portfolios**, not a new tradable strategy. Estimate as-of previous close P(next 21-session OPEN/OPEN log return < -8%). The actual label is generated after the fixed 21-session horizon and only for evaluation. A 21-session -8% severe loss is a **predeclared stress-definition**, not a stop-loss chosen from backtest profits.

## Four rival probability models
- K0 online empirical event frequency from fully matured past 21-day comparison events of the same basket policy (Laplace-smoothed); no risk factor signal.
- K1 trailing 252-day portfolio return volatility Gaussian, 21-day sqrt-time scaling, zero mean; no claim exact law.
- K2 correlated Student-t(5) two-/six-asset scenarios using as-of 252 daily log returns, covariance shrink 65% sample +35% diagonal, 1024 deterministic seeded common-Student-t shocks, zero mean, 21-session horizon. Calculate log of weighted terminal wealth. No fitting to realized future event.
- K3 trailing 252d nonparametric overlapping 21-session empirical basket block losses, probability smoothed (add one pseudocount), purely historical. Overlapping 21d blocks are not independent, so this is not a valid frequentist posterior confidence band.

## Protocol gates
Signal close before entry Open, label exit at Open t+21, only fully matured observations allowed in K0. Stratify R0 vs R2; evaluate primary out-of-development period 2021-2026, slices 2021-23 and 2024-26. Score probabilistic severe-loss event by Brier and logloss, and recall / false alarm rate at fixed P(event)>=0.30, not backtested exit trades. Block bootstrap by **monthly anchor** (3 contiguous anchors). Require K2 or K3 better Brier and logloss than K0 and K1, with nonzero positive CI on R2 and improvement in both eras. Otherwise declared **RISK_PROBABILITY_UNCALIBRATED** and not permitted as an operational risk controller.
R0 and R2 heavy risk incidents also may be sparse; count events and say "not statistically estimable" rather than fabricate certainty. No uses of actual future risk outcome in exposures, scoring features or model fitting.
Data remains previously mined, survivor-biased and adjusted Yahoo broker opens unverified. Preserve all forecasts/labels, source file hashes, outcomes and models in Git.
