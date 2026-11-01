# OLC-08 — controlled whole-chain reassessment

1 November 2026. The user requests reevaluation and improvement of every step of the best strategy. There is no demonstrated single winner on return and risk in both markets. This experiment therefore preserves CL01 P0 HALF IMMEDIATE, DELAY3 and PHASE5 as a reference frontier, with DELAY3 the growth-oriented local anchor, not a globally optimal or approved strategy. The legacy Original39/Stage19 and native European reports remain distinct historical anchors. Main and live trading unchanged.

## Scope and nonclaims
Reassess the entire chain through a coverage register: raw universe/total return/FX; temporal eligibility; feature/label/train identity; experts; blend and lag; selection; weights; actual-incumbent persistence; transfer timing; exposure/V6/systemic/stop; fees/fills; inference; preservation. Status per step must distinguish inspected, replay-tested, changed, unresolved and not executed. This lot uses the authenticated P0 annual CL01 forecasts, not new ranker fits. Alternative-calendar fits were already studied in OLC07; no results from that study are relabeled new. Fundamental metadata, delisted funds, distributions, FX hedging and true live fills are not certified by this lot.

All controls and candidates must be run on USA149 and EU165, same specification and cost convention. No rejection solely because an uncertainty interval includes zero. No US+EU average may conceal material damage in one market. No reinvention of CASH/HOLD learned vetoes whose earlier tests failed. No silently changing the baseline to the winner of another window.

## Frozen inputs and dates
OLC06 checkpoint SHA256 7e3a23176e27813b324a4fed275965b6644b4dd97ae8f33a31061c0b518319aa. OLC07 results ZIP SHA256 0e7494b173d769394900876ac1d3e6c45388294d1635dd63f8ccb4128322e2c8. Its P0 forecasts provide Return, ET and XGB values on genuine month-end signals. Preserve own as-of dates and missingness. Compare on the same actual next-Open valuation dates, exclude the terminal flat observation. Main diagnostic window 2021-2024; 2019-2020, 2025, 2026partial and full2019-July2026 shown separately. These dates are already researched, not virgin out-of-sample. No unseen future period is used for choosing parameters.

## Experts and blending
Five fixed score contracts, with no search for the best blend after outcomes:
- CL01: .475 Return percentile + .525 power1.1 of (.4 current+.3 previous+.3 two-back) Hybrid; Hybrid=.6ET+.4XGB.
- RETURN_ONLY.
- HYBRID_ONLY, same original smoothing and power.
- CURRENT_HYBRID: original blend but no historical Hybrid smoothing.
- RANK25: .25 Return percentile + .75 cross-sectional percentile of original smoothed Hybrid. This was previously promising but unstable; here its interaction with execution is examined, not called a new discovery.
All use the same contemporaneous common support; missing forecasts are not zero. Preserve the exact first-two-period lag initialization used in the parent. Verify CL01 scalar scores and final selections exactly before attributing differences.

## Selection, weights and persistence
Fixed alternatives:
- TOP2 original names.
- DISTINCT: retain first leader, choose the next highest of Top5 with trailing correlation <=.90 to it, else original second. Correlation computed on at least84 shared historical observations in126 sessions, strictly at signal time. This is a statistical concentration filter, NOT certified economic deduplication. No post-hoc category exclusions.
- BUFFER4: on a monthly event retain actually held primary names that remain in current Top4, prioritized by actual prior-close holding weight, fill by current rank until two. No future outcomes or hypothetical momentum incumbent.
Weight alternatives: equal half, or inverse prior63-session volatility capped in [.4,.6] for a two-name pair. Missing/insufficient covariance uses equal weights, recorded. Weights held between events. Also retain original legacy score-margin weights as a separate control, not included in equal/inverse-weight claims.
Execution alternatives: IMMEDIATE, DELAY3, PHASE5 exactly as OLC06. No new delays or phase tuning. Initial/reentry from no primary holdings follows original contract. The complete 5score x3selection x2weight x3execution structure isolates interaction effects; every cell goes to both markets and both fee levels. This is a bounded factorial, not 180 independent strategies or statistical observations.

## Risk, accounting and executable information
Original daily exposure g and V6 targets remain frozen for initial comparisons to isolate each step. Explicit independent ablations on CL01 TOP2 HALF for each execution: no DDgross, noV6, no systemic trigger, no conditional stop, no risk controls, fixed75% gross cap. Stop-induced cooldown and systemic cooldown are declared shared mechanisms; disabling one trigger does not silently disable the other. Never call removal of a protection an improvement from CAGR alone.

Implement separately a previous-session information contract: lag gap and breadth used both for systemic decision and stop arming by one session; do not use current opening breadth to place an order retrospectively at that same opening. Original prices still mark/fill the orders. This is a conservative alternate timing contract, not a certified live replication or a predicted opening gap.

Implement optional exact proportional one-way fee accounting: solve F=c*sum_i|target_i*(V-F)-old_notional_i| on the aggregate tradable book; EUR cash pseudo-accounts are not securities, BIL/SHV are. Net overlapping primary/V6 sleeves by ticker for fees. Charge actual stop sells once, record slippage separately. Preserve the full original ledger schema and legacy-fee mode so all original arrays can be verified. The new .001/.003 one-way schedule is NOT numerically the same price assumption as legacy .001/.003 half-turnover; the bridge shows this rather than attributing the lower net return to alpha.

Replay prior-known-timing/exact-fee checks for five predeclared structural variants: baseline; inverse-vol-only; DISTINCT-only; RANK25-only; RANK25+DISTINCT+inverse-vol. Each with all three executions, both markets and both costs. Keep the original timing/legacy-fee ablations separately. Do not choose timing to rescue performance.

## Stepwise evidence and acceptance
First reproduce original controls. Then audit learned-score utility and same-support forward outcomes at21/42/63 with genuinely observed Open endpoints, including absence of labels, rather than summing overlapping returns. Then run isolated and factorial structural comparisons, independent risk ablations and execution/cost bridge. Select no production configuration from the largest historical CAGR. Report improvements versus local parent and versus immutable anchors separately, parameter/period/market tradeoffs, added turnover/positions/drawdown and actual decision examples.

For meaningful increments compute paired monthly log contrasts with common USA/EU block indices, 6000 circular bootstrap draws, blocks3 and6, seed20261101. Label positive draw fractions resampling stability, never posterior success probabilities. Show within-family multiplicity/selection sensitivity and maximum-drawdown changes; no p<.05 or95% threshold automatic gate. A shortlist may be generated by worst-market net log improvement and risk/complexity tradeoff, but is descriptive post-selection. No claim of statistical confirmation after reusing the same history.

## Verification and preservation
Tests before new implementation: baseline parity, no future signal statistics, unique selection/alias behavior, actual incumbent buffer, missing forecast/quote handling, cap normalization, isolated risk switches, fee fixed-point and capital conservation, stop friction exactly once, prefix invariance. Independently reconstruct every final NAV from quantities and next observed/carry valuation and recompute reported metrics. Run inherited tests in their defined roots, not a false whole-repo-green claim. Self-review is labeled as such.

New complete sources, test code and compact results will be versioned on research/olc08-whole-chain-20261101. Full paths/input-dependent checkpoints are delivered separately unless actual remote content/hash is verified. The historical full-binary GitHub gap is not silently declared fixed. No local process is presumed to run after the response and no training is promised in background.
