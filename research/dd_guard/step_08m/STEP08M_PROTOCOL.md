# STEP08M — True Credit Spread Confirmation + Structural Breadth

Date: 2026-08-31
Status: pre-registered before any 2021–2022 STEP08M economic replay.

## Question
Can true corporate credit-spread information distinguish a recoverable equity shock (STAY) from a persistent/systemic deterioration in which temporary BIL is economically preferable?

## Frozen baseline/action mechanics
- Baseline: exact FUSION1 engine and q95 decision states inherited from STEP08J/K/L.
- Actions: **STAY in FUSION1** or **BIL** only.
- Action start/end, 5 bp FUSION1 costs and BIL switch accounting: identical to STEP08J/K/L.
- Development: 2021-01-01 through 2022-12-31 only.
- 2023+ remains sealed unless the predeclared gate passes.

## Frozen estimator
- HistGradientBoostingRegressor with exactly the STEP08K/L parameters: max_iter=180, learning_rate=0.04, max_leaf_nodes=7, min_samples_leaf=35, l2_regularization=8, random_state=20260824.
- Exponential sample recency weighting with half-life 365 calendar days.
- Refit at 2021-01-01 using only matured 2017–2020 labels; refit at 2022-01-01 adding only matured 2021 labels.
- Action rule: BIL iff predicted incremental utility(BIL−STAY) > 0; otherwise STAY.
- No threshold/model search.

## New information — true credit, deliberately low-dimensional
Daily ICE BofA OAS series:
- HY OAS: BAMLH0A0HYM2
- IG corporate OAS: BAMLC0A0CM
- HY-minus-IG OAS

For each spread family, frozen causal transforms:
- current level
- change over 5, 21 and 63 market sessions
- short-vs-medium acceleration = change5 − change21/4.2
- causal trailing percentile over the prior 252 available sessions, min 126

Structural breadth block is inherited unchanged from STEP08L.

One simple predeclared interaction only: `hy_chg21_x_breadthweak = hy_oas_chg21 * (1 - breadth_above_ma63)`.

## Promotion-eligible primary policy
`TRUE_CREDIT_BREADTH` = frozen STEP08J base state + true-credit block + structural breadth.
A credit-only attribution replay may also be emitted, but cannot be selected post-hoc for promotion.

## Gate
All must hold against FUSION1 on 2021–2022:
1. delta mean MaxDD >= +0.50 pp;
2. delta p10 MaxDD >= +0.50 pp;
3. delta worst-decile MaxDD >= 0;
4. delta CAGR >= -0.50 pp;
5. delta mean MaxDD >= 0 separately in 2021 and 2022.

If the primary policy fails: `REJECT_BEFORE_2023_HOLDOUT` and immediately perform a full STEP06–STEP08M reset audit rather than retuning STEP08M.

## Data integrity
- OAS source must contain pre-2023 history and will be hard-truncated at 2022-12-31 before feature construction.
- Missing/no-observation rows may be forward-filled only onto the frozen engine market calendar with a maximum 5-calendar-day gap.
- No 2023+ OAS observation may enter a transform, percentile, imputer, fit, or replay.
