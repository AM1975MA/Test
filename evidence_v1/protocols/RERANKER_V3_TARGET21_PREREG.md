# Evidence V1 — Reranker v3 target-aligned 21d

Status: **PREREGISTERED BEFORE EXECUTION**

## Hypothesis

The rejected reranker v2 reused the producer's multi-horizon relevance target. Evidence V1 now supports a stable reference-universe representation, but Top1 selection remains unresolved.

The v3 hypothesis is deliberately narrow:

> keeping reranker capacity, features, OOS shortlist and evaluation rule fixed, a target aligned directly to the 21-trading-day decision horizon can improve ordering inside the frozen LTR Top10.

No model-capacity sweep or hyperparameter search is allowed.

## Frozen inputs

- branch: `research/evidence-v1`
- evaluator: `evidence_v1/src/reranker_v3_target21.py`
- evaluator Git blob: `a7bd126a270f770eceaf5c41c5950a401be83388`
- frozen Original149 data manifest SHA256: `1efba2bc213ba26b042a9e77630fe26664343654629e658f43d314d068ba9e71`
- frozen source manifest SHA256: `cc4d315da68ec42275a7a74f05446ac6cbb484c3bd92a7861cd76805c5a94782`
- locked runtime SHA256: `01305fe62203c7b7895d95836267c4288f86d2c5a763ce7070c9c3d3d9f807ae`
- source-only panel builder Git blob: `34cc133d4d44bb06cc21363b1444865e2d8ec5c1`
- canonical producer / `FEATURES_42` Git blob: `e691376e3a8e0ec1bd38cc5b85a8ebbfa35d0592`
- frozen Retriever LTR v1 checkpoint manifest Git blob: `e51a8651f6696a0081acb09e3ed230e7e35fd79c`
- frozen Retriever LTR v1 `TOP10.csv` Git blob: `cd2ae12a5223feda0ec1306d824d426dbbbb7550`
- frozen Retriever LTR v1 `OOS_PREDICTIONS.csv` Git blob: `1745a6d12b6957bc629998c7ac3417550ac9bceb`
- OOS prediction SHA256: `3f9e054fdc0716161cec185ad5a32a62671ad3032070b9ca24ceed655011abd6`

The retriever is **not retrained** in this experiment. v3 consumes its already-materialized OOS Top10 shortlist.

## Representation

Reference universe: frozen `Original149`.

Reranker features:

- canonical Hybrid24 `FEATURES_42`, computed from the frozen Original149 source-only panel;
- frozen `LTR_POSITION` from Retriever LTR v1.

Thus the v3 development test follows the supported architectural rule:

`features = f(asset, stable_reference_universe)`.

On Original149 itself this does not change feature values relative to the canonical full-universe panel; its purpose is to keep the architecture explicit for later transfer/promotion tests.

## Target — only scientific change versus v2

For each historical **frozen OOS Retriever Top10** signal date:

1. observe future 21-trading-day return `fwd_ret_21` only for label construction;
2. rank the ten shortlist members by that future 21d return;
3. assign ordinal relevance `9` to the best, `8` to second, ... `0` to the worst.

Target name: `RR3_TARGET21`.

This target is defined only inside the OOS shortlist because the reranker's task is to order names already retrieved by LTR.

## Model — frozen before execution

Exactly the same nonlinear reranker capacity/configuration used by rejected v2:

- XGBoost `rank:pairwise`
- `n_estimators = 300`
- `max_depth = 2`
- `learning_rate = 0.02`
- `subsample = 0.85`
- `colsample_bytree = 0.75`
- `min_child_weight = 20`
- `reg_lambda = 20.0`
- `reg_alpha = 1.0`
- `tree_method = hist`
- `random_state = 211`
- `lambdarank_pair_method = topk`
- `lambdarank_num_pair_per_sample = 8`

No sweep and no early-stopping selection.

## Causal training

- annual expanding reranker fits for evaluation years 2017 through 2026;
- training rows come only from frozen historical Retriever LTR v1 OOS Top10 shortlists;
- a training label is admissible only when `exit_date_21 < January 1` of the prediction year;
- no in-sample retriever shortlist may enter reranker training;
- imputation is fit only on each year's admissible training rows.

The maturity horizon is 21d because v3's target itself is 21d. This is part of the preregistered target-alignment hypothesis, not an ex-post timing choice.

## Evaluator

Evaluation window: `2017-01-01 <= signal_date < 2026-07-01`.

Expected periods: **114**.

The relevant winner is the ETF with the highest future 21d return across the **full Original149 OOS candidate universe**, not merely the best ETF inside Top10.

The reranker may choose only within the frozen historical LTR Top10.

The frozen LTR comparator must reproduce before v3 is judged:

- 114 periods;
- exact Top1 global winner: `10/114 = 8.7719%`;
- global winner in Top2: `15/114 = 13.1579%`;
- global winner in Top3: `21/114 = 18.4211%`.

A comparator mismatch aborts the run.

## Primary advancement rule

v3 advances from development evidence only if, on the same 114 periods:

1. **Top2 global-winner containment is strictly higher than frozen LTR v1**, and
2. **exact Top1 global-winner rate is not lower than frozen LTR v1**.

CAGR is diagnostic only and cannot rescue a failure of the ranking rule.

The following must also be reported, but are not additional promotion thresholds:

- Top3 global-winner containment;
- 21d Top1 CAGR proxy;
- margin vs Top1-minus-Top2 future-return Spearman;
- separate 2017-2022 and 2023-2026 metrics.

## After the result

- **If REJECTED:** do not tune v3 ex post. Record the result and require a genuinely new hypothesis/version.
- **If ADVANCE:** do not promote directly. The next action is to freeze a new, disjoint **Holdout-B** before observing its performance, then run exactly one promotion test. No tuning after Holdout-B freeze.
- confidence calibration/sizing remains downstream of a reranker that first passes the ranking gate.

Durable result path after a valid run:

`evidence_v1/results/reranker_v3_target21/`
