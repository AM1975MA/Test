# ETF INPUT QUALITY GATE — evidence checkpoint 2026-10-09

Research only; immutable original inputs. NO model training, parameter selection or portfolio economic replay. NO production change to Etf_trader.

## Step 1 — original three Yahoo OHLCV acquisitions

Run [37942366260](https://github.com/AM1975MA/Test/actions/runs/37942366260), workflow `ETF_INPUT_RAW_CENSUS_V1`: **SUCCESS**. 149 tickers × three source acquisitions = 447 raw ETF files, each read and structurally validated for unique ordered dates, finite positive OHLC, nonnegative finite Volume, and bar high/low envelope. Across all 447 original ticker files: 1905 zero-volume bars, 123 close-to-close single-session return events |r|>20%, none |r|>50%, no weekend dates. These are **candidate anomaly counts repeated across acquisitions**, not known bad bars or unique market events. Every snapshot pair has 137/149 tickers with differing OHLC, zero volume differences and matching ticker calendars. Maximum absolute daily close-return differences: repeat 1–2: 3.39559772e-6; repeat 1–3: 3.41768331e-6; repeat 2–3: 3.79591429e-6. Artifact [ID 11622110733](https://github.com/AM1975MA/Test/actions/runs/37942366260/artifacts/11622110733): `RAW_PER_TICKER.csv`, each pair's per-ticker/field change CSV, full file SHA256 and JSON report.

**Uncertainties**: Yahoo corporate action reconciliation, independent issuer/exchange pricing, whether zero-volume bars indicate illiquid instruments, no automated independent expected calendar, no causal classification of ~1e-6 revisions and ex-post price adjustments. Structural PASS does not mean official economic data are clean.

## Step 2 — all fixed Original149 Compact and Tail input columns

Run [37942643873](https://github.com/AM1975MA/Test/actions/runs/37942643873), workflow `ETF_INPUT_FEATURE_CENSUS_V1`: **SUCCESS**. Full three-source original fixed source feature panels, 40230 rows per acquisition each, 125 Compact21 numerical inputs plus 60 Tail numerical inputs = 185 feature columns. **178/185** show at least one finite-value difference; **14/185** show a changed finite/missing mask among vintages; **106 pairwise missing-mask changes** (same source events counted separately across pairs and derived aliases). All 14 changing-mask feature names trace to the `downvol21/63/126` families and their `_pct`, `_dev`, and Tail rank aliases; no other changing masks observed in these frozen Original149 panels. Artifact [ID 11622446118](https://github.com/AM1975MA/Test/actions/runs/37942643873/artifacts/11622446118): full per-column source/null counts, per-pair rank and numerical drift statistics, machine-readable result.

Largest raw absolute observed feature differences across snapshot pairs include `downvol126_dev` 0.967647, `downvol21_dev` 0.911580, `downvol63_dev` 0.361579, `sign_entropy63_pct` 0.191275, `positive_frac63_pct` 0.151007, `rsi14` 0.098625. These are **feature units**, not portfolio returns. The downvol semantic source repair remains unpromoted after the adverse XGB quality/stability test.

## Step 3 — further original stored predictor-input panels

Run [37942985269](https://github.com/AM1975MA/Test/actions/runs/37942985269), workflow `ETF_INPUT_AUXILIARY_CENSUS_V1`: **SUCCESS**. Fixed upstream panels:
- TI_EXTRA.parquet: 40230 rows/vintage, 18 numeric non-label columns; 15 differ across at least one acquisition pair, 0 changed missing masks.
- TI_MACRO.parquet: 1620 rows/vintage, 18 numeric non-label columns; 10 differ, 0 changed missing masks.
- TI_MODEL_RAW_SCORES.parquet: 16986 rows/vintage, 9 numeric non-label columns; 8 differ, 0 changed missing masks. Model raw scores are outputs of historical models, **not raw financial features**; their comparison does not establish how much of variation is due to raw input versus fitting.
Artifact [ID 11622691359](https://github.com/AM1975MA/Test/actions/runs/37942985269/artifacts/11622691359) retains schema and drift CSV.

## Gate decision and unresolved checks

**NOT CERTIFIED / DO NOT ADVANCE TO MODEL EXPERIMENTS.**

The three audits are descriptive source/panel censuses with clear scope. We have NOT independently verified provider corporate-action and adjusted-price correctness; audited every input mathematical transformation for lookahead, near-zero denominators, leakage and investment meaning; reconciled 1905 zero-volume observations or 123 >20% return events; systematically distinguished historically undefined warmup NaN from bad missing price inputs; certified MA3 retained RAW_FEATURE_PANEL.pkl or the full ensemble's remaining features; or implemented any additional upstream correction. Full feature-profile samples are available as GitHub Actions artifacts.

The next data-only stage must prioritize (1) mapping the 106 historical missing-mask differences to exact ticker/date/feature cause, proving the entire dependency graph with downvol without changing the model; (2) the 123 extreme bars and 1905 zero-volume bar classifications by ticker/date and age; (3) upstream adjustment factor provenance; (4) independent MA3-panel audit and training label/as-of causality; and (5) controlled changes with regression tests, separately recording corrected vs still-uncertain data.

No universal fillna, no blending sources and no model fitting. Any attempt to infer a new CAGR from these reports would be invalid.
