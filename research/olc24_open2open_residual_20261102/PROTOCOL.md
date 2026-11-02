# OLC24 — execution-aligned Open-to-Open residual switch model

2 November 2026. Registered after OLC23 failed. This is exploratory reused-history research, not an independent holdout. Parent OLC23 is frozen at b8e33fae7f269f92fff8fb90b9adbffa04828a04. No new ETF base predictor, AUTH ranking, context fit, risk barrier, cooldown, V6 rule or market-data source is changed.

## Hypothesis fixed before OLC24 outcomes
OLC23 trained the replacement veto on a fixed 21-trading-day close-based forward label while the portfolio is actually valued and rebalanced from one archived execution Open to the next. Test whether aligning the differential label to the exact monthly execution interval repairs the residual-value decision.

A second fixed factor tests whether the residual relationship is sufficiently different between EU165 and USA149 to justify separate model parameters under the SAME architecture. A third fixed factor limits recursive drift by allowing a veto-created carry to persist for at most one signal interval.

## Event and exact label
Use frozen AUTH replacement events. Let e0 be the execution Open for the current signal and e1 the execution Open for the next signal. For outgoing o and incoming i, when both archived Opens are observed at e0 and e1:
Y_O2O = log(O[e1,o]/O[e0,o]) - log(O[e1,i]/O[e0,i]) + 0.0005.
The +0.0005 is the saved base-fee amount for avoiding one 50% slot replacement under the legacy half-L1 convention at fee .001.

The label becomes available only at e1. An annual model may use an event only if e1 is strictly before 1 January of that model year. No 21/42/63 outcome enters this target.

## Features
Exactly the same ten signal-time features as OLC23:
incoming-minus-outgoing gaps in FUSION, RETURN, C21, C42, C63, I42, I63; outgoing FUSION; incoming FUSION; outgoing target age.
No realized return, stop outcome, year result or portfolio metric is a feature.

## Model factor
Two fixed fitting modes:
1. POOLED: one EU+USA weighted ridge per year, each market total weight 0.5.
2. STRATIFIED: one ridge per market per year, same feature set, standardization, lambda grid and chronology. This is not permission to use different thresholds or model families.

Ridge lambda grid {0.1,1,10}. Chronological validation uses at most the last two eligible prior calendar years and minimizes validation MSE; tie-break is larger lambda. Fallback lambda=1 only when no valid prior fold exists.

## Persistence factor
Two fixed policy modes:
1. RECURSIVE: a vetoed outgoing ticker becomes part of the candidate previous pair and may be reconsidered again next month.
2. TTL1: a ticker retained solely by a veto cannot receive another veto at the immediately following signal unless AUTH itself has reselected it. This forces re-anchoring after at most one extra monthly interval and prevents indefinite drift.

No alternative TTL is tested in OLC24.

Thus four new candidate procedures are fixed before outcomes:
- O2O_POOLED_RECURSIVE
- O2O_POOLED_TTL1
- O2O_STRATIFIED_RECURSIVE
- O2O_STRATIFIED_TTL1

AUTH_CONTROL is the exact comparator.

## Decision
For each replacement edge, predicted Y_O2O > 0 keeps the outgoing ticker; <=0 accepts the incoming ticker. Two-slot replacements use the matching with maximum summed predicted residual value. No threshold grid, confidence cutoff or market-specific decision threshold is permitted.

## Economics
Candidate-specific V6 is rebuilt. Replay ALARM and FAST_LOCK3, fees .001/.003, stop friction .001 and all inherited timing/accounting unchanged.

Primary: ACTIVE2021_2024 fee .001. A common improvement requires CAGR strictly above AUTH in BOTH EU and USA under the same risk contract. Rank common improvements by min(delta CAGR EU, delta CAGR USA).

Secondary diagnostics: fee .003, FULL history, yearly returns, MaxDD, CVaR, turnover, replacement-veto count, and exact O2O realized residual of vetoed edges. No alternative winner criterion is introduced after outcomes.

## Verification
- Open label uses the exact archived entry dates from the frozen calendar.
- Both Opens must be observed; no missing price is filled.
- label availability e1 strictly precedes annual cutoff.
- future-price perturbations after a cutoff cannot alter earlier model/decision.
- POOLED market weights and STRATIFIED event weights are normalized.
- TTL1 cannot retain the same veto-created carry twice consecutively.
- AUTH_CONTROL account arrays are exact to OLC20.
- candidate V6 never overlaps primary targets.
- independent interval-return reconstruction.

## Limits
The archived Opens and quote masks retain upstream limitations; this does not certify auction fills, spreads, FX/total-return history or delisted-universe completeness. STRATIFIED fitting is motivated after observing OLC23's market-asymmetric failure and is therefore exploratory. Any winner remains a challenger, not prospective proof or a trading recommendation.
