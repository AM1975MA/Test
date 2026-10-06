# Evidence V1 — Universe Sensitivity v1 common-support amendment

Status: **FROZEN BEFORE ANY VALID METRICS EXIST**

The original preregistration `UNIVERSE_SENSITIVITY_V1_PREREG.md` remains authoritative for the scientific hypothesis, subsets, model, hyperparameters, evaluation window, stability metrics and decision rule.

## Invalidated technical run

Run `37053782730` is **not evidence**. It rebuilt all panels successfully but stopped at the first isolation check before fitting/evaluating the LTR methods and before writing any result metric or artifact.

Observed technical condition:

- U120 full-reference panel filtered to candidate tickers had 132 `(signal_date,ticker)` keys that were absent from the natively rebuilt U120 panel;
- native-only keys: 0;
- therefore exact pre-alignment key equality was impossible.

This support difference is itself universe-dependent preprocessing behavior, not a model-performance result.

## Technical correction only

New evaluator:

- `evidence_v1/src/universe_sensitivity_v1_supportfix.py`
- Git blob: `dc2b9ec577283485537f05e6e39debb0696a68b3`

For each U120/U100/U70:

1. construct the intersection of available `(signal_date,ticker)` keys between the full-reference filtered panel and native panel;
2. restrict **both** B and C to that identical common support;
3. only then recompute candidate-relative 21/42/63 target ranks and `target_relevance`;
4. require exact key and label equality after alignment;
5. restrict frozen anchor A to the identical common support **before** reranking surviving candidates;
6. record reference-only/native-only rows, signal-date counts, and retention ratios as coverage diagnostics.

The evaluation still requires exactly 114 OOS periods for every subset. Failure to retain all 114 evaluation dates aborts the test.

## Unchanged scientific specification

No change is permitted to:

- frozen U120/U100/U70 membership;
- LTR v1 model or hyperparameters;
- annual expanding / 63-day maturity rules;
- `FEATURES_42`;
- A/B/C conceptual definitions except the necessary identical-support alignment;
- 2017-2026 evaluation window;
- primary Top5-turnover metric;
- the four stability metrics;
- the original decision rule: B must have lower Top5 turnover than C in all three subsets and win at least 3/4 stability metrics in every subset;
- diagnostic-only status of performance metrics;
- prohibition on Holdout70 as promotion evidence.

No metric from run `37053782730` exists or was used to choose this correction.