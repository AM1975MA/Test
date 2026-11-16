# OLC114 — Complete, bounded protection and redeployment plans

**16 November 2026. Adaptive exploratory research after OLC111–113. This protocol precedes all OLC114 market-data labels, fitted models and account returns.**

## Problem and chosen approach

OLC113 restores the monthly continuation omitted by OLC112 cash accounts. Its primary PRICE_RESET reaches 24.1622% full-period CAGR and 22.4209% common-period CAGR, versus 22.5708% and20.0121% for BASE. Sampled drawdown changes by only0.0016609 percentage points. It therefore fails the predeclared +3 percentage point CAGR/no-worse-drawdown criterion and the separate30% aspiration. The remaining issue requires more than restoring the monthly deadline.

OLC114 evaluates and executes the **same finite per-position plan** before handing control back to the baseline. It preserves unaffected economic units, includes the sale/wait/purchase/handoff in each target, and prohibits another discretionary plan before handoff. This differs from three independent CASH/FRESH/ENTRY heads acting repeatedly. It is not a claim that per-position stops, weekly opportunities, native economic labels, or small regressors are novel; OLC110, OLC70/74/99 and other prior studies already tested those components.

Alternatives considered: another stop/rebound threshold grid is rejected because those families already failed; indefinite on-policy reinforcement learning is deferred because of sparse independent market cycles and greater implementation/state complexity. The selected finite-plan experiment has an explicit reference continuation and a direct native-account audit.

Existing authorization covers autonomous research and saving research branches in AM1975MA/Test. No trades, production changes, main-branch updates or OLC100 changes are authorized or performed here.

## Actions and exact continuation

At a nonscheduled, noninitial Close, when the account has no pending/queued order and no active discretionary plan, consider each actually held asset j. BASE means no discretionary action. Two plan families are available:

| Plan | Immediate instruction | Later behavior before monthly handoff |
|---|---|---|
| PARK(j) | Sell only actual j units at the next accepted executable Close. | Preserve every other unit and hold resulting cash until monthly handoff. |
| REDEPLOY(j) | Same targeted sale. | At the first weekly decision Close strictly **after the final actual sale execution index**, with the book idle and before monthly handoff, make one candidate-selection attempt. Buy the selected candidate with actual available cash. If no candidate exists, retain cash until handoff. |

The fixed weekly mask is the existing `decision_mask(...,'WEEKLY')`. Entry is never assumed on the sale day, and its signal still fills at a later accepted bar. A delayed sale shifts the eligible weekly entry. There is only one entry attempt; there is no hidden retry, stop, confirmation filter, threshold search or early cycle termination after a successful purchase.

The candidate is selected **at the actual later entry decision**, from the existing DEDUP_DUAL_TREND_OPP selector's explicit `selected_indices` order. Reconstruct that order with the unchanged selector; NPZ nonzero/index order is not equivalent. Exclude every retained holding and require126-session correlation <=0.85 with each retained holding, using the existing correlation implementation. The outgoing ETF may compete again if the same selector chooses it. Current features describe only today's candidate; no future candidate or realized waiting time enters them.

The targeted entry uses current available cash/current NAV as its involved target weight and preserves all unaffected quantities. Actual affordability and fees remain native. Targeted sale and purchase use `force=True`; sale is sell-only. Do not use a blind50% entry weight.

Every scheduled monthly Close has priority: end the discretionary plan and submit the frozen full baseline target with `force=False`, including cash accounts and pending orders, preserving the original native scheduler's supersession and execution semantics. A handoff ends discretionary control; it does not assert immediate completion of delayed fills. No same-Close plan/entry may override a scheduled target. After handoff and once the book is idle, a later new plan may be selected. During an active plan, all other discretionary choices are disabled.

Initial and not-ready behavior is the baseline. Fully cash accounts with no active plan follow the baseline monthly calendar; they do not use an independent indefinite ENTRY gate.

## Native engine extension

Copy the unchanged OLC111 replay engine into `cycle_engine.py` and add one opt-in: `allow_initial_targeted=False`. It may be enabled only with a valid seeded `initial_state`. When enabled, the initial seeded callback may issue a targeted mask, preserving the other units across the next-price gap. Ordinary initial and scheduled calls retain the original restrictions by default. This enables a counterfactual plan beginning at the actual Close k without fictitious same-Close fills or a false prior-day account state. Default output parity with the original engine is mandatory.

## Training bank and reference continuation

Use the frozen OLC111 primary next-Close baseline states on every nonscheduled idle Close with held inventory. Compare BASE and all legal PARK/REDEPLOY actions from **identical actual units, cash and NAV**. The same `PlanExecutor` implements a chosen plan in labels and in the historical deployed policy.

All branches end at the fixed **k+42** Close, without fictitious terminal liquidation. The plan hands off at the next monthly date; subsequent monthly targets through the common endpoint are the frozen baseline. Target is `log(terminal_nav_plan / terminal_nav_BASE)`, net of every actual fee and accepted execution. Future candidate selection in a label occurs only when that simulated plan reaches the later decision date. Future values are outcomes, not features.

Missing terminal support/right-edge, busy initial state, invalid features, and unsupported held marks have explicit statuses. If any branch in a starting-state group lacks accepted valuation support, censor the whole comparison group, not just the losing branch. Accepted held marks may be at most five calendar days old. The BASE replay must match the original baseline's future NAV for every supported starting state within numerical tolerance.

Training states are a **reference-policy distribution**, not on-policy. Fixed tickets, gaps, nonforced bands, wealth and residual holdings can make actual policy states differ even after monthly handoff. No later-fitted model regenerates earlier training states. Record actual eligible decision states and standardized feature support. The finite plan repairs continuation within its life; reference continuation after handoff and state shift remain limitations.

## Fixed information block

Use price/account information only. No new VIX/term data, ticker identifiers or future regime labels.

PARK has eight features, in this exact order:

1. Held asset NM21 from its own unit-weight63-session return history.
2. Held asset NM63.
3. Held asset log(sigma21/sigma63).
4. Held asset annualized sigma63.
5. Actual held asset weight.
6. NM21 of the retained basket at its actual current weights, zero when empty.
7. Known sessions to the next monthly handoff divided by21.
8. Primary ticket cost1 EUR divided by actual NAV.

REDEPLOY uses those eight plus:

9. Current compatible-candidate availability indicator.
10. Current candidate NM21 minus held NM21; zero if unavailable.
11. Log(current candidate sigma63 / held sigma63); zero if unavailable.
12. Known sessions to the first weekly signal strictly later than k+1, divided by5. This is the primary next-Close calendar expectation, not a future realized sale date.

Use OLC111's trailing `basket_stats` convention and volatility floor. Current absence of a replacement does not make a future REDEPLOY plan illegal. Both execution stresses retain the primary1-EUR feature definition; realized state/wealth can still differ. No scaling or clipping is learned from future rows.

## Models, fitting and decisions

Separate PARK and REDEPLOY value heads pool held legs, giving each distinct signal date total training weight one. Three matched models use identical rows and features:

- **MEAN_CYCLE:** train-only mean per plan family.
- **RIDGE_CYCLE:** linear comparator, weighted training-only mean/standard deviation, unpenalized intercept, penalty1 on mean squared loss.
- **TREE_CYCLE (primary):** one small `DecisionTreeRegressor`, squared-error criterion, `max_depth=2`, `min_weight_fraction_leaf=0.20`, `min_samples_leaf=1`, `random_state=114`. At most four leaves. No boosted ensemble or parameter grid.

TREE is primary to test whether a small nonlinear condition on a complete plan can improve on the previous global linear action responses. RIDGE separates the effect of the finite-plan architecture from the learner class. This primary choice is made before any OLC114 labels/returns and is not retrospectively changed.

At each monthly fit cutoff, admit only outcomes with terminal index **strictly before** the first panel date of that month. Both heads require504 mature distinct signal dates,24 distinct signal calendar months, and12 greedily nonoverlapping42-session outcome intervals. Calendar months are not independent outcomes. Do not reuse OLC111's hard-coded21-session overlap counter.

Use32 deterministic paired bootstrap resamples of fixed63-session calendar-index blocks, retaining every leg/date row in a sampled block. The same draws are shared between heads and model types when block support matches. Seed114; normalize date weights after multiplicities. Keep the full-training Ridge representation fixed within coefficient resamples. Refit the small tree under each block weighting. Save full fitted objects in portable numerical form, all draws/provenance, and exact model hashes. The10th percentile is a heuristic conditional-value buffer, not a calibrated confidence interval.

An action qualifies only when mean>0 and lower10th percentile>0. Select the largest lower value; break ties by plan-family name then ISIN. Fees are already in the labels; do not subtract a second arbitrary hurdle. If none qualifies, follow BASE until the next eligible decision. These are complete-plan values, not independent exit and entry permissions.

No learned intervention before both heads are ready **and** the OLC111 all-head readiness signal index865 (2022-07-01). This preserves a shared earliest activation boundary with OLC111–113. Report the actual common start as max(865, new readiness index)+1 and recompute every control on that date with its own preceding Close NAV. Earlier returns belong to baseline warmup.

## Experiment matrix and judgment

Five accounts: BASE, STATIC_75, MEAN_CYCLE, RIDGE_CYCLE, TREE_CYCLE. Three scenarios: NEXT_CLOSE (1EUR+15bp; lag0), DOUBLE_COST (2EUR+30bp; lag0), DELAY1_CLOSE (1EUR+15bp; one extra session, hence earliest k+2 Close). Total **15 full account paths**. No Open-execution arm is needed in this experiment. Recompute all controls with the new engine; BASE/STATIC_75 next-Close and double-cost accounts must reproduce their original OLC111 counterparts.

Use10,000EUR initial capital, fractional economic units, zero cash return, no account borrowing/shorting, taxes excluded. Same2,096-ISIN current-catalog EUR panel, eligibility/liquidity filters and full2020-03-02–2026-10-30 window. Existing survivorship, adjusted-price-vintage, capacity and daily execution limitations remain.

Report every model/scenario, whole and common periods, all years, net costs/turnover, exposure/cash, drawdown episodes, plan initiations/handoffs/redeployments/no-candidate/deferred/right-censored events and complete nonoverlapping42-session plan counts. Compare with BASE, STATIC_75, the mean-value control, the linear comparator and OLC113 PRICE_RESET on matched dates. The absence of a delayed OLC113 path is disclosed rather than invented.

Preserve the material criterion: at least +3 percentage points CAGR against BASE with no worse sampled MaxDD, on both full and common periods in primary next-Close execution. Report whether the primary model meets it. Separate30% CAGR aspiration. Gains must retain their direction under doubled costs and delayed execution to be called robust within this historical exercise. A secondary success cannot replace a failed primary. No automatic production promotion follows any historical result.

Forecast comparisons are separate: date-balanced prequential MSE/bias against MEAN/RIDGE, conditional realized plan advantages and counts, and action-ranking diagnostics. Overlapping labels and hindsight-best plan advantages are not additive CAGR. Record all forecast failures even if an account path is favorable. The repeatedly studied historical sample is not a pristine holdout.

## Freezes and verification

Before constructing labels, freeze this protocol, the engine/plan/feature/bank/model source, prior source/input identities and causal target order. Before fitting or running policy returns, freeze the completed bank and runner. Save every fit, prediction, plan trace, daily account, instruction, order and decision ledger. Independently reconstruct accounts and marks; test strict maturity, prefix causality, paired date weights, unknown-candidate handling, sale/weekly/handoff priority, delayed fills and unchanged unaffected units. Archive code, protocols, all results and negative findings on a new research branch; old study files remain unchanged.
