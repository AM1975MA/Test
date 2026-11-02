# OLC21 — causal context shrinkage / blend exploration

2 November 2026. This block is registered after inspection of OLC20 and is therefore exploratory, not an independent holdout. Parent OLC20 is frozen at commit 6c387fac4c2e544bb9dc90f6622cd94faba6d7c2. No main modification, no trading, no new ETF base learner, feature, target, barrier, stop or V6 optimization.

## Motivation fixed before OLC21 outcomes
OLC20 AUTH is strongest in USA while Europe is weaker and some predeclared variants (especially PENALTY_HALF and CONTEXT_LAG) improve EU but damage USA. Test whether partial shrinkage/interpolation can retain the authentic US context benefit while improving Europe under one rule shared by both universes.

## Frozen score sources
Use OLC20 reconstructed score tables only:
- AUTH
- STATIC
- CONTEXT_LAG
- PENALTY_HALF

All have the same RETURN component and support. Blend only the final FUSION score, so the inherited Return weight remains unchanged. No ticker may be dropped because its future outcome is unavailable.

## Fixed blend families
For each secondary source S in {STATIC, CONTEXT_LAG, PENALTY_HALF}, define
BLEND_S_w = w * AUTH_FUSION + (1-w) * S_FUSION
for w in {0.1,0.2,...,0.9}. AUTH and the three source endpoints are controls, not new candidates.

Weights are identical for EU and USA and fixed across dates. Do not choose a different w by market, period, cost or risk contract.

## Causal annual meta-selector
Also build META_CAUSAL. At each calendar year 2021..2026 choose one member of {AUTH plus the 27 fixed blends} using only groups whose complete 63-day outcome is available strictly before 1 January of that year. Evaluate candidate ranking on actual chronological historical score predictions for those already-mature groups. Criterion is the same balanced two-market form used by the contextual fitter:
0.5*(EU mean Top2 excess U42 + USA mean Top2 excess U42) - 0.25*abs(EU-USA).
Require at least 8 eligible groups in each market; otherwise use AUTH. Tie-break in this order: higher criterion, larger AUTH weight, then family order PENALTY_HALF, STATIC, CONTEXT_LAG. Do not use portfolio CAGR, drawdown, fees or future years to choose the annual member.

## Portfolio replay
Use the authenticated OLC20/OLC19 portfolio path unchanged. Candidate-specific V6 is rebuilt for each proposed pair. Risk contracts ALARM and FAST_LOCK3; fees .001 and .003; friction and timing unchanged. Preserve all results.

Primary economic window: ACTIVE2021_2024, fee .001. A fixed or causal candidate is a common improvement only if, under the same risk contract, CAGR exceeds AUTH in BOTH EU and USA. Rank common improvements by the minimum of the two CAGR deltas. This is an optimization criterion, not a statistical probability.

Secondary diagnostics, not alternative winner rules:
- fee .003 same sign in both markets;
- FULL 2019-Feb through 2026-07;
- yearly returns;
- MaxDD/CVaR/turnover;
- ALARM versus FAST_LOCK3.
A candidate that wins only one market is not a common improvement.

## Verification
Tests must establish exact control reproduction, blend identity at w=1 and source endpoint arithmetic, no market-specific weights, causal cutoff for META_CAUSAL, support/NaN preservation, candidate-specific V6 non-overlap, and independent NAV/return reconstruction. Publish adverse cases and all tested weights. No lucky null or single-year winner is promoted.

## Interpretation limits
This is post-OLC20 historical exploration on reused data. Even a common improvement is a challenger, not prospective evidence, not a posterior probability of alpha, and not a live recommendation. Raw total-return/FX/delisting/quote-mask/intraday-fill limitations remain.
