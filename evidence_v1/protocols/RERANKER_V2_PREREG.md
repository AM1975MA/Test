# Evidence V1 — Reranker v2 preregistration

Status: **FROZEN BEFORE EXECUTION**

Branch at design review: `research/evidence-v1`
Observed head before this protocol: `b147697096bf77fd9f486db2cc5446caad1a2e0e`

## Scientific question

Can a shallow nonlinear reranker improve the ordering of the **historical OOS Top10 shortlists emitted by Retriever LTR v1**, without changing the frozen data, baseline producer features, target definition, or causal maturity rules?

This test is development evidence on **Original149 only**. Holdout70 remains burned/diagnostic and is not used for promotion.

## Frozen inputs

- data: `evidence_v1/data/original149/`
- baseline source: `evidence_v1/source/baseline/etf_trader_v2/`
- data manifest SHA256: `1efba2bc213ba26b042a9e77630fe26664343654629e658f43d314d068ba9e71`
- source manifest SHA256: `cc4d315da68ec42275a7a74f05446ac6cbb484c3bd92a7861cd76805c5a94782`
- runtime lock: `evidence_v1/requirements.lock.txt`

The workflow must verify both frozen manifests before rebuilding the panel. No live ticker download is permitted.

## Retriever

Retriever LTR v1 is regenerated causally from 2011 onward with the already validated configuration. For every historical signal date only the OOS Top10 is retained.

The reranker may train **only** on those historical OOS Top10 rows whose 63-day labels have fully matured before the yearly cutoff.

## Reranker v2

Representation:

- frozen `FEATURES_42` candidate features;
- normalized OOS LTR position (`1.0 = retriever rank 1`, scale normalized to universe size);
- no ticker identity;
- no future/ex-post feature;
- no in-sample retriever prediction.

Target:

- unchanged frozen `target_relevance` / multi-horizon target already used in Evidence V1;
- 63-day maturity gate.

Model: one single preregistered `XGBRanker` configuration, no sweep:

```json
{
  "objective": "rank:pairwise",
  "n_estimators": 300,
  "max_depth": 2,
  "learning_rate": 0.02,
  "subsample": 0.85,
  "colsample_bytree": 0.75,
  "min_child_weight": 20,
  "reg_lambda": 20.0,
  "reg_alpha": 1.0,
  "tree_method": "hist",
  "random_state": 211,
  "n_jobs": 2,
  "lambdarank_pair_method": "topk",
  "lambdarank_num_pair_per_sample": 8
}
```

Training schedule: annual expanding walk-forward. Prediction year `Y` may use only historical OOS shortlist rows with `exit_date_63 < Y-01-01`.

Fail-closed source identity for this preregistered test:

- Git blob SHA of `evidence_v1/src/reranker_v2_nonlinear.py`:
  `6a3ad3c33cec375b18dc871ec971a947676cf067`

The workflow must compare `git hash-object` of the executed test source to this exact blob before execution. Runtime provenance will additionally record SHA256.

## Primary comparison

Compare Reranker v2 directly with the same-date LTR v1 ordering on the OOS Top10 shortlist.

Primary ranking metrics:

- exact winner at Top1;
- winner contained in Top2;
- winner contained in Top3.

Secondary diagnostics:

- Top1 21-day CAGR proxy;
- score margin vs subsequent Top1-Top2 21-day return differential;
- 2017–2022 vs 2023–2026 stability.

CAGR is **not** an advancement criterion in this test.

## Preregistered advancement rule

Advance Reranker v2 to confidence-calibration diagnostics only if, on the full evaluation window:

1. Top2 winner containment is strictly higher than LTR v1; and
2. exact Top1 winner rate is not lower than LTR v1.

Otherwise reject it as the final reranker candidate and retain the result only as diagnostic evidence.

No hyperparameter or threshold change is allowed after observing this test result. Any changed configuration is a new version/test.
