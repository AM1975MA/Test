# OLC111 — option term structure and daily economic action values

Frozen design before new forecasts or financial results, 16 November 2026.

## Objective and prior evidence

Test whether **new information**, the shape of SPX option implied volatility across 9-day, 30-day and 3-month horizons, improves daily decisions to hold the actual ETF account, sell it to cash, or buy the fresh basket selected by the unchanged OLC109 selector. The user's approximately 30% CAGR objective is a target, not an assumed attainable result. The full research history and 2020–2026 outcomes have already been inspected: this is exploratory chronological validation, not an untouched holdout.

Prior studies already tested VIX level, state-aware action learning, broad ETF breadth, many technical features, and native counterfactual accounting. None of those is claimed as new. The source review and design memo under `research/` preserve that evidence. OLC110's dynamic protection rules failed; do not conceal them or revise their results.

## Fixed data, selector and accounts

- Frozen 2,096-ISIN EUR Xetra ETF panel, 2019-02-01 through 2026-10-30; original price/quality/liquidity masks and the current-catalog/survivorship and adjustment-vintage limitations remain.
- Fixed `DEDUP_DUAL_TREND_OPP` candidate selector, unchanged from OLC109/110. It chooses from the contemporaneously eligible liquid subset, not literally all listed ETFs on every date.
- EUR10,000 initial account, fractional economic units, long-only, no borrowing, cash return zero, no taxes. Original self-financing rebalance implementation and its 3% band, delayed-fill and immutable-instruction semantics remain.
- Primary execution: the following accepted **Close**, normal costs EUR1 +15bp per actual executed order. Sensitivities: next Close with EUR2 +30bp, and the prior next-Open convention with EUR1 +15bp. Open availability uses final daily-volume information; that convention is a sensitivity, not certified opening-auction executability.
- Source files and prior code remain unchanged. New engine only adds seeded-account replay, optional suppression of initial instruction, and permission for a scheduled HOLD to submit no instruction. No live orders, scheduled tasks, or production workflow changes.

## Information ablations

Four matched learned controls: `MEAN`, `PRICE`, `VIX`, `TERM`.

`MEAN` is a training-only historical advantage mean. `PRICE` has only the small price/account feature set below. `VIX` adds log(VIX) and its 21-source-session log change, an existing information family. `TERM` additionally adds log(VIX9D/VIX) and log(VIX/VIX3M), the new hypothesis. VVIX and SKEW were downloaded for possible later research but are **not used** or searched in this study.

Each source date must be strictly earlier than the European decision date; the latest prior observation must have the same date across all three indices, be positive/finite and at most seven calendar days old. No same-date US final Close is used at a European Close. All four learners use the same complete-case label and option-feature training support. A missing option feature at inference falls back to the matching PRICE model and is logged.

## Decisions, labels and continuation

At every decision Close, snapshot the actual units, cash and NAV. Suppress new discretionary decisions while an instruction is pending/queued. Initial entry and model warmup follow the frozen monthly baseline. Once models are ready, the learned policy can HOLD or stay in cash at a monthly date too; monthly scheduled reentry is not compulsory.

HOLD means no order, preserving economic units. CASH sells all actual inventory. FRESH submits the unchanged selector's current target and can be a switch or an entry. A fresh target less than 3% in total absolute weight difference from the actual account is a no-op and is not acted on or labelled. A fresh basket with zero exposure is unavailable; cash is a separate action. All discretionary orders are forced after the explicit no-op filter; remaining account/execution constraints are unchanged.

The trigger-independent training bank has two states per eligible date: the actual frozen **primary-execution baseline** book, and a hypothetical all-cash book with the same NAV. The latter is a conditional training state, not a claim of a free historical liquidation. Label both possible interventions in the invested book and entry in the cash book. Keep all legal observations, rather than only historical stop events.

Each comparison starts from identical units/cash. The initial action is placed at Close k and executes no earlier than k+1. After that intervention, **all branches follow the same frozen monthly baseline at future dates j > k**, through terminal Close k+21. A HOLD at a monthly k skips that date's baseline instruction. Targets at future monthly dates are computed only from information available at those dates. No learned continuation enters labels.

Three action heads predict native net log-wealth advantages: CASH−HOLD, FRESH−HOLD, and ENTRY−STAY_CASH. Costs are already in labels; do not charge them again as a prediction hurdle. Terminal accounts are marked, not fictionally liquidated. Known native nonfills remain outcomes. An unsupported valuation censors the whole comparison; terminal holdings require a positive finite accepted causal mark no more than five calendar days old, and any intervening held-book valuation must meet this condition. Right-edge k+21 comparisons are pending, not filled with zero. Store censor reasons and endpoint dependencies.

These labels describe a one-time intervention against frozen continuation. Repeated daily decisions have a different state distribution and continuation. Actual complete-account replay is therefore necessary, and its result is not guaranteed by positive mean label values.

## Features

For a basket with today's actual weights, form descriptive trailing constant-weight daily simple returns (cash return zero) from trailing ETF returns, then take log returns. This is a description of present exposures, not a historically funded basket. Use daily volatility floor 1%/sqrt(252). NM21 and NM63 are trailing log returns divided by trailing 63-day daily volatility times sqrt(horizon).

- CASH: held NM21, held NM63, log(held vol21/vol63), representative breadth63, sessions to next monthly event /21, actual gross exposure.
- FRESH: fresh−held NM21 and NM63, log(fresh vol63/held vol63), held/fresh correlation63, sessions to next monthly event /21, actual gross.
- ENTRY: fresh NM21, NM63, log(vol21/vol63), representative breadth63, sessions to next monthly event /21.

Representative breadth is the fraction of liquid representatives with positive m63. Use the original complete-linkage 0.85 groups at the initial date and each monthly Close; carry their representative identities forward and drop representatives no longer liquid at the current date. No future group is used. The next monthly event means strictly after the current decision, including when today itself is monthly. It is a known exchange-calendar schedule, not a future-price feature.

## Fitting and action rule

Monthly expanding refits at the first panel session of the month, clipped to the initial decision date; the cutoff does not move later because a bank row is missing. Outcomes must have terminal index **strictly less than** the fit cutoff. Require 504 distinct mature valid dates and at least24 greedily separated 21-session outcome blocks per head. All three heads must be ready before any learned override, avoiding a CASH exit before an ENTRY model exists and preserving matched warmup across arms. Earlier decisions remain baseline. Report each head's first ready date, and distinguish full-window warmup from the common post-warmup period.

Training-only standardization; residualize the legacy VIX block against price/intercept, and the term block against price+legacy/intercept, using training-only least squares. Standardize residuals on training data. Ridge minimizes date-weighted **mean** squared error plus 1.0 times squared slopes; intercept unpenalized. No penalty, horizon, threshold or feature grid. Date balancing prevents duplicate state rows from multiplying market episodes.

Use100 fixed-seed paired bootstrap resamples of whole63-session date blocks. Keep the full-training representation fixed during coefficient resampling. The10th percentile of conditional-mean predictions is an action buffer, **not a calibrated90% confidence statement**. An action requires both positive predicted mean net advantage and positive lower-buffer value. Choose the action with the largest eligible lower value, with deterministic CASH before FRESH tie resolution; HOLD/STAY_CASH has value zero. Missing head/model/feature support cannot authorize that action. Before the required models for the current state are ready, a monthly date retains the frozen baseline; between monthly dates it holds.

## Predeclared runs and evaluation

Exactly six account policies (`BASE`, `STATIC_75`, `MEAN`, `PRICE`, `VIX`, `TERM`) in three execution/cost scenarios,18 complete paths. Label bank and model fits use primary next-Close normal costs only. Stress scenarios reuse those frozen fits and apply them to their own actual accounts; do not refit to make costs or execution stress look better.

Write a prequential forecast ledger before interpreting portfolio performance. For each head compare MSE, bias, prediction bins and action-conditioned realized advantage with MEAN and PRICE; attribute TERM increment specifically against VIX. Report dates, censoring, model hashes, first-ready dates and number of nonoverlapping episodes. Overlapping21-session advantages are not additive and cannot be annualized into CAGR.

All18 paths are run for economic diagnosis even if forecast gates fail. A failed gate bars promotion, threshold relaxation, feature expansion or a claim of discovered alpha. Report CAGR, sampled MaxDD, exposure, cash days, costs, orders, year contributions, drawdown/recovery periods and post-warmup results against the same-date controls. Fewer than12 separated realized interventions per action family is insufficient evidence of reliability. No model is promoted merely because one full-sample CAGR exceeds30%.

## Bounded completion

Complete source alignment, common-state labels, causal models, full account replays, one independent review, and save the complete study on a new branch of AM1975MA/Test. Preserve negative results. No retrospective threshold search, no rerunning all older research, no claims that prospective performance is established.
