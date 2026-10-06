# Evidence V1 — Cascade v1: frozen LTR Top5 -> canonical Hybrid24

Status: **PREREGISTERED BEFORE EXECUTION**

## Scientific question

Does the already-validated frozen LTR retriever become a better final selector when its fixed Top5 shortlist is ordered by the already-frozen canonical Hybrid24 OOS score?

This is a development-only architecture test on burned Original149. It cannot promote a model by itself.

## Frozen inputs

### Retriever

`evidence_v1/checkpoints/retriever_ltr_v1/`

- frozen LTR v1 OOS checkpoint;
- shortlist is **Top5 only**;
- no retraining;
- no Top10 or alternate K;
- expected development facts used as fail-closed checks: LTR Top1 CAGR proxy `0.220630708412056`, exact global-winner Top1 `10/114`, Top5 global-winner containment `32/114`.

### Hybrid24 selector

`evidence_v1/checkpoints/hybrid24_oos_v1/`

- materialized source-only before this protocol;
- Phase-A run `37065765114` completed successfully;
- artifact `11253020356`, artifact digest `sha256:74fbeeb35eadeb625a86d5a1d15e6ad5d69a90a2c48223a3514be212918f5f18`;
- `OOS_SCORES.csv` SHA256 `661feb2b9b80997e78e51b4701a2f4d9501b1ac390ceb331d59bec837b0db4f7`;
- `OOS_SCORES.csv` Git blob `15d346c6723c85e9d7975254b07e20e4fbd2fe53`;
- checkpoint manifest Git blob `7c05170b816337a863b5f02f083a930b45fda8f2`.

No model is fitted in this cascade test.

## Single frozen cascade rule

At each of the 114 evaluation signal dates from `2017-01-31` through `2026-06-30`:

1. take the five names in frozen `Retriever LTR v1 TOP5.csv`;
2. join the canonical `HYBRID24_SCORE` for the same `(signal_date, ticker)` from the frozen Hybrid24 checkpoint;
3. choose exactly one ETF: the Top5 member with the highest `HYBRID24_SCORE`;
4. deterministic ticker alphabetical order is used only to break an exact score tie.

No LTR score blending, Hybrid24 layer substitution, learned reranker, confidence margin, allocation sizing, regime switch, or risk overlay is allowed.

## Evaluation

Forward performance uses the same frozen Original149 `fwd_ret_21` panel and the same 114 monthly 21d periods used by the previous Evidence V1 selector/allocation tests.

Primary comparators on exactly the same dates, universe and returns:

1. frozen **LTR Top1**;
2. **Hybrid24-only Top1**, i.e. highest canonical `HYBRID24_SCORE` across the entire eligible Original149 candidate universe.

Reported diagnostics also include:
- exact global-winner counts/rates;
- LTR Top5 winner containment;
- conditional cascade hit rate when the global winner is retrievable inside Top5;
- annualized volatility, Sharpe rf=0, max drawdown and Calmar of the monthly 21d proxy;
- 2017-2022 and 2023-2026 subperiods, diagnostic only.

The strategic Hybrid24 baseline CAGR of 31.60% is provenance/context only and is **not** numerically compared as if it were the same statistic: the cascade evaluation is a monthly single-selector 21d proxy, not the full basket/risk engine.

## Primary advancement rule — frozen before execution

The cascade advances only if **all** are true on the full 114-period development window:

1. cascade CAGR is strictly greater than frozen LTR Top1 CAGR;
2. cascade CAGR is strictly greater than Hybrid24-only selector CAGR;
3. cascade exact-global-winner count is strictly greater than LTR Top1 exact-global-winner count;
4. cascade exact-global-winner count is no lower than Hybrid24-only selector exact-global-winner count.

Subperiods and all other metrics are diagnostics and cannot rescue a failed primary rule.

## Decision consequences

### If PASS

The architecture may proceed only to a **new, disjoint Holdout-B**, selected and frozen before any cascade result on that universe is observed. Original149 remains burned and Holdout70 remains burned/diagnostic only.

### If FAIL

Close the Evidence V1 architecture search on Original149. Do **not** test Top10, Top3, alternate Hybrid24 layers (`BASE`, ET-only, XGB-only), score blends, nearby K values, or other cascade variants ex post.

## Anti-leakage / anti-overfit constraints

- Original149 only for this development test.
- Holdout70 must not be read.
- Both LTR and Hybrid24 checkpoints are immutable productive inputs.
- No training or parameter estimation occurs.
- No parameter is selected from cascade performance.
- One cascade configuration only.

## Frozen evaluator

Path: `evidence_v1/src/cascade_v1_ltr_top5_hybrid24.py`

Git blob: `aafff4f99552b23fc5e547690ee21b093625f741`
