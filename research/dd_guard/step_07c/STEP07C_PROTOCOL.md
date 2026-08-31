# STEP07C — persistent stress state + direct treatment-advantage value

Date: 2026-08-31

## Why this is a separate experiment
STEP07B is frozen and rejected. Its diagnostic showed that the earlier STEP07A/07B episode definition terminates at the crash endpoint, so action opportunities disappear precisely when sustained protection is most valuable. STEP07C changes the state machine, not thresholds or holdout evidence.

## Holdout discipline
- Model/replay development only: 2021–2022.
- 2021 OOF uses labels ending <= 2020-12-31.
- 2022 OOF expands through labels ending <= 2021-12-31.
- 2023+ remains sealed unless a lane passes the same quality-jump gate.

## Persistent episode state
Using the exact frozen Treatment Value HGB path:
1. start an episode when path drawdown first crosses below `-1.0 * s0`, where `s0 = trailing 63-session daily volatility * sqrt(21)` fixed at episode start;
2. **do not terminate when a deeper crash threshold is crossed**;
3. remain active until path drawdown recovers above `-0.5 * s0`, or 126 sessions elapse;
4. `depth_s0`, episode age, and `crash_crossed = drawdown <= -3*s0` are state features.

This is a persistent de-risk/re-risk controller rather than a one-step crash classifier.

## Ticker-normalized state
Join the frozen monthly basket-specific leader/satellite state from `RISK_LEARNING_PANEL.csv` to each active day and convert momentum/drawdown to volatility-scaled coordinates. Add the causal daily normalized path features from STEP07A and frozen regime controls. No feature search.

## Exact risky sleeves
- `TV`: exact Treatment Value HGB path (substitution-bearing sleeve).
- `FLIP`: exact ARMED_FLIP_25_75 path.
- `BLEND50`: 50/50 of TV and FLIP.
- Cash/exposure reductions are exact scalar combinations of TV and cash.

## Actions
- C1 EXPECTED_ADV_EXPOSURE: TV, TV75, TV50, TV25, CASH.
- C2 EXPECTED_ADV_SUBSTITUTION: TV, BLEND50, FLIP, CASH.
- C3 Q10_ADV_FULL: TV, TV75, TV50, TV25, BLEND50, FLIP, CASH.

## Counterfactual target
Primary horizon: 10 sessions, action starts with one conservative full-session lag (`t+2` first affected close-to-close return). Horizon is **not** terminated by a crash threshold and is not capped at monthly rebalance; the exact frozen path already includes rebalance effects.

For each action:
`utility = horizon_return + 0.5 * local_MaxDD`, with MaxDD negative.

The supervised target is the **incremental treatment advantage**:
`advantage(action) = utility(action) - utility(TV)`.
TV has advantage 0 by construction. A non-TV action is selected only if its predicted advantage exceeds 0.

## Models
No model grid.
- C1/C2: HistGradientBoostingRegressor on expected treatment advantage.
- C3: HistGradientBoostingRegressor with quantile loss q=0.10 on treatment advantage.
- max_iter=160, learning_rate=0.04, max_leaf_nodes=7, min_samples_leaf=35, l2_regularization=8, random_state=20260831.
- Sample weight = inverse number of active basket rows on the same market date.

## Replay
Each active-day decision controls the return two sessions later. Because persistent episodes continue through deep crashes until recovery, action decisions remain available during the full stress path. Outside active states the portfolio defaults to TV. 5 bp one-way turnover is charged from exact daily sleeve-weight changes.

## Quality-jump gate versus frozen FUSION1, 2021–2022
All must pass:
1. mean MaxDD improvement >= +0.50 pp;
2. p10 MaxDD improvement >= +0.50 pp;
3. CAGR delta >= -0.50 pp;
4. mean MaxDD delta >= 0 separately in 2021 and 2022;
5. leave-one-decision-date-out worst-case mean-MaxDD delta >= 0.

If no lane passes, 2023+ remains sealed and this controller research lane stops.
