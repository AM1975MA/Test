# Evidence V1 — Universe Sensitivity v1 anchor-window amendment

Status: **FROZEN BEFORE ANY VALID SUMMARY OR PERFORMANCE METRICS EXIST**

This amendment follows the original preregistration and the common-support amendment. It changes no scientific hypothesis, subset, model, training rule, metric or decision threshold.

## Second invalidated technical run

Run `37054571788` is **not evidence**. It successfully rebuilt all frozen panels and began the evaluator, but aborted before `PER_DATE_STABILITY.csv`, `SUMMARY.json`, provenance, result persistence or artifact upload.

The failure occurred when anchor A was requested for common-support rows dated before the frozen Retriever LTR checkpoint begins. Example missing keys were from `2007-11-30`. This is outside the preregistered evaluation window and therefore does not define any test outcome.

No summary/performance metric from this run was written, persisted or used to choose a model or threshold.

## Technical correction only

New thin evaluator wrapper:

- `evidence_v1/src/universe_sensitivity_v1_supportfix2.py`
- Git blob: `e356fab47ffb935c5a54663f72b87cd29118917a`

Rules:

1. B and C continue to train on the complete aligned common historical support available to both representations.
2. Anchor A remains the already-frozen Original149 Retriever LTR v1 OOS checkpoint.
3. A is looked up only on common-support rows inside the preregistered evaluation window `2017-01-01 <= signal_date < 2026-07-01`.
4. Every evaluation common-support key must exist in the frozen checkpoint; otherwise the run fails closed.
5. A is reranked on that exact evaluation common support before comparison to B/C.
6. The evaluator must still produce exactly 114 evaluation periods for U120, U100 and U70.

## Unchanged specification

The following remain byte-/logically unchanged from the previous frozen protocols:

- frozen candidate universes U120/U100/U70;
- reference vs native common-support alignment;
- recomputation of candidate-relative labels after support alignment;
- LTR v1 configuration and annual expanding 63-day maturity gate;
- `FEATURES_42`;
- 2017-2026 evaluation window;
- Top1 agreement, Top5 turnover, rank correlation and normalized rank displacement metrics;
- Top5 turnover as primary stability metric;
- decision rule requiring lower B Top5 turnover in all three subsets and at least 3/4 B stability wins in every subset;
- diagnostic-only role of performance metrics;
- Holdout70 exclusion from promotion evidence.
