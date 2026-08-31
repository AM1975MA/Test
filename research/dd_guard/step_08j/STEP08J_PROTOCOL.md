# STEP08J — Direct BIL vs STAY value selector

Date: 2026-08-31
Status: preregistered before any STEP08J development replay and before opening any 2023+ outcome.

## Motivation
STEP08I officially failed the promotion gate, but a strictly post-hoc diagnostic showed that removing ETF substitutions and retaining only the binary decision BIL versus STAY produced a much better risk/return trade-off. STEP08J tests that simplified hypothesis as a new, independent experiment. The post-hoc STEP08I numbers are not eligible evidence for STEP08J promotion.

## Frozen action space
At each already-frozen q95 risk decision used by STEP08C–I, exactly one action is allowed:
- `STAY`: retain the exact FUSION1 path.
- `BIL`: replace the exact action window by BIL for the same frozen 10-session horizon and transaction-cost accounting used in STEP08I.

No ETF alternative, no top-k filtering, no correlation rule, no Titanium rank is allowed in STEP08J.

## Trigger and action timing
- Trigger: unchanged q95 decision set already frozen in `STEP08C/ORACLE_DECISIONS.csv` for development 2021–2022.
- Decision date: unchanged.
- Action starts two engine sessions after the decision, exactly as in STEP08C–I.
- Horizon: 10 engine sessions, unchanged.
- BIL transaction cost: 10 bps one-way on entry and exit, identical to STEP08I action accounting.
- FUSION1 path and costs remain unchanged.

## Training data
Training is restricted to fully matured pre-2021 stress-state rows from 2017-01-01 through 2020-12-31.
Unlike STEP08I, no origin ticker identity is required, so the full 2017–2020 stress-state history can be used without reconstructing missing 2019 holdings.
For calendar-time balance, at most 10 basket states per date are retained deterministically by equally spaced basket order when more than 10 are present.
Only rows whose entire t+2 through t+11 action window matures by 2020-12-31 are eligible.

## Target
For every training state:
`target = utility(BIL over frozen 10-session action window) - utility(exact FUSION1 STAY over the same window)`
where utility is the already frozen local objective:
`terminal_return + 0.5 * min(0, local_drawdown)`.

## Features
Only causal variables available at the decision close are allowed:
- `zdd`
- `zret1`, `zret3`, `zret5`, `zret10`
- `vol10_over63`
- `negfrac5`
- `dd_delta5_over_s21`
- `sync_rankmean`
- `accel_rankmean`
- `systemic_rankmean_6`
- BIL absolute state: `bil_ret5`, `bil_ret21`, `bil_ret63`, `bil_vol20`, `bil_vol63`, `bil_dd21`, `bil_dd63`

No future episode fields, no future labels, no `episode_rows`, no oracle information, no 2021–2022 economic outcome, no Titanium score, and no post-hoc ETF-selection diagnostic enters the model.

## Model
One fixed model only:
`SimpleImputer(median) -> HistGradientBoostingRegressor`
with exactly the already-used HGB parameters:
- max_iter = 180
- learning_rate = 0.04
- max_leaf_nodes = 7
- min_samples_leaf = 35
- l2_regularization = 8.0
- random_state = 20260824

Training sample weight = `1 / number_of_retained_states_on_that_date`, so each calendar date has equal aggregate weight.

## Decision rule
No threshold search:
- if predicted BIL advantage > 0: `BIL`
- otherwise: `STAY`

## Development period and gate
Replay is restricted to 2021-01-01 through 2022-12-31.
STEP08J qualifies for exactly one future holdout only if all are true versus FUSION1:
1. delta CAGR >= -0.50 pp;
2. delta mean MaxDD >= +0.50 pp;
3. delta p10 MaxDD >= +0.50 pp;
4. delta worst-decile MaxDD >= 0;
5. mean MaxDD does not worsen separately in either 2021 or 2022.

No q95, horizon, threshold, HGB hyperparameter, utility coefficient, feature family, or transaction cost may be changed after the replay.

## Holdout discipline
2023+ remains sealed unless the complete development gate passes. No post-development retuning is permitted.
