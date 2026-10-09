# Source data correction checkpoint — 2026-10-09

Source-only Original149, no external data added and no production changes.

## Root cause (verified by reading canonical implementation)
`kernel.rolling_downvol(lr,h)`: conditional `lr.where(lr<0)` followed by `rolling(h,min_periods=max(10,h//2)).std(ddof=0)*sqrt(252)`. This creates a discontinuity in missingness when the number of loss days falls below 10,31,63 respectively for h=21,63,126. The original source pipeline can have a full valid window of prices and still produce NaN. Changing the semantics to fixed zero-target semideviation on **all** h historical returns, with positive days contributing zero, removes this particular threshold while refusing incomplete source windows. The derived `_pct` and `_dev` features must be recomputed consistently. This is not unbiased imputation or a small neutral numerical repair, but an explicitly registered redefinition of 9 features.

## Read-only first-stage single-snapshot validation
GitHub run [37936052825](https://github.com/AM1975MA/Test/actions/runs/37936052825), **success**; canonical source gate and six tests **passed**; matched original Repeat1 TI downvol feature reconstruction; 114 monthly dates, 16986 rows, 149 ETFs, original eligibility 16986/16986 and unchanged, other 116 features, keys and targets byte-exact.

| Family | Original raw NaN | New raw NaN | Source-complete rows recovered |
|---|---:|---:|---:|
| downvol21 | 8195 | 0 | 8195 |
| downvol63 | 10807 | 0 | 10807 |
| downvol126 | 12692 | 0 | 12692 |

## Independent cleaned data construction for three retained consecutive snapshots
GitHub [37936573578](https://github.com/AM1975MA/Test/actions/runs/37936573578), **success**, three separate source-preparation jobs, original TI SHA256/source formula parity validated in each. Frozen source SHA for cleaned panels:
- repeat1 `e44c3d3559cd1524e6b9f92c84c5450b4895d10923afbbbc6a2e9a8df6c340bb`
- repeat2 `e8c25fbf4cefd2fd07dd83643ae024929cbe6818d66a758003f8a790ef340629`
- repeat3 `1c081a6dbdb5ee01db04d199441441e20b2ae17994c3d088915f395bd85b7c07`

In raw `downvol63`: repeats 1,2,3 respectively 10807,10809,10809 original null cells; all 0 with cleaned feature definition. In downvol21 8195 each; downvol126 12692 each; all cleaned 0. These raw null counts are not an estimate of the model's instability and do not by themselves establish improved future performance.

## Next sequential controlled model comparison
GitHub [37936989442](https://github.com/AM1975MA/Test/actions/runs/37936989442) started canonical unmodified XGB 2017-2026 annual training on all three cleaned panels, preregistered stability and quality preservation gates before any full strategy replay and CAGR. At creation of this checkpoint, that run is still pending; no new CAGR verified or claimed.

Status: source-level remediation QA **PASS**; scientific predictor/portfolio outcome **PENDING**. No files in production `Etf_trader` changed.
