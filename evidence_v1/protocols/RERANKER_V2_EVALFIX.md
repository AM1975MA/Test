# Evidence V1 — Reranker v2 evaluator correction

Status: **FROZEN BEFORE VALID RE-RUN**

The first technical run of Reranker v2 (`run 37045478600`, artifact `11243968811`) is **INVALID AS EVIDENCE** because its evaluation code defined the winner as the best 21-day return **inside the retriever Top10 shortlist**. Canonical Evidence V1 diagnostics define the winner on the **full Original149 candidate universe** and then ask whether the retriever/reranker places that global winner at Top1/Top2/Top3.

This correction changes **only the evaluator**. It does not change:

- frozen Original149 data;
- frozen baseline source;
- Retriever LTR v1 configuration;
- reranker feature set;
- reranker target / 63-day maturity gate;
- reranker model class;
- reranker hyperparameters;
- annual expanding walk-forward schedule;
- preregistered advancement rule.

The invalid technical result must not be used for tuning or parameter selection.

## Correct evaluation

For each OOS signal date:

1. determine the 21-day winner from all available Original149 candidates;
2. keep reranker choices restricted to the historical OOS LTR Top10 shortlist;
3. score exact Top1 / Top2 / Top3 containment against the global winner;
4. retain CAGR and margin correlations as diagnostics only.

Corrected source path:

`evidence_v1/src/reranker_v2_nonlinear_evalfix.py`

Preregistered corrected source SHA256:

`97804291b154f096ca404fc194eba89cffc596fd269e93f2f6e6728cd0aa5779`

A workflow must fail closed if the executed file SHA256 differs from this value or if the frozen data/source manifests fail verification.
