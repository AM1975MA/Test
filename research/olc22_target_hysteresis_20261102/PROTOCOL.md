# OLC22 — fixed target hysteresis / replacement-margin control

2 November 2026. Registered after OLC21 showed that linear score shrinkage does not produce a common EU/USA improvement. Exploratory reused-history block, not a new holdout. Parent OLC21 e0ce6920d3e9634afdcc27abf330d7209ffaa8a5. No new ETF learner, feature, context model, target, stop barrier, cooldown, V6 rule or market-specific parameter.

## Motivation and label-blind scale check
AUTH FUSION Top1–Top2 score-gap medians are approximately 0.0128 EU and 0.0170 USA. The score deficit of a prior target relative to the new Top2 threshold has median approximately 0.0470 EU and 0.0406 USA. These quantities use scores/decisions only, not future returns.

## Decision rule
Use exact OLC20 AUTH FUSION scores. At each monthly signal:
1. compute the ordinary current Top2 threshold s2;
2. inspect the two targets proposed at the preceding signal (not future outcomes);
3. retain a prior target if its current FUSION score is finite and >= s2 - margin;
4. if two are retained, keep both; if one is retained, fill the second slot with the highest current-score candidate not already retained; if none is retained, use ordinary Top2;
5. deterministic ticker tie-break remains ascending.

This is target hysteresis, not yet a model of the actual post-stop holding. Risk execution can make actual holdings differ from the previous proposed pair; that limitation must be reported.

## Fixed margins
Test exactly {0, 0.005, 0.01, 0.02, 0.04, 0.08, 0.12} score units. Margin 0 must reproduce the AUTH decisions and economics exactly. The same margin is used for EU and USA, all years, both risk contracts and both fee levels. No local refinement is permitted inside OLC22 after seeing outcomes.

## Economic replay
Candidate-specific V6 rebuilt from each hysteresis pair. Same OLC20/OLC19 ALARM and FAST_LOCK3 contracts, fees .001/.003, stop friction .001, timing and accounting. Primary window ACTIVE2021_2024.

A common improvement requires CAGR > margin0 in BOTH EU and USA under the same risk contract. Rank common improvements by the smaller of the two CAGR deltas. Secondary diagnostics: fee .003, FULL history, yearly returns, MaxDD, CVaR, turnover, pair-change count and replacement suppression. No different margin by market.

## Verification
- margin0 exact pair and account-array parity with AUTH;
- no use of label/outcome columns in the decision function;
- deterministic carry/retain/fill behavior;
- V6 never overlaps primary target;
- independent interval-return reconstruction;
- all seven margins persisted including adverse outcomes.

## Interpretation
This block measures whether a fixed replacement buffer improves the transition from one Top2 decision to the next. It does not certify a residual-value model, actual intraday execution or prospective alpha. A successful margin remains an exploratory challenger and any later refinement requires a separate protocol.
