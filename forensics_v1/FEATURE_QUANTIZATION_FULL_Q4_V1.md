# ETF_TRADER_FEATURE_QUANTIZATION_FULL_Q4_V1 — preregistration

## Purpose
Test whether deterministic 4-decimal quantization of the 125 Compact21 F2D input features, applied identically at training and inference immediately before the canonical Compact21 XGBoost ranker, reduces the full ETF_trader cross-snapshot instability.

This follows the preregistered diagnostic FEATURE_QUANTIZATION_V1, where Q4 reduced Compact21 rank mean absolute cross-snapshot difference by ~18%, while Q3 did not improve it. This full test is not a performance optimization and must not select parameters from CAGR.

## Frozen intervention
- Variant: Q4 only.
- Round all 125 F2D_FEATURES values with np.round(..., decimals=4).
- Apply after canonical feature construction and before Compact21 train/predict.
- No rounding of targets, Tail inputs, MA3 42 features, prices, risk inputs, execution inputs, or output scores.
- No other model, blend, seed, allocation, risk or execution parameter changes.

## Frozen inputs
The same three frozen Yahoo repeat snapshots used in the repeatability forensic.

## Full pipeline
For each snapshot:
1. canonical raw preparation;
2. canonical Titanium feature/label construction;
3. Q4 intervention only on Compact21 F2D values;
4. canonical Titanium annual walk-forward fit;
5. canonical MA3 panel and annual ensemble fit;
6. canonical Stage19 score/allocation/risk/execution;
7. full 2017-02-01 through completed 2026-07-01 replay.

## Baseline references
Native unquantized frozen-repeat CAGR values:
- repeat1 0.29753447746605727
- repeat2 0.30843704925646037
- repeat3 0.346770790748319
- CAGR span 4.9236313282261746 percentage points.

## Primary endpoints
- Q4 CAGR span across repeats.
- Pairwise daily Top1 disagreement and either-Top1/Top2 disagreement.
- Cross-repeat Final Score / decision agreement where available.

## Secondary endpoints
- mean CAGR, MaxDD, Sharpe, turnover.
- Q4 vs native decision changes per repeat.

## Interpretation
Q4 is considered a useful stabilization mechanism only if it materially reduces cross-snapshot decision/economic dispersion. A higher CAGR alone is not evidence of improvement. Original149 remains development/burned evidence; any later production promotion requires independent validation.
