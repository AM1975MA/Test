# Evidence V3.1 — Category-balanced LTR6

Status: **PREREGISTERED BEFORE EXECUTION**

## Hypothesis

The Dev72 baseline-transfer result shows strong broad winner retrieval but poor economics from globally concentrating on the highest LTR scores. A structural category-balanced decision layer may convert the causal within-category rankings into a more robust portfolio without modifying or refitting the model.

## Frozen inputs

- Dev72 frozen universe and six macro categories.
- Frozen causal OOS predictions from `evidence_v3/results/ltr_baseline_transfer_dev72/PREDICTIONS.csv`.
- Prediction SHA256: `fafe49e44bd24a250ecb023338ef97696f79767404b281ff1d04af1f890c14b5`.
- Baseline summary SHA256: `fb898837f35c2b50febddfd575dffe2c56d7bec43ab7d60252afb2ebb0576fa9`.
- Dev72 universe SHA256: `412e577eab42cf9978fe57d6e42c62f9959aa0e46667ee5070aa3a788b9b5778`.

No model is fit or refit in this test. No network is permitted.

## Exact decision rule

For every evaluated signal date:
1. join each ticker to its frozen `macro_category` from Dev72 `universe.csv`;
2. within each of the six categories, sort by frozen OOS `LTR_SCORE` descending, ticker ascending for deterministic tie-breaking;
3. select exactly the first ticker in each category;
4. hold the six selected ETFs equal-weight, exactly `1/6` each;
5. period return proxy is the arithmetic mean of their frozen `fwd_ret_21` values.

All six categories must be represented. There is no category omission, category performance weighting, global Top-K threshold, volatility filter, score-proportional weighting, cash allocation or regime rule.

The number six is structural: Dev72 was frozen as six equal macro categories before any V3 performance result.

## Comparators

On exactly the same evaluation dates:
- frozen LTR global Top1;
- frozen LTR global Top5 equal-weight;
- Dev72 Universe-EW across all 72 eligible ETFs.

The evaluator must fail closed unless it reproduces the Phase-B baseline values at 1e-12 CAGR tolerance:
- periods: `114`;
- global Top1 CAGR proxy: `-0.07567660003526067`;
- global Top5-EW CAGR proxy: `0.034215706909629384`;
- Universe-EW CAGR proxy: `0.08524482878917694`.

## Evaluation

Full window: 2017-01-31 through 2026-06-30, 114 periods.

Diagnostics are also reported for:
- 2017-01-31 through 2022-12-31;
- 2023-01-01 through 2026-06-30.

CAGR proxy uses the frozen monthly-compounding convention `prod(1+r)^(12/N)-1`.

Volatility, Sharpe-rf0, maximum drawdown, positive-period rate, category turnover and selected tickers are diagnostics only.

## Primary advancement gate

All three conditions must hold:
1. Category-balanced LTR6 full-window CAGR proxy > Dev72 Universe-EW full-window CAGR proxy;
2. Category-balanced LTR6 CAGR proxy > Universe-EW CAGR proxy in 2017-2022;
3. Category-balanced LTR6 CAGR proxy > Universe-EW CAGR proxy in 2023-2026.

This deliberately requires economically positive excess performance in both broad subperiods rather than allowing one regime to drive the full result.

## Decision rule

- **PASS**: freeze the exact category-balanced LTR6 architecture. Do not make further changes on Dev72. The next scientific step is to construct and freeze a new disjoint Holdout-B before a one-shot transfer/promotion test.
- **FAIL**: close the category-balanced use of LTR on Dev72. Do not test category weights, omitted categories, top-2-per-category, alternate K, score weighting, volatility weighting or nearby allocation variants on Dev72.

Dev72 is already burned development data. This test itself cannot support a promotion claim.