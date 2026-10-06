# Evidence V2 — Retriever calendar-context v1

Status: **PREREGISTERED BEFORE EXECUTION**

## Hypothesis

The frozen LTR v1 retriever may be missing low-dimensional seasonal state information that is known ex-ante and common to all candidates. Month-of-year can interact with the existing asset features without introducing any future information.

## One permitted change

Use the exact frozen LTR v1 model, target, annual expanding schedule and hyperparameters, appending exactly twelve binary indicators derived only from `signal_date`:
- `month_01`
- `month_02`
- `month_03`
- `month_04`
- `month_05`
- `month_06`
- `month_07`
- `month_08`
- `month_09`
- `month_10`
- `month_11`
- `month_12`

Every row must have exactly one active month indicator. No quarter encoding, weekday encoding, Fourier/cyclic transform, holiday feature, alternate calendar representation or interaction engineering may be added.

## Causality

- Calendar features are derived only from the already-known `signal_date`.
- Annual expanding fitting remains unchanged.
- Training labels require `exit_date_63 < annual cutoff` exactly as frozen LTR v1.
- No network access or external data are used.

## Baseline comparator

Frozen Evidence V1 Retriever LTR v1 on the same source-only Original149 panel and the same 114 evaluation dates.

Fail-closed expected baseline:
- periods: `114`
- Top1 global winner: `10`
- Top5 global winner: `32`
- Top10 global winner: `47`
- Top1 21d CAGR proxy: `0.220630708412056`

## Primary advancement gate

All four conditions are required:
1. calendar-context Top5 global-winner count > `32`;
2. calendar-context Top10 global-winner count > `47`;
3. calendar-context Top1 exact-winner count >= `10`;
4. calendar-context Top1 21d CAGR proxy >= `0.220630708412056`.

Top3, IC, NDCG, mean/median winner rank, Top5-EW CAGR and subperiods are diagnostic only.

## Decision rule

- **PASS**: stop Original149 development and freeze a new disjoint Holdout-B before any promotion test.
- **FAIL**: close Evidence V2 development on Original149. Do not try quarter, weekday, Fourier seasonality, alternate month encodings, calendar interactions, nearby model settings, or additional information-block tests on Original149.

## Stop rule

This is the final Evidence V2 information-block test permitted on Original149. Original149 remains burned development data. Holdout70 is not used.