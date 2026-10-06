# Evidence V1 — Reranker v4 best-in-shortlist classifier

Status: **PREREGISTERED BEFORE EXECUTION**

## Rationale

Evidence V1 has already rejected three deterministic reranker variants on the burned Original149 development set:
- pairwise linear v1;
- nonlinear ranker v2 using the producer multi-horizon target;
- nonlinear ranker v3 using a directly aligned 21d ordinal target.

The remaining narrow hypothesis is that learning the complete 1→10 ordering is unnecessarily difficult. v4 therefore asks only one binary question for each member of the frozen LTR Top10:

> is this ETF the best 21-day performer inside the OOS shortlist?

This is the **last deterministic reranker family allowed on Original149**. There will be no hyperparameter sweep and no v4b/v4c tuning after observing results.

## Frozen retriever / representation

- Universe for development evaluation: frozen Original149 only.
- Original149 is burned and **cannot provide promotion evidence**.
- Stable reference representation: `FEATURES_42` computed from frozen Original149 reference panel.
- Candidate rows: frozen Retriever LTR v1 OOS `TOP10.csv` checkpoint only.
- Frozen `LTR_POSITION` is appended to `FEATURES_42`.
- Retriever is not retrained.
- Holdout70 is not used.

## Binary target

For every historical frozen OOS Top10 signal date with mature 21d returns:
- exactly one row receives `RR4_BEST21 = 1`: the ETF with highest `fwd_ret_21` inside the Top10;
- the other nine rows receive `0`;
- exact return ties are broken deterministically by ticker ascending;
- no full-universe future information is used to construct the training label.

The full Original149 future winner is used **only by the evaluator** for the primary advancement gate.

## Causal walk-forward

Annual expanding reranker fit for prediction years 2017–2026.

For cutoff `YYYY-01-01`, training rows must satisfy:
- frozen retriever OOS shortlist row;
- `signal_date < cutoff`;
- `exit_date_21 < cutoff`;
- binary target available.

Each mature training signal date must contribute exactly 10 rows, one positive and nine negatives.

No contemporaneous or future shortlist labels enter the fit.

## Model — single frozen configuration

`XGBClassifier`:

- objective: `binary:logistic`
- n_estimators: `300`
- max_depth: `2`
- learning_rate: `0.02`
- subsample: `0.85`
- colsample_bytree: `0.75`
- min_child_weight: `20`
- reg_lambda: `20.0`
- reg_alpha: `1.0`
- tree_method: `hist`
- random_state: `211`
- n_jobs: `2`
- scale_pos_weight: `9.0`
- eval_metric: `logloss`

`scale_pos_weight=9.0` is fixed ex ante from the structural 1:9 class ratio; it is not tuned.

Ranking at inference is descending `predict_proba(...)[positive class]` within the frozen Top10.

Executed source is frozen at Git blob:

`e98ec05f459b27cb33d5e390998432abc456027b`

Path: `evidence_v1/src/reranker_v4_best_classifier.py`.

## Evaluation window

Exactly the same 114 monthly 21d periods used by the certified LTR comparator:

`2017-01-01 <= signal_date < 2026-07-01`.

The evaluator must fail closed unless frozen LTR reproduces:
- Top1 exact global winner: `10/114`;
- Top2 global-winner containment: `15/114`;
- Top3 global-winner containment: `21/114`;
- global winner retrievable in frozen Top10: `47/114`.

## Primary advancement rule — frozen before execution

v4 advances on the burned development set only if **both** hold over all 114 periods:

1. v4 Top2 global-winner containment is **strictly greater** than frozen LTR v1 (`15/114`);
2. v4 exact Top1 global-winner rate is **not lower** than frozen LTR v1 (`10/114`).

CAGR is diagnostic only and cannot rescue a failed ranking gate.

Report separately:
- full 2017–2026;
- 2017–2022;
- 2023–2026.

Secondary diagnostics, with no role in advancement:
- Top3 global-winner containment;
- top1 21d CAGR proxy;
- classifier score margin vs realized Top1−Top2 return difference;
- Top1/Top2 accuracy for the **best available ETF inside the shortlist**;
- mean rank assigned to the actual shortlist-best ETF;
- conditional global-winner Top1/Top2 rates on the 47 dates where the global winner was retrievable.

## Decision consequences

### If v4 passes

- do **not** promote from Original149;
- freeze a new disjoint Holdout-B before observing its performance;
- execute one promotion test only, with no tuning after freeze.

### If v4 fails

- permanently close the deterministic reranker line on Original149;
- do not create v5 or tune v4;
- next scientific line becomes preregistered **top-k allocation / sizing**, exploiting LTR retrieval recall rather than forcing a single-winner decision.

Confidence calibration remains a separate later task and is not part of v4.
