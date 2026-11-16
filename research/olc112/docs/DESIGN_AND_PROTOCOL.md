# OLC112 — preserve invested monthly rotation while testing daily protection

Predeclared after inspecting OLC111 results on16 November2026, before any OLC112 return. This is an explicitly adaptive **mechanism ablation**, not an independent holdout or a new options-information discovery.

## Why this additional comparison is necessary

OLC111 primary next-Close results were negative: BASE22.57% CAGR, PRICE18.56%, VIX17.18%, TERM15.95%. TERM's prequential MSE was worse than VIX for all three action heads. That information hypothesis remains rejected; this experiment cannot retroactively change its result.

OLC111 also changed the default monthly behavior: if a learned fresh-switch value did not pass its buffer, HOLD skipped the monthly rotation. MEAN made no learned interventions and consequently retained the old book after readiness, yielding16.23% full-window CAGR. A protection overlay should also be examined while preserving the existing invested selector's monthly behavior. OLC112 changes exactly that mechanism.

## Fixed rule

All OLC111 input vintages, candidates, fees, execution conventions, model coefficients, bootstrap buffers and monthly training cutoffs are unchanged. Reuse the already saved fit objects and model hashes; no new training, threshold search, feature search, horizon change or historical model selection.

- Initial entry and pre-readiness monthly behavior remain the frozen baseline.
- After all three heads are ready, **when invested at a scheduled monthly Close and no order is pending/queued**, submit the frozen baseline target with its original non-forced3% rebalance band. Do not require a learned FRESH approval, and do not evaluate a CASH override on that same monthly Close.
- On nonmonthly invested dates, use exactly the OLC111 CASH/FRESH/HOLD rule.
- When the actual account is all cash, use exactly the OLC111 ENTRY/STAY_CASH rule even at a monthly boundary. No forced monthly reentry.
- Pending/queued orders suppress new discretionary decisions. Actual units and cash remain authoritative.

This intentionally forgoes a new cash exit on the monthly Close itself. A learned exit can be evaluated at a subsequent nonmonthly Close. The cash reentry rule can still remain out for long periods, and its conservative buffer may miss rebounds. Neither behavior is adjusted after seeing OLC112 results.

## Arms and comparisons

Four arms: `MEAN_ROTATION`, **`PRICE_ROTATION` (primary)**, `VIX_ROTATION`, `TERM_ROTATION`. The primary uses price/account information because OLC111 did not support adding the options block; this choice is made after those observed results and is exploratory.

Three unchanged scenarios: `NEXT_CLOSE` (EUR1+15bp), `DOUBLE_COST` (next Close,EUR2+30bp), `NEXT_OPEN` (EUR1+15bp). Exactly12 new full accounts. Reuse the six OLC111 BASE/STATIC_75 control paths for matched comparisons; no need to rerun them. Every learned arm is also compared with its corresponding OLC111 arm to isolate the default-rotation mechanism.

Use the same common post-warmup interval, first execution2022-07-04, with actual preceding Close NAV. Keep full period2020-03-02–2026-10-30 separately. Do not attribute warmup returns to the learner. Preserve every result, including failures and sensitivity reversals.

## Evaluation and limits

Report native CAGR, sampled MaxDD, cash days/exposure, turnover/costs, actual interventions, annual contributions, source-mark support and common post-warmup results. Verify MEAN_ROTATION against BASE where the saved mean fits authorize no discretionary actions; any difference must be explained, not tuned away.

OLC111's forecast ledger remains the source for signal quality; its action-conditioned21-session means are not causal realized gains of the repeated OLC112 policy. Restoring monthly behavior does not repair poor forecasts, create an untouched test, or guarantee the user's30% CAGR target. Repeated-action continuation and state-coverage limitations remain. Any path with unsupported held marks or fewer than12 separated actual action-family interventions has an explicit evidence limitation.

Complete this one structural comparison, review the actual ledgers and preserve both OLC111 and OLC112. No retrospective parameter sweep or silent replacement of earlier results.
