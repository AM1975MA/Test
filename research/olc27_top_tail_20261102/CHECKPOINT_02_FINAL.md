# OLC27 checkpoint02 — final preservation and verification

2 November 2026. Research closed with **negative** matched performance on EU165 and USA149. Frozen protocol b50e756831cd7b237083fabe0fe2c901ddf8597d; pre-outcome correction 4306b6c4d790cc0dd759c1169938c06924f67eba. No modification to main, no trading or strategy promotion.

## Completed economic and independent verification
- Seven score procedures (AUTH, AUTH_ONLY, LONG_POOL, LONG_STRAT, three label-shuffle controls), 36 annual fitted classifiers in total.
- 56 complete saved portfolio accounts = 7 procedures x 2 markets x 2 risk contracts x 2 fees.
- All eight AUTH arrays reproduce OLC20 parent files exactly.
- All applied Top5 swaps match the saved decision log exactly.
- 32 genuine/control CAGR metrics recomputed independently from saved daily log-return series, maximum absolute difference 2.45e-15.
- Six local tests pass, including strict label maturity, balanced pooled training, future-label cutoff perturbation, deterministic seeds, Top5-only actions and decision parity.
- Cost-stressed accounts, FULL and yearly slices, OOS tail diagnostic, paired 6-month-block uncertainty and gross Open-to-Open switch attribution retained.
- No authentic candidate improves 2021–2024 CAGR in both EU and USA under any of the matched risk/fee contracts. Null frequencies are descriptive and not posterior probabilities.

## Persisted binary package in Library
Folder: `/ETF_Research/OLC27_TopTail_20261102`
File: `OLC27_TopTail_Results_20261102.zip`
Size: 9,521,765 bytes
SHA-256: `53ce519d4701ada54cec9464d614f65dd6169398b2368729abd360bf162d4717`
Contains 149 files; ZIP CRC verification returned no errors. Sidecar SHA-256 stored separately in the same folder. Includes model coefficients, score tables, complete authentic portfolio NAV, scorecards, tests and code. Parent OLC20/OLC26 upstream input binary assets are NOT duplicated and upstream raw-market completeness is not independently certified.

## Research limits
Historical sample heavily researched, no genuine new forward holdout, possible overlapping 126-session targets; original USA quote observation masks not preserved, raw total-return, FX, delistings and executable intraday fills unverified. The full test cannot be represented as live alpha or a posterior improvement probability.

See `RESULTS_IT.md` for full matched economic numbers, cost and risk differences, O2O switch diagnostics, null outcomes, and interpretation.
