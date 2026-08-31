# STEP08K — Regime-adaptive BIL vs STAY

Date: 2026-08-31
Status: preregistered before any STEP08K 2021–2022 replay and before opening any 2023+ outcome.

## Motivation
STEP08J showed that the binary BIL/STAY action space retains a strong oracle ceiling, but one static 2017–2020 mapping is temporally miscalibrated: it uses too much BIL in 2021 and too little in 2022. STEP08K tests one fixed causal adaptation mechanism, without changing the action set, target, feature family, trigger, horizon or zero decision threshold.

## Frozen action space / trigger / accounting
Identical to STEP08J:
- q95 decision set already frozen by STEP08C–J.
- `STAY` = exact FUSION1 path.
- `BIL` = BIL for the same frozen 10-engine-session action window.
- action begins two engine sessions after the decision.
- BIL entry and exit cost = 10 bps one-way.
- no ETF substitutions.

## Target and features
Identical to STEP08J.
Target = `utility(BIL) - utility(STAY)` with utility = terminal return + 0.5 * min(0, local drawdown).
Features are exactly the 18 STEP08J causal state/BIL variables; no new feature is added.

## Fixed model
Same HGB as STEP08J:
- max_iter=180
- learning_rate=0.04
- max_leaf_nodes=7
- min_samples_leaf=35
- l2_regularization=8.0
- random_state=20260824
with median imputation.

## Regime adaptation — frozen before replay
One-year exponential recency weighting, fixed ex ante:
- half-life = **365 calendar days**.
- raw recency weight for training row i at refit date T: `2 ** (-(T-date_i).days / 365)`.
- this multiplies the existing calendar-balance weight `1 / retained_states_on_date`.
- no floor, cap, search or calibration of the half-life.

Walk-forward refit schedule:
- all 2021 decisions use one model fit at 2021-01-01 from fully matured 2017–2020 rows only.
- all 2022 decisions use one model fit at 2022-01-01 from fully matured rows through 2021-12-31, including 2021 labels only because they are then historically observed and fully matured.
- 2021 is never refit using any 2021 outcome.
- no 2022 outcome enters any STEP08K model.

Training-state construction remains at most 10 basket states per date by the deterministic equally-spaced rule used in STEP08J.

## Decision rule
No threshold search:
- predicted BIL advantage > 0 => BIL
- otherwise => STAY.

## Development gate
2021-01-01 through 2022-12-31 only. Qualify for one future holdout only if versus FUSION1:
1. delta CAGR >= -0.50 pp;
2. delta mean MaxDD >= +0.50 pp;
3. delta p10 MaxDD >= +0.50 pp;
4. delta worst-decile MaxDD >= 0;
5. mean MaxDD does not worsen separately in either 2021 or 2022.

No half-life, threshold, feature, model parameter, trigger, horizon or cost may be changed after replay.

## Holdout discipline
2023+ remains sealed unless the complete gate passes. No post-development retuning.
