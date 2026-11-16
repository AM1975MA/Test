# OLC114 — complete-cycle, per-position design review

Methodological review before new labels, fitting or portfolio returns. This note proposes implementation details for the root author's protocol; it is not itself the frozen protocol and does not report a successful strategy.

## 1. Recommendation and attribution

The proposed architecture is a useful next mechanism test: one temporary position-level plan is selected and actually executed through its prescribed reentry and monthly handoff. Its label must simulate exactly that same plan. The other position's economic units remain untouched by discretionary instructions.

OLC110 already tested targeted position exits and fast/slow/staged/fresh reentry. The novel combination here is learning the economic value of a **complete bounded plan** and then committing to that plan. It is not merely the existence of per-position stops or frequent opportunity searches.

OLC113 repairs the missing scheduled reentry of OLC111/112. OLC114 must retain that repaired monthly behavior for every account, including cash. Any gain over OLC112 alone would confound the known repair with the new architecture.

## 2. Complete-plan contract

At a nonscheduled, idle decision Close k, with no active plan, evaluate two plans for every materially held position j:

- PARK(j): sell only j at the next accepted execution; preserve that cash until the next monthly baseline instruction.
- REDEPLOY(j): the same targeted sale; at the first permitted weekly decision after confirmed liquidation and before monthly handoff, choose a compatible candidate from the frozen selector's ordered target list at that later date; buy using actual available cash; preserve unaffected units; hand back at the next monthly event.
- BASE is the no-intervention comparator and the zero-advantage default.

One active plan blocks every further discretionary plan until handoff. Monthly baseline instructions take precedence over entry attempts, use force=False and the existing 3% band, and terminate the discretionary plan. Native pending/queued-order semantics remain authoritative.

Details that the protocol must decide explicitly:

1. **Entry timing:** recommend a weekly signal index strictly greater than the actual final liquidation execution index. This avoids ambiguity about an entry decision on the same Close that completes the sale. Execution of the new buy is still no earlier than a later accepted bar.
2. **No candidate at the attempt:** recommend exactly one attempt; if the ordered current target list has no admissible candidate, REDEPLOY remains cash until monthly handoff. Retrying every later weekly date is a different plan and must not be introduced silently.
3. **Entry budget:** use the actual available cash while keeping all unaffected units fixed. Do not silently target 50% if the sold leg had drifted to another weight. Existing cash can be included consistently, with native fees and affordability scaling; log that choice.
4. **Candidate rules:** require current liquid eligibility and observed accepted signal Close; exclude all retained assets; require trailing126 correlation <=0.85 against every retained position. Allow the outgoing asset if the frozen recipe currently selects it and it satisfies those rules. No preferential return to it.
5. **Candidate order:** use the selector's explicit selected_indices order, not sorted ISIN order or the order of nonzero NPZ weights. The weights cache alone does not preserve the original leader/challenger ordering.
6. **No weekly date before reset:** REDEPLOY degenerates to PARK; record this rather than fabricating an entry.
7. **Missing sale quote:** no cash or vacancy exists until actual liquidation. A monthly handoff can supersede the pending plan through the existing engine rules; no synthetic fill is allowed.
8. **Small held residuals:** define whether every positive economic holding or only a weight at least the existing 3% band is a candidate. Avoid fitting a new cutoff; using the existing economic-band rule is a defensible implementation choice, but BASE comparison and unit tests must reflect the exact choice.

## 3. Labels and fixed terminal

All plans and BASE start from identical actual quantities and cash. Use a common terminal Close k+42, not the most profitable entry or handoff date. After the next monthly handoff, every branch follows the same ordinary baseline continuation through that terminal. Retain ordinary transaction costs, fills, gaps, netting and source-mark support.

Target for plan p: y_p = log(NAV_p[k+42] / NAV_BASE[k+42]). It includes sale, attempted replacement and subsequent monthly transaction costs. Mark terminal inventory rather than forcing a fictitious liquidation.

Distinguish control handoff from complete execution: the plan ends when the monthly baseline takes control, while resulting baseline orders may still be pending. Keep native pending outcomes at the common endpoint and report any incomplete execution. For causal source failures, censor the matched comparison group with an explicit reason; never turn an unavailable or right-edge label into zero.

The final months can contain right-censored actual plans even though they belong in the account return. Report them separately from complete-cycle event evidence. The known terminal month-end may be used in calendar features even when the backtest cannot execute a signal beyond its last price date.

For efficient native replay, a subset may include the union of all potential future scheduled targets and weekly candidates through the terminal. That future union is only an implementation device for available price columns; current features and current policy decisions must never consume future target identities. Preserve global ISIN mappings and candidate order in every subset.

## 4. Training-state coverage

A baseline-state bank is a defensible **reference-policy training distribution** for this first test because active plans prevent repeated discretionary decisions until the monthly handoff. It is not on-policy.

Even after handoff, the 3% nonforced band, fixed ticket fees, gaps and delayed fills can leave different NAV, cash, weights and possibly residual holdings from those of the baseline bank. A common monthly recipe does not prove identical states.

I would not combine this first experiment with an additional adaptive roll-in/state-aggregation learner. That introduces another methodological change and risks regenerating past states with later fitted models. Instead:

- Fit on the fixed reference-state bank and describe it honestly.
- Include leg weight, retained-basket state and ticket/NAV burden in the features.
- Save every actual free-decision state and its feature values.
- Audit actual versus training support with standardized feature ranges and nearest training-state distances; do not tune a clipping or rejection threshold after seeing performance.
- If distribution shift is material, report that failure and make chronological own-state aggregation a separate experiment.

If own-state labels are later used, retain only states actually recorded during the historical prequential rollout. Add a state to training only when its whole42-session outcome matures. Do not recreate old states using a model trained with later data.

## 5. Suggested small feature block

Use separate PARK and REDEPLOY heads, pooling held-position rows within each head and giving every signal date total weight one. Features are available at the initial decision date, not at the future entry attempt.

PARK, eight features:

1. Held leg NM21: trailing21 log return / (sigma63 * sqrt21).
2. Held leg NM63: trailing63 log return / (sigma63 * sqrt63).
3. log(sigma21 / sigma63) for that leg.
4. Held leg sigma63 * sqrt252, retaining absolute risk scale.
5. Actual current leg weight in whole-account NAV.
6. Retained-basket NM21 using current retained weights; zero for an empty retained basket.
7. Known sessions to the next monthly signal /21.
8. Current primary ticket charge / actual NAV, to represent fixed-fee scale.

REDEPLOY adds four:

9. Indicator that a compatible candidate exists in today's ordered frozen target list.
10. Today's candidate NM21 minus held-leg NM21; zero when unavailable.
11. log(today's candidate sigma63 / held-leg sigma63); zero when unavailable.
12. Known sessions to the next weekly signal /5.

Use the existing declared volatility floor. This candidate is only a description of the current opportunity set; the actual later entry candidate is determined at its own future decision time. No future candidate identity, future liquidity, realized future wait length or future reentry price belongs in X.

An unavailable current candidate does not necessarily make REDEPLOY illegal: the strategy may find one by its later attempt. Its indicator and zero-filled opportunity features distinguish the current state.

These are proposed price/account features, not a claim of novel information beyond earlier research. No VIX block is justified by the failed incremental tests.

## 6. Models and readiness

Use the same labels, date weights, chronological cutoffs and initial warmup for every model:

- MEAN: training-only average per plan family.
- RIDGE: primary, training-only standardization, mean-loss L2 slope penalty fixed before results; intercept unpenalized.
- One optional nonlinear secondary: a regression tree with max_depth=2, min_weight_fraction_leaf=0.20 and fixed random seed. At most four leaves; no depth, leaf, feature or threshold grid. It changes the learner, not the architecture, and must be compared with RIDGE on identical complete-cycle data.

Keep primary costs for the bank and models. Stress accounts reuse the saved models; they use their own actual holdings and NAV but must not be refitted for their scenario. The ticket-burden input should retain its declared primary-cost interpretation if stress is meant to isolate execution/cost changes rather than a redesigned forecast rule.

Suggested readiness: at least504 distinct mature signal dates, at least24 distinct signal calendar months and at least12 greedily nonoverlapping42-session outcome windows, separately for both heads. Require all heads before any discretionary plan. Terminal index must be strictly less than monthly fit cutoff.

**24 months are not24 independent observations:**42-session outcomes cross month boundaries. Report all three counts. Requiring24 genuinely nonoverlapping42-session windows would consume roughly four years of this panel before activation and materially shorten evaluation; if chosen, show that cost explicitly.

Do not reuse OLC111's hard-coded21-session nonoverlap counter. Use actual interval endpoints. Bootstrap paired complete calendar blocks of at least63 sessions across both heads and all models, retaining all rows from each date. A lower10th-percentile action buffer remains a heuristic, not calibrated90% confidence. The effective block count and sparse regimes limit any reliability claim.

## 7. Decision rule and comparisons

BASE has predicted advantage zero. For every legal plan, require positive mean and positive lower buffer; choose the largest lower buffer with a declared deterministic tie rule. Costs are already in net labels and must not be subtracted a second time. A missing or unsupported required feature cannot authorize a plan.

The minimal architecture comparisons are BASE, STATIC_75, the corrected OLC113 PRICE_RESET mechanism, complete-cycle MEAN, complete-cycle RIDGE and optional complete-cycle TREE. If practical, run the full-account PARK/REDEPLOY controls as the same labels with constant means; do not confuse mean-value selection with a no-intervention control.

Use next Close, doubled next-Close costs and one extra Close execution session. The delayed scenario must also delay plan liquidation and therefore may change the first permissible weekly entry; never hold the normal-cost entry date fixed when the account has not sold yet.

Report matched full periods and the new model's own common post-readiness period. Recompute BASE on that new period rather than reusing OLC111's July2022 segment automatically. Keep annual2024 and all other years, plus original fixed historical segments, visible.

## 8. Forecast and power evaluation

Separate forecast MSE/bias, action-value ranking/regret and complete-account economics. Predictive MSE alone is not the portfolio objective, but a model consistently worse than its mean control cannot be described as demonstrated forecasting skill because one account path wins.

Report complete active-plan counts, plan-family counts, number of distinct affected ETFs/exposure groups, calendar months and nonoverlapping42-session episodes. Thousands of correlated leg/date rows do not create thousands of independent market regimes. A four-leaf tree at minimum readiness may still have only a few independent42-session episodes per leaf; its role is exploratory.

Compare against the previously declared material criterion (+3pp CAGR with no worse sampled MaxDD on full and common active periods), the separate30% aspiration, and cost/delay consistency. Do not replace a failed primary by a favorable secondary after results.

## 9. Failure modes to audit directly

- A future-entry candidate or realized liquidation time leaking into initial features.
- Sorted NPZ nonzero indices replacing the selector's explicit order.
- A weekly entry using cash before liquidation or entering on a monthly handoff date.
- A targeted plan selling or rebalancing unaffected units.
- A 50% replacement target silently changing the intended cash budget after weight drift.
- A persistent pending sale or buy being overwritten by a new discretionary action.
- Baseline-only training described as on-policy.
- Counting overlapping monthly labels as independent.
- Choosing profitable or variable endpoints rather than the fixed42-session boundary.
- Excluding final censored plans from account returns or counting them as completed event evidence.

No new financial path, label bank or fitted model was generated during this review.
