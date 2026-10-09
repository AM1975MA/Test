# ETF INPUT QUALITY GATE V1 — 2026-10-09

## Hard boundary

NO training, ranking, feature selection, hyperparameter tuning, portfolio replay or CAGR before source/input validation. Work only in AM1975MA/Test, production Etf_trader unchanged. Use frozen three distinct Original149 Yahoo downloads (run 37121749852); do not cross-fill acquisitions, drop changed rows silently or force numerical identity.

## Raw data certification

Validate per download, ticker and date: schema, unique keys, price/volume positivity and OHLC ordering; inception/last session, gaps, unusual stale bars, outliers, volume zero/illiquidity, timezone and session calendar. Compare all three pairwise date/key coverages; detect altered OHLC and returns, including nonconstant revisions and adjustment factor effects. Flag suspicious rows rather than automatically deleting or smoothing. Yahoo corporate-action and adjusted-price semantics require independent source confirmation before claiming truth. Original research contract: adjusted OHLC via same-date Adj Close/raw Close, raw volume. Production data-loading semantics may differ.

## Full feature-input census, still no models

Recompute and audit every as-of feature used by Compact21 (all 125), Compact63, Tail, MA3, macro, opportunity and ensemble. For each feature record dependencies, history lookback, units, missing counts by ticker/date/vintage, source-missing versus structurally undefined, inf and invalid domain values, denominator zeros, percentile rank ties, near-zero MAD, outliers and revision amplification. Analyze exact data-lineage of each cross-vintage feature change, including both Compact21 and Tail downvol derivatives. Audit input-feature future-append invariance and label/entry/exit-session correctness separately; training labels must mature before annual fit cutoffs. Preserve all original labels and source files.

## Cleaning principles

Every change must have reproducible root-cause evidence, versioned algorithm, test that first reproduces the problem, source-specific auditable change log and no post-signal information. Never indiscriminately fill NaN with zero, round prices or merge two downloads. Classify verified invalid, legitimate missing, cold-start, structurally undefined and unresolved suspected provider issue distinctly. Preserve pristine source artifacts and affected-row list. All source adjustments must be financially meaningful, not tuned to predictive outcomes.

## Data-only acceptance gate

Require verified manifests for three snapshots, per-domain coverage/quality reports, reproducible deterministic causal transforms, validated exceptions and reconciled or explicitly unresolved upstream provider changes. Remaining uncertainties such as externally unverified corporate actions must be reported as NOT CERTIFIED, not marked clean. The gate needs interpretable residual differences, not artificial identical outcomes.

Only after data quality status is accepted, preregister separate model-stability experiments on frozen cleaned inputs; only after these pass predictive quality checks, perform full strategy CAGR/MaxDD/turnover tests.

## Evidence to preserve

Research audit found original source rolling_downvol requires negative-count threshold, generating artificial NaNs in downvol21/63/126. Replacing nine Compact21 downvol raw/pct/dev features removed 8195, 10807 and 12692 original missing entries in Repeat1 but reduced common rank MAD only 13% and worsened native Top1 disagreement from 50.00% to 50.58%. This did not correct Tail and was not adopted.

Original consecutive Yahoo downloads differ in OHLC for 137/149 tickers, no date or volume grid changes, with return changes as small as order 1e-6. These changes were not corrected; the raw provider source must be audited independently of learned-model sensitivity.
