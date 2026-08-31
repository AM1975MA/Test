# STEP08C — Protective Rotation / Destination Selection

Date: 2026-08-31

## Objective
Test the structural hypothesis that, when the already-frozen STEP07A risk state gives a high-confidence collapse warning, capital should be rotated to the strongest available ETF rather than reduced mechanically. BIL is the explicit safe outside option when no risky destination is convincing.

## Scientific boundary
- Development/replay window: 2021-01-01 through 2022-12-31.
- All destination-model fitting uses only data dated <= 2020-12-31.
- 2023+ remains sealed for this experiment unless a frozen causal policy passes the quality-jump gate.
- No GitHub Actions and no post-result parameter grid.
- Current benchmark: exact frozen FUSION1 replay on the Treatment Value HGB 500-basket path.

## Frozen origin-risk trigger
Reuse STEP07A `LOCAL_PLUS_REGIME` exactly; no new crash classifier is fitted for development selection.
A protective-rotation decision is armed at the first row of an adaptive stress episode with causal `risk_pct > 0.95`.
This threshold is not selected in STEP08C: it is the already-frozen highest-risk bucket from STEP07A, where the exposure map prescribed zero gross exposure.
One decision is allowed per adaptive episode. A decision at close t becomes effective for returns beginning after the next session close (t+2), matching the conservative lag convention used in STEP07B.

## Destination universe
Primary ceiling and selector universe: all frozen 150 Meteor ETFs with valid point-in-time prices at the decision date, excluding the current monthly leader and satellite when they are explicitly identifiable. BIL is always admitted as the fallback outside option.
The full-150 test is deliberately an opportunity ceiling; a later basket-only deployment audit is required before promotion if the causal selector passes.

## Holding rule
A selected destination is held for 10 trading-session returns, then the portfolio returns to the frozen FUSION1 path. New decisions for the same basket are suppressed while a prior rotation is active.
Direct ETF rotation pays 10 bp one-way at entry and 10 bp one-way at exit. STAY pays no incremental cost.

## Phase C0 — oracle destination ceiling
At each frozen high-risk decision, compute every candidate ETF's realized 10-session path, strictly for diagnostic oracle purposes.
For a path with cumulative return R and local minimum drawdown M <= 0, define robust utility

`U = R + 0.5 * M`.

This is the same return/downside structure used in the earlier robust action-value work.
Two oracle diagnostics are frozen:
1. `ORACLE_FORCE_ROTATE`: choose the ETF/BIL with maximum U; origin/FUSION1 continuation is not an action once the collapse warning fires.
2. `ORACLE_STAY_ALLOWED`: choose the maximum-U action among exact FUSION1 continuation and all ETF/BIL destinations. This is the pure opportunity ceiling.

No oracle result can be promoted; it only determines whether destination selection has enough economic ceiling to justify modeling.

## Oracle continuation gate
Proceed to a causal destination model only if `ORACLE_FORCE_ROTATE` or `ORACLE_STAY_ALLOWED` achieves, versus FUSION1 on 2021-2022:
- delta mean MaxDD >= +0.50 pp;
- delta p10 MaxDD >= +0.50 pp;
- delta CAGR >= -0.50 pp;
- mean-MaxDD delta non-negative separately in 2021 and 2022.
If neither passes, stop STEP08C before causal modeling and before 2023+.

## Phase C1 — causal destination selector (only if C0 passes)
Training examples are generated from pre-2021 adaptive stress rows. The model never sees post-2020 labels.
The target for each candidate is its 10-session robust utility advantage over BIL, net of the fixed entry/exit costs.
A deliberately low-dimensional Ridge model is used to avoid another high-capacity search. Candidate inputs are restricted to causal price/state features available at the decision close:
- candidate returns 5/21/63;
- candidate realized vol 20/63;
- candidate drawdown 21/63;
- candidate correlation 63 to the exact basket HGB daily return;
- candidate relative returns versus the basket over 5/21/63;
- cross-sectional ranks of return, volatility and drawdown;
- the frozen raw STEP07A local/regime state variables (not fitted hazard probabilities).

At a validation trigger, choose the candidate with maximum predicted advantage. If the maximum predicted advantage is <= 0, rotate to BIL. Otherwise rotate to that ETF. No threshold search is permitted.

## Causal quality-jump gate
A frozen STEP08C causal policy qualifies for a one-shot holdout only if, versus FUSION1 on 2021-2022:
- delta mean MaxDD >= +0.50 pp;
- delta p10 MaxDD >= +0.50 pp;
- delta CAGR >= -0.50 pp;
- mean-MaxDD delta non-negative in both 2021 and 2022;
- worst-decile mean MaxDD does not worsen.

## Stop rule
If the oracle has a strong ceiling but the causal selector fails, do not tune the q95 trigger, 10-session horizon, Ridge alpha, destination threshold, feature weights, or ETF universe in STEP08C. The conclusion is then that destination opportunity exists but is not causally extractable with the current information set.
