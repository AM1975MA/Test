# Evidence V2 — Retriever category-context v1

Status: **PREREGISTERED BEFORE EXECUTION**

## Hypothesis

The frozen LTR v1 retriever may be missing stable semantic information about what an ETF represents. The frozen `macro_category` taxonomy is known ex-ante, is independent of future returns, and is distinct from the data-driven cluster/rank features already present in `FEATURES_42`.

## One permitted change

Use the exact frozen LTR v1 model, target, annual expanding schedule and hyperparameters, appending exactly six binary indicators from the frozen Original149 `universe.csv`:
- `C01_US_BROAD_STYLE`
- `C02_US_SECTOR_THEME`
- `C03_DEVELOPED_GLOBAL`
- `C04_EMERGING`
- `C05_BONDS_CASH_CREDIT`
- `C06_REAL_ASSETS`

Every ticker must map to exactly one category. No category aggregation, performance weighting, learned embedding, alternate taxonomy, category interaction engineering or other feature may be added.

## Causality

- Category metadata is read only from the already frozen `evidence_v1/data/original149/universe.csv`.
- It is static metadata and therefore available before every signal date.
- Annual expanding fitting remains unchanged.
- Training labels require `exit_date_63 < annual cutoff` exactly as frozen LTR v1.

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
1. category-context Top5 global-winner count > `32`;
2. category-context Top10 global-winner count > `47`;
3. category-context Top1 exact-winner count >= `10`;
4. category-context Top1 21d CAGR proxy >= `0.220630708412056`.

Top3, IC, NDCG, mean/median winner rank, Top5-EW CAGR and subperiods are diagnostic only.

## Decision rule

- **PASS**: stop Original149 development and freeze a new disjoint Holdout-B before any promotion test.
- **FAIL**: reject semantic-category context and do not try category subsets, alternate encodings, learned embeddings, category interactions or nearby model settings on Original149.

Original149 remains burned development data. Holdout70 is not used.