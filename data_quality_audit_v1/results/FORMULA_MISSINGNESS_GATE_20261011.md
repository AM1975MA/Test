# Compact21 remaining missing base-feature formula gate — 2026-10-11

## Prior-work verification
Reviewed previous historical source checks #51, exact raw-window lookback diagnoses #52, MAD zero cause #53, residual missing decomposition #64, source-calendar age comparison #65. They do **not** explicitly map the remaining 11,641 cells to **each frozen base feature's formula-derived minimal required raw bar count**. This pass evaluates all Compact21 base feature definitions in exact versioned `vendor/etf_trader_v2/src/etf_trader/source_only/kernel.py`, including rolling moments, momentum, moving averages, GK volatility, volume surprise, market beta/correlation, autocorrelation and the derived acceleration/ratios. No model changes, no fitting, no prediction score comparison, no full price repair.

## Verified job and data
GitHub Actions [38136132049](https://github.com/AM1975MA/Test/actions/runs/38136132049) succeeded; pristine Original149 raw acquisition artifacts from 37121749852, α=1 Compact21 panel assets from 38094232042, three independent acquisition copies. Candidate row eligibility and missing masks match previous PRs. All base feature names are exhaustively covered by explicit formula rules and closed-coverage assertion in `data_quality_audit_v1/formula_missingness_gate.py`.

## Counts per source vintage
- 18,449 originally absent base/other Compact21 feature cells among the 1,665 otherwise eligible incomplete ticker dates.
- **18,401 cells (99.7398%)** have fewer raw historical observations prior to the signal date than the feature's formula-defined minimum horizon.
- **48 cells (0.2602%)** have adequate source history length but their `volume_surprise21` log-volume domain has nonpositive raw volume in the rolling history window; exact rolling min-periods/positive-volume count still requires direct replay verification and should **not** be labeled confirmed corrupt source.
- 0 missing raw signal dates, 0 missing required raw columns, 0 nonfinite required raw inputs and 0 positive-price invalid cases under tested conditions.
- All counts identical in 3 frozen acquisitions.

### Crucial qualification
This diagnostic is a **static necessary-history and domain-gate**, not a cell-by-cell recomputation of full pandas rolling feature outputs and numeric equality. It establishes a compelling legitimate warmup explanation for 18,401 cells but does not certify every feature formula numerically or detect all optional positive-volume window constraints. The residual 48 cells might be valid mathematically undefined or reflect illiquid/zero-volume feed bars; classify with exact raw-volume rolling calculation before approving any exclusion strategy. Dynamic feature missingness can also propagate through a rolling window despite available same-day price. No synthetic fills and no reinterpretation of zero-volume as zero trade return.

## Economic decision
No new CAGR or training is justified by this result. Source data gate remains NOT CERTIFIED due to corporate-action truth, suspect events and full MA3/Tail/Macro/Extra lineage. Do not adopt strategy changes until those gates are independently addressed. Production repo unchanged.
