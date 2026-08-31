# STEP08I — Small-Set Protective Selector

Date: 2026-08-31
Status: pre-registered before any STEP08I development replay. 2023+ remains sealed.

## Objective
Test whether the causal reduction achieved by STEP08H is sufficient to make destination selection learnable. The action space is restricted to:
- STAY in exact FUSION1 continuation;
- BIL;
- at most the five ETFs retained by the frozen STEP08H live shock-resilience filter.

No new trigger, universe, action horizon, cost assumption, or resilience rule is introduced.

## Frozen state/action mechanics
- Trigger/development schedule: exact non-overlapping STEP08C q95 schedule.
- Basket universe: original 24 ETFs per basket.
- Origin holdings: last strictly-prior STATE_PANEL leader/satellite state.
- Resilience filter: exactly STEP08H (relative returns 1/3/5/10, 21d current-DD gap, downside gap on origin-negative days; hard pass count >=2; top 5 by mean cross-sectional percentile score).
- Action start/end: exact STEP08C/08H schedule; 10-session action window.
- One-way transaction cost: 10 bps at entry and exit for replacement actions.
- STAY: exact FUSION1 continuation, with no additional replacement cost.
- Event-time Titanium score: frozen STEP08F HGB distillation producer. It is an input feature only; it does not directly select the action.

## Training
- Training states: 2019-01-01 through 2020-12-31 only, generated from the frozen STEP07A episode panel and deterministically thinned to <=10 basket states per calendar date, as in STEP08G.
- A state is usable only when the full 10-session action label is mature by 2020-12-31.
- For every state, apply the exact STEP08H resilience filter. Candidate training actions are the retained ETFs plus BIL.
- Target for every candidate action:
  `action_advantage = utility(candidate action) - utility(exact FUSION1 STAY continuation)`.
- Date/event balancing: each calendar date receives equal aggregate weight; within date, each basket state receives equal weight; within state, each candidate action receives equal weight.

## Predictor
Exactly one model; no development model selection:
`SimpleImputer(median) -> HistGradientBoostingRegressor(max_iter=180, learning_rate=0.04, max_leaf_nodes=7, min_samples_leaf=35, l2_regularization=8.0, random_state=20260824)`.
These hyperparameters are inherited unchanged from STEP08G.

Candidate features are frozen before replay:
- STEP08H resilience features and ranks;
- candidate 5/21/63 return, 20/63 volatility, 21/63 drawdown;
- event-time Titanium percentile and its rank within the resilient set;
- candidate minus origin relative return features;
- STEP07A normalized state variables for the origin episode;
- binary `is_bil`.
No feature is selected or removed based on 2021-2022 results.

## Deployable policy
For each 2021-2022 q95 decision:
1. build the frozen STEP08H top-5 resilient ETF set;
2. append BIL;
3. predict incremental action advantage for each available action;
4. if the maximum predicted advantage <= 0, choose STAY;
5. otherwise choose the single action with the highest predicted advantage.
No threshold other than zero is searched.

## Development gate
A candidate may qualify for a one-shot 2023+ holdout only if all are true on 2021-2022:
- delta mean MaxDD vs FUSION1 >= +0.50 pp;
- delta p10 MaxDD >= +0.50 pp;
- delta worst-decile MaxDD >= 0;
- delta CAGR >= -0.50 pp;
- delta mean MaxDD is non-negative separately in 2021 and 2022.

No post-result tuning of model, feature set, q95 trigger, resilience filter, action window, costs, or decision threshold is permitted. If the gate fails, 2023+ remains sealed.
