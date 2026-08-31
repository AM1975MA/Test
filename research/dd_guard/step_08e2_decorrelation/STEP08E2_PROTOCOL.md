# STEP08E2 — correlation-aware basket-local protective rotation

Date: 2026-08-31

## Scientific question
STEP08E showed that the 24-ETF basket contains a very large oracle replacement opportunity, but pure authentic monthly `TIT_R` selection still fails temporal replication because 2021 is negative. STEP08E2 tests the user's structural hypothesis directly: a replacement is useful only if it behaves materially differently from the risky sleeve being abandoned.

## Frozen inputs inherited unchanged
- STEP08C/STEP07A q95 risk decision schedule.
- STEP08C 10-session replacement window and 10 bp round-trip replacement cost.
- Exact FUSION1 development replay.
- Frozen 24-ETF basket membership.
- Authentic historical `TIT_R` panel.
- Frozen OHLCV close history.
- Development only: 2021-01-01 through 2022-12-31. 2023+ remains sealed.

## Origin return used for decorrelation
The origin is the exact underlying HGB risky-sleeve return of the affected basket, not a generic market proxy and not just one ticker. This captures the joint behavior of the actual risky exposure being protected.

For each q95 decision at close d, correlation statistics use the trailing 63 engine sessions ending at d. The 63-session horizon is inherited from the already-preregistered STEP08A LOWCORR test; it is not searched here.

A candidate requires at least 40 finite paired observations in the 63-session window. Downside statistics condition on origin-return < 0 and require at least 10 finite downside observations.

## Health filter and outside option
A basket ETF is considered eligible for rotation only when its authentic `TIT_R` on the latest causal score date is strictly greater than BIL's `TIT_R` on that same score date. Current leader and satellite are excluded. If no eligible ETF exists, use BIL.

## Frozen policies
All are single-destination 100% replacement policies for the already-frozen 10-session action window; afterwards the path returns to exact FUSION1.

### C1 — INV_CORR_MIN
Among healthy basket candidates, select the ETF with the minimum trailing-63 Pearson correlation to the exact origin risky-sleeve return. If no valid healthy candidate exists, use BIL.

### C2 — INV_DOWNSIDE_BETA_MIN
For each healthy candidate compute downside beta conditional on origin-return < 0:
`beta_down = Cov(candidate, origin | origin < 0) / Var(origin | origin < 0)`.
Select the candidate with minimum downside beta. If no valid healthy candidate exists, use BIL.

### C3 — NEG_DOWNSIDE_THEN_TITR
First require a healthy candidate to have downside beta <= 0. Among those candidates choose the highest authentic `TIT_R`. If no candidate satisfies both conditions, use BIL.

This is the primary structural test because it is lexicographic rather than coefficient-tuned: protection property first, alpha rank second.

## Diagnostics only
For each decision record ordinary correlation, downside correlation, downside beta, destination, TIT_R, realized event utility and comparison with FUSION1/BIL. No diagnostic may alter a policy after replay.

## Development gate
A policy qualifies only if versus FUSION1 over 2021-2022 all are true:
- delta CAGR >= -0.50 pp;
- delta mean MaxDD >= +0.50 pp;
- delta p10 MaxDD >= +0.50 pp;
- delta worst-decile MaxDD >= 0;
- delta mean MaxDD >= 0 separately in 2021 and 2022.

If no policy passes, STEP08E2 is rejected before holdout and research proceeds to the already-specified STEP08F event-time Titanium-ranking lane. No threshold, lookback, beta cutoff, trigger, holding period or weighting is retuned after seeing STEP08E2 results.
