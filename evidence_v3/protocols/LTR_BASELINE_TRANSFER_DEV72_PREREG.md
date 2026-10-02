# Evidence V3 — Frozen LTR baseline transfer to Dev72

Status: **PREREGISTERED BEFORE ANY DEV72 PERFORMANCE RUN**

## Question

Does the exact Evidence V1 LTR retrieval architecture retain meaningful cross-sectional retrieval and economic signal when retrained causally on the newly frozen, disjoint Dev72 universe?

This is a transfer/baseline test, not a new model search.

## Frozen inputs

- Dev72 frozen dataset: `evidence_v3/data/dev72/`.
- Dev72 manifest SHA256: `2856f629c06a5e66d6229756cdc721858b30c0e35b8ed78cc90a45872fe63b3c`.
- Dev72 universe SHA256: `412e577eab42cf9978fe57d6e42c62f9959aa0e46667ee5070aa3a788b9b5778`.
- Canonical source-only MA3 builder Git blob: `34cc133d4d44bb06cc21363b1444865e2d8ec5c1`.
- Frozen MA3 producer Git blob: `e691376e3a8e0ec1bd38cc5b85a8ebbfa35d0592`.

No network access is permitted in the model test.

## Model — unchanged from Evidence V1 Retriever LTR v1

Use frozen `FEATURES_42` and `target_relevance` only.

XGBoost `XGBRanker`:
- objective `rank:ndcg`
- n_estimators 400
- max_depth 2
- learning_rate 0.02
- subsample 0.90
- colsample_bytree 0.90
- min_child_weight 12
- reg_lambda 12.0
- reg_alpha 0.2
- tree_method `hist`
- random_state 101
- n_jobs 2
- lambdarank_pair_method `topk`
- lambdarank_num_pair_per_sample 10

Training is annual expanding. For year Y, a training row is admissible only if `signal_date < Y-01-01` and `exit_date_63 < Y-01-01`. No Original149 rows, Holdout70 rows, EU110/EU120 rows or frozen LTR scores are used for model fitting.

## Evaluation window

Evaluate every Dev72 signal date from 2017-01-01 onward for which:
- `fwd_ret_21` is available;
- at least 10 eligible candidates have an OOS score.

The number of periods is determined mechanically by the frozen source-only panel; it is not tuned to reproduce Original149's 114 periods.

## Random retrieval expectation

For each evaluated period with `n_t` eligible candidates:
- random Top5 winner probability = `min(5,n_t)/n_t`;
- random Top10 winner probability = `min(10,n_t)/n_t`.

Across periods:
- `Top5_enrichment = observed_Top5_hits / sum_t[min(5,n_t)/n_t]`;
- `Top10_enrichment = observed_Top10_hits / sum_t[min(10,n_t)/n_t]`.

This adjusts the gate for the actual candidate count and avoids importing Original149 absolute hit counts into a different universe.

## Economic comparators

On exactly the same evaluation dates:
- LTR Top1: return of highest-score ETF;
- LTR Top5-EW: equal-weight mean return of score ranks 1..5;
- Universe-EW: equal-weight mean `fwd_ret_21` of all eligible candidates.

CAGR proxy is the same monthly compounding convention used in Evidence V1/V2: `prod(1+r)^(12/N)-1`.

## Primary transfer gate

LTR transfer is considered **credible development evidence** only if all four conditions hold:
1. Top5 enrichment versus exact random expectation >= **2.0x**;
2. Top10 enrichment versus exact random expectation >= **1.5x**;
3. LTR Top1 CAGR proxy > Universe-EW CAGR proxy;
4. LTR Top5-EW CAGR proxy > Universe-EW CAGR proxy.

Top1 exact-winner rate, Top3, IC, NDCG, winner-rank statistics and subperiods are diagnostic only.

## Decision rule

- **PASS**: mark the frozen LTR architecture as transferred to Dev72. Dev72 then becomes burned development data. Preregister exactly one new V3 decision-layer hypothesis before testing it.
- **FAIL**: do not tune LTR hyperparameters, target, K, feature subset or gate on Dev72. Close the frozen-LTR transfer hypothesis on Dev72 and reassess V3 architecture before any additional model run.

This test cannot produce a promotion claim and does not open Holdout-B.