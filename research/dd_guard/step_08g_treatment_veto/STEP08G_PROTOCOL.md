# STEP08G — Event-Time Titanium + Incremental Protective Treatment Value

Date: 2026-08-31
Status: **PRE-REGISTERED BEFORE 2021–2022 GATE REPLAY**
2023+ remains sealed.

## Scientific question
STEP08F showed that refreshing Titanium at event time improves CAGR (+0.632483 pp vs FUSION1 on 2021–2022) but does not improve tail drawdown. STEP08G asks whether the event-time alpha proposal can be retained while a separately trained treatment-value gate vetoes economically harmful switches.

## Frozen inputs
- Danger trigger: unchanged STEP08C/STEP08F q95 schedule.
- Action start/end: unchanged STEP08C 10-session windows.
- Candidate universe: exact original 24-ETF basket, current leader/satellite excluded.
- Event-time producer: frozen STEP08F HGB distillation of authentic `TIT_R`; no producer changes.
- Proposal semantics: exact STEP08F V2 rule: 100% top-1 when event-time score margin >= 0.12; otherwise 75%/25% top-1/top-2.
- Transaction costs: unchanged 10 bp round-trip replacement cost.
- Baseline: exact FUSION1 continuation.

## Treatment-value model
A single fixed HistGradientBoostingRegressor is used. Hyperparameters are inherited from the previously accepted Titanium Treatment-Value HGB architecture and are not searched here:
- max_iter = 180
- learning_rate = 0.04
- max_leaf_nodes = 7
- min_samples_leaf = 35
- l2_regularization = 8.0
- random_state = 20260824

Training uses only fully matured pre-2021 stress states. As in STEP08C, at most 10 deterministic basket states per date are retained to prevent same-date basket multiplicity from dominating. Candidate examples use the frozen STEP08C candidate/state feature family.

Target for each candidate j is direct incremental utility versus the exact FUSION1 continuation over the same 10-session action window:
`gain(j) = U(j) - U(FUSION1 continuation)`
where `U = terminal return + 0.5 * local minimum drawdown`.

The same model scores BIL; there is no separately tuned BIL rule.

## Frozen three-way decision
For each 2021–2022 q95 decision:
1. STEP08F event-time Titanium proposes the frozen V2 allocation (top1 or 75/25 top1/top2).
2. Predict treatment gain for each proposed ETF constituent and BIL.
3. Proposed ETF-action predicted gain = the frozen portfolio-weighted average of constituent predicted gains. This is only a gate score; realized replay uses the exact mixed path.
4. If both ETF predicted gain and BIL predicted gain are <= 0: **STAY** in exact FUSION1.
5. Else choose **ETF** if ETF predicted gain > BIL predicted gain.
6. Else choose **BIL**.
7. Exact ties resolve to **STAY**.

No threshold other than zero is searched or calibrated on 2021–2022.

## Development gate
STEP08G qualifies for one future 2023+ holdout only if, versus FUSION1 on 2021–2022:
- delta CAGR >= -0.50 pp;
- delta mean MaxDD >= +0.50 pp;
- delta p10 MaxDD >= +0.50 pp;
- delta worst-decile MaxDD >= 0;
- delta mean MaxDD >= 0 separately in 2021 and 2022.

Secondary diagnostic: compare STEP08G directly with STEP08F to determine how much alpha the veto preserves and whether it repairs STEP08F tail damage.

## Stop rule
If the gate fails, STEP08G is rejected before 2023+ holdout. No tuning of HGB, zero threshold, q95, horizon, 12% margin, action weights, utility coefficient, or feature family is permitted inside STEP08G.
