# Original149 Compact21 residual base-feature missingness versus raw Yahoo histories — 2026-10-11

**Status: COMPLETED — partial source-root certification, not complete feature-formula certification.**

## Duplicate-prevention
Searched historical PRs before execution. The Original149 frozen source structural/price anomaly census and independent event adjudication were already performed in [PR #51](https://github.com/AM1975MA/Test/pull/51); [PR #52](https://github.com/AM1975MA/Test/pull/52) already established raw history warm-up for five long-lookback formulas. [PR #64](https://github.com/AM1975MA/Test/pull/64) newly inventoried 18,449 still-missing base/non-transformed feature cells among 1,665 otherwise-eligible Compact21 ticker-date rows. Present work **only cross-checks those 18,449 cells against each same-vintage frozen ticker raw Close calendar**, carrying forward known five lookback facts. No re-fitting, no parameter tuning, no CAGR.

## Completed experiment
Actions run [38135219538](https://github.com/AM1975MA/Test/actions/runs/38135219538) **SUCCESS**; three original Yahoo Original149 snapshots, frozen six candidate-feature panels from run 38094232042, α=1.0 (the two alpha masks had previously been shown identical). All three vintages have exactly 34,876 currently eligible and 1,665 incomplete rows. At each of three vintages, **18,449** base/other feature missing cells decomposed into:
- **6,808** cells of five previously verified feature families with fewer chronological raw price observations than the required horizon (mom126, mom252, mom252_ex21, breakout_pos252, ma_gap200). These are historical warmup cases; do not impute.
- **11,641** other feature cells whose same-vintage raw Close exists and is positive and finite at signal date, but whose **full feature formula, full lookback and mathematical domain were NOT audited by this job**. The source-calendar check alone cannot determine whether these reflect legitimate warmup, insufficient non-Close inputs, undefined moments/denominators or a feature defect.
- **Zero** cells in the categories missing raw signal-date, invalid raw Close at signal date, and known-window raw Close missing after satisfying sufficient lookback. This does not certify data from other price columns or corporate actions.

All three vintages yielded the same counts. The diagnostic does not modify any source, model, raw values, or feature.

## Technical guardrail
**Data-quality gate remains NOT CERTIFIED.** Never construe 11,641 cases as `BAD_DATA` merely because raw Close exists on signal date, nor construe them all as `LEGITIMATE_WARMUP`. Those 11,641 require the exact source-code formula/lookback dependency trace, including High/Low/Open/Volume for any relevant feature, and must be checked against PR #52 and #53 before adding more tests. Distinguish raw market facts from post-hoc Yahoo adjustments; do not blend snapshots, round values or `fillna(0)`. No production adoption.
