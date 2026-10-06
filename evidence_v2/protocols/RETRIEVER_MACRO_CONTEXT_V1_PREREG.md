# Evidence V2 — Retriever macro-context v1

Status: **PREREGISTERED BEFORE EXECUTION**

## Hypothesis

The frozen LTR v1 retriever may be missing state information common to all candidates. A fixed external macro-context block may allow the same ranking model to learn state-dependent interactions with the existing 42 asset features.

## One permitted change

Use the exact frozen LTR v1 model/label/training schedule, adding exactly six frozen macro-context features:
- `vix_z252`
- `dgs2_delta21`
- `dgs10_delta21`
- `curve_10y2y_z252`
- `baa10y_z252`
- `usd_ret21`

The credit feature is based on `BAA10Y` after the documented pre-model data-availability amendment replacing the FRED-truncated ICE HY OAS series. No performance result was observed before this substitution.

No other feature, target, model, hyperparameter, K, loss, seed, lookback, normalization, weighting or allocation rule may change.

## Causality

- Macro data must come only from `evidence_v2/data/macro_context_v1/` committed before this model test.
- Each signal date uses only the last macro row with `macro_date < signal_date`; same-date observations are excluded.
- Model fitting remains annual expanding.
- Training labels are allowed only when `exit_date_63 < annual cutoff`.

## Baseline comparator

Frozen Evidence V1 Retriever LTR v1 checkpoint on the same Original149 panel and the same 114 monthly evaluation dates.

Fail-closed expected baseline:
- periods: `114`
- Top1 global winner: `10`
- Top5 global winner: `32`
- Top10 global winner: `47`
- Top1 21d CAGR proxy: `0.220630708412056`

## Primary advancement gate

All four conditions are required:
1. macro-context Top5 global-winner count > `32`;
2. macro-context Top10 global-winner count > `47`;
3. macro-context Top1 exact-winner count >= `10`;
4. macro-context Top1 21d CAGR proxy >= `0.220630708412056`.

IC, NDCG, mean/median winner rank, Top3, Top5-EW CAGR and subperiods are diagnostics only and cannot override this gate.

## Decision rule

- **PASS**: no further Original149 tuning; freeze a new disjoint Holdout-B before any promotion test.
- **FAIL**: reject the macro-context hypothesis on Original149 and do not try macro-series subsets, alternative transformations, alternate lookbacks or nearby model settings.

Original149 remains burned development data. Holdout70 is not used.