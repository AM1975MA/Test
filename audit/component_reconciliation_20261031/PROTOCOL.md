# Component-to-decision reconciliation — 31 October 2026

Research only. Production/main unchanged. No model fitting or parameter optimization.

## Question
Reconcile each component's contribution to decisions and realized net portfolio paths, preserving opportunities for large trends rather than rewarding stability alone.

## Immutable evidence
Original149, three correlated frozen raw revisions: Actions run 37121749852, artifact 11272972639. Frozen 2x2x2 score-factorial paths: run 39058118631, artifact 12110461075. Frozen selection/weight intervention paths: run 39060389253, artifact 12111590600. Source engine commit 13443836649d0f107d2063eb7acc1039135d6e9b. Original main 77f7a4706f934e7061541cd62c1c0ce64ab7135d.

## Fixed analyses
1. Independently recompute all 51 archived path metrics, preserving the initial NAV=1 and all 2366 observations. Require shared dates, identical three-vintage universe and cross-experiment R_T0_H1/R_R parity.
2. Score factorial: Compact BASE vs RETURN_RANK_NDCG, Titanium Ridge Tail package off/on, MA3 Hybrid package off/on. Analyze all eight corners, conditional differences, exact two-/three-way interactions and Shapley allocation in additive annualized log wealth, not by adding standalone CAGRs. Hybrid-off also removes model-agreement sizing: label package effects, not pure score effects.
3. Selection/weight mediation: four H_H/H_R/R_H/R_R corners plus fixed-half controls. Recompute exact selection and weight Shapley and interaction, daily/monthly/yearly contributions. Margin is bundled with weight; downstream risk is recomputed, not artificially frozen state.
4. Reproduce canonical original engine from frozen OHLCV and frozen predictions before policy ablation. Numerical parity tolerance 1e-12 against archived complete daily arrays. Then execute complete six-toggle policy factorial for two preidentified scoring policies: original BASE/Titanium/Hybrid (B_T1_H1), and historical ReturnRank+Hybrid without Titanium Ridge Tail (R_T0_H1). Toggles: score-based concentration vs equal-half; DD-first/HighCAGR gross vs full gross; V6 alternative vs none; systemic opening-gap/cooldown protection vs disabled; conditional intraday stops vs disabled; original transaction fee/slippage vs zero. These are attribution interventions, NOT a search for the best configuration. No promotion based on corner ranking.
5. Preserve exact original simulator when all toggles are on. Instrumented research copy may expose switches and an execution ledger; compare its all-on path to unmodified original engine. Keep raw gap inputs for stop predicates when systemic-gap protection alone is disabled. Stop-induced cooldown is kept when stops are on, even if systemic-gap triggering is off; name the shared mechanism explicitly. V6 state is recomputed for each altered allocation/gross contract; gross-off removes the DD residual-cash budget, so V6 can legitimately become inactive.
6. Complete-path counterfactuals include endogenous holdings, costs and risk-state feedback. Distinguish these from a mechanical same-holdings cost subtraction. Measure actual executed trades/weights where available, not just monthly proposed leaders.

## Statistics and accounting
Use calendar time as the unit; average correlated vintage log-return contrasts before resampling. Paired circular 21-session blocks, 10000 replicates, seed 20261031, and 63-session sensitivity for main component contrasts. Report raw 95% exploratory intervals and family-wise simultaneous bounds for each six-effect policy family. No virgin holdout claims; old history and model choices are reused. Sum daily log contributions exactly to annualized log wealth difference and separately show nonlinear CAGR conversion. Retain negative and zero effects, interactions, exposure, cost, drawdown, year attribution, and counterfactuals that are economically unattractive. Purely accounting Shapley allocation is conditional on the declared off-state and players, not proof of future causal alpha.

## Scope limits
This does not certify raw Yahoo prices, live fills, delisting survival or total model-training validity. Frozen-score replay is not source-only model retraining. The policy factorial is not a full cross-product of every training, scoring and execution variant. Archived score-factorial and new policy-factorial effects cannot be indiscriminately summed. Explicitly report any parity failure or unexecuted check.
