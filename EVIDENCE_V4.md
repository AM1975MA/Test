# Evidence V4

## Status

**OPEN — universe freeze only; no V4 performance has been observed.**

## Hypothesis inherited from Evidence V3 diagnostic

On the fully disjoint Dev72 universe, frozen LTR scores strongly predicted future 21-day return **magnitude** but not **sign**:
- mean score-vs-return Spearman about -0.018;
- mean score-vs-absolute-return Spearman about +0.333;
- positive score-vs-absolute-return correlation in 94.7% of months;
- Top10 captured the global winner 60/114 times and the global loser 53/114 times.

Therefore V4 tests a materially new architecture:

`Stage 1 magnitude/tail retriever -> Stage 2 separately trained causal 21-day direction/sign head`.

The V4 architecture will not be selected or tuned on Dev72. It must be preregistered before any performance is observed on a new disjoint development universe.

## Phase A — Dev60 freeze

V4 will freeze exactly 60 ETFs, 10 per the same six structural macro categories.

To avoid performance-guided universe construction, V4 reuses the **exact candidate order frozen before V3 performance** in `evidence_v3/src/freeze_dev72.py`. It does not create or reorder candidates after V3 results.

It excludes:
- Original149;
- Holdout70;
- tested EU110/EU120 reference names;
- all 72 Dev72 names.

Selection remains first coverage-valid non-burned ticker in frozen category order. No performance, target or model statistic is allowed during freeze.

After Dev60 is frozen, the complete two-stage V4 architecture, training maturity, shortlist K, classifier hyperparameters, decision rule and advancement gate must be committed before the first Dev60 performance run.

## Data policy

- Original149: burned.
- Holdout70: burned diagnostic.
- EU110/EU120: previously tested.
- Dev72: burned V3 development/diagnostic.
- Dev60: clean until the first V4 performance run.
- No Holdout-B is opened yet.