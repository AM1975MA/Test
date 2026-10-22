# V3 Complete Full Stack — source-faithful V2 integration

Source is copied unchanged from the original ETF Trader V2 archive (Test commit c349cac9dc352f86087bdd6a6ca99c72d17970f0), itself cloned from AM1975MA/Etf_trader. All vendored Git object IDs and SHA-256 file identities are documented in SOURCE_IMPORT_LOCK.json.

## End-to-end source-only sequence

Original RAW OHLCV 149 ETFs and category metadata -> causal yearly Titanium XGB compact rank -> S3B persistent raw-price clusters -> MA3 42-feature panel -> ExtraTrees60/XGB40 Hybrid24 producer -> temporal smoothing 40/30/30, exponent 1.10 -> 47.5 percent BASE + 52.5 percent Hybrid Tail -> monthly continuous dynamic Top2 -> DD-first prior-close market risk -> V6 resilient alternative -> HighCAGR24 dynamic exposure/Top1 threshold -> exact open-based daily intraday evaluation with one-way 10bp cost.

Original V2 source-only code is frozen under src/etf_trader and scripts/build_tit_r_source_only.py, build_ma3_panel_source_only.py, run_ma3_highcagr24_ensemble_source_only.py. Never edit these frozen V2 source files. Identical 500 canonical baskets of 24 ETFs are regenerated only from raw metadata with frozen SHA 36a45916b5d8191f3ccd206f39bf3fd3f1ed4bcaffd474e352b69c598f2b6a5e.

## First, isolated V3 experiment

scripts/run_v3_fullstack_pair25.py runs the original V2 baseline AND a V3 candidate in the same source-only DAG, market calendar and risk/execution engine. The one controlled change: during ORIGINAL full hybrid score formation, use 75 percent the frozen V2 Titanium base plus 25 percent the frozen original annual-OOS V3 CORRECTED Pairwise127 rank, then retain the original 47.5/52.5 producer score blend and ALL risk, Top2, and execution modules. V3 input takes only signal_date,ticker,variant,pred, not future returns or labels. Missing 2017 V3 scores leave V2 unchanged. Both models use identical fee and chronological source-only training.

Actions: .github/workflows/v3-fullstack-500-v2-pair25.yml. Frozen raw run 39482809691, V3 Pair scores run 39700865721. Strict source and label maturity audits; do not claim victory until original V2 baseline reconstructs with identical inputs. Historical years have already been explored, so any improvement remains research-only without untouched later validation.

Always distinguish mean individual basket CAGR from CAGR of aggregated equal-capital NAV; original 24.49 percent V2 was the former. The unrestricted global 149 ETF historical 43.15 percent and later source-only fresh 31.60 percent are separate universe/vintage references, not comparable to the constrained 500-basket result.
