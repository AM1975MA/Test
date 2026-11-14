# OLC106 — Multi-universe automatic-allocation research screen

Date: 2026-11-14. Research only. No trades, no live alerts, no changes to OLC19/OLC67 or main. This protocol is frozen before OLC106 economic outcomes; all historical windows were previously examined and are NOT pristine holdouts.

## User mandate
Monitor a broad Trade Republic-accessible ETF set covering World, Europe and USA exposures; actionable infrequent allocation/risk alerts. Desired calendar CAGR >=20%, absolute historical MaxDD <=25%, and CAGR/abs(MaxDD)>=1. These are research acceptance criteria, never guarantees. No leverage or shorts. The user requires backtests before any live decision.

## Universes and currencies
1. EU165 original European-listed funds, excluding synthetic cash columns.
2. USA149 original US-listed research universe; native USD performance is NOT EUR performance and is NOT evidence of Trade Republic retail eligibility.
3. TR29 frozen OLC105 ISIN set in EUR, which already includes European, US and global underlying exposures, not 29 World funds.
4. EU194 = EU165 plus TR29 (deduplicate identical instrument IDs; economic overlaps handled by the predeclared correlation rule). Original EU165 Trade Republic account availability is not certified; this combined universe is research-only.
No EUR/USD price pooling without a historical FX source. Daily inputs from the immutable OLC104/105 archives; use existing audited OLC100 append-only prices where compatible. No new instrument chosen after performance is known. Hash every source. Preserve OLC105's issuer-verified P500 split repair, and raw files. Do not modify unknown corporate actions or interpolate execution prices.

## Dates
Primary common window: first Open 2020-03-02 to Close 2026-10-30 (completed calendar months). Sources have later data; show any partial period separately. Pre-2020 history is warm-up, not hidden performance. Report calendar-year and 2020-24 / 2025-26 chronological descriptive subwindows, without reselecting parameters. Pandemic drawdown before the common start is not captured.

## Five fixed arms, same rules for every universe
B0 PASSIVE: EUNL.DE for EU165, SPPW/IE00BFY0GT14 for TR29/EU194, ACWI for USA149; no rotation. The passive comparators do not match the candidate's factor/risk exposure.
B1 MOM252_TOP2: top two trailing 252-session total-return proxies, monthly equal-weight, no other protection.
A0 DIVERSE_TREND: monthly ranking by mean of annualized log-momentum at 63/126/252 sessions, divided by 63-session annual volatility; requires positive 252-session momentum and Close above trailing 200-session mean. At least 253 valid historical observations; at least 95% observations within trailing 253 calendar-session slots; latest observed quote within five calendar days. Ties sorted by instrument identifier. Greedy selection of up to six candidates with pairwise trailing 126-session correlation <=0.90. Inverse-volatility weights, individual maximum 25%; cash retains any unallocated weight when fewer than four candidates. No leverage.
A1 DIVERSE_RISK15 (primary candidate): A0 with covariance-based ex-ante annual portfolio volatility target 15%, scaling gross down only, never above 100%. Monthly normal rebalance. Daily risk check reduces exposure if current forecast volatility exceeds 18.75%; action at the next eligible Open. No upward daily rescaling between monthly reviews.
A2 DIVERSE_GUARD (secondary): A1 plus close-observed portfolio drawdown guard. Drawdown from the controller's active-cycle high-water at or below -12% caps exposure at 50%; at or below -18% requests liquidation. Minimum 20 market sessions in cash. Re-entry only at a monthly decision when the fixed passive reference is above its 200-session mean with positive 21-session momentum and at least four trend candidates exist. Re-entry at 50% of A1 target; normal exposure allowed after 20 sessions. Controller high-water is reset on re-entry only; reported portfolio drawdown NEVER resets. Guards are delayed alerts, not guaranteed-stop fills and not guaranteed drawdown caps.

## Execution and costs
All decisions use completed prior closes only. Orders filled at next observed eligible Open; base latency zero extra sessions, sensitivity one/two EXTRA sessions for both allocations and risk alerts. No missing Open filled with a Close. Concurrent conflicting alerts resolved by latest known instruction; risk exits take priority. Cash earns zero; taxes excluded.
Common screen uses 10,000 native currency units, cost 1 native unit per instrument order plus 15 bp one-way adverse execution. Other costs 0/0, 1/5bp, 1/30bp with no refit. This is a model, not an observed Trade Republic spread. Do not claim EUR/USD equivalence of flat tickets.
Rebalance no-trade band 3% of portfolio per instrument except mandatory exits. Self-financing, no borrowing. Fractional adjusted economic units permitted for the first signal screen; this is explicitly NOT a whole-share brokerage replay. Any interesting candidate requires a separate raw-price/corporate-action/whole-share replay before adoption. Do not round split-adjusted prices and call them physical shares.

## Verification and reporting
TDD for causality, capped allocation, missing Open, self-financing, order costs, drawdown governor and re-entry, lag, passive benchmark ratio and metrics. Independent recalculation from saved NAV and orders. Report CAGR calendar, cumulative, max drawdown close/open sampled, Calmar, downside periods, recovery duration, allocations/exposure, alerts/orders, turnover, costs, deferred fills and data warnings. Report every fixed arm, not just the best.
Report results as sensitivity to this proposed new rules-based architecture, not OLC19/67 or already validated alpha. No parameter sweep, market-specific winner, or optimised combination after seeing the outcomes. Passing target in historical data is a numeric screen only, not permission for live trading. Failing target is reported without retuning.

## Implementation plan
- [ ] Verify source hashes, price masks and dates; prepare four frozen price panels and document limitations.
- [ ] Write and observe failing tests, then implement independent causal strategy/portfolio engine.
- [ ] Run all five arms across all four universes, cost and reaction-lag sensitivities.
- [ ] Recalculate metrics/costs independently, inspect exceptional returns and behaviour.
- [ ] Save scripts, source hashes, numerical results, tests and final report on this research branch and in a downloadable bundle.
