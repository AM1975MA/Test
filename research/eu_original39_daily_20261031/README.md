# European Original39 / RH-50 retest

Read PROTOCOL.md and RESULTS_IT.md first. The test is a declared European port, not DUAL-01 and not an executable-live certification.

Core training, market adapter, audited engine, replay and unit tests are versioned here. Unchanged helpers engine_prepare.py, instrumented_engine.py, reconcile_math.py and test_reconciliation.py are in audit/component_reconciliation_20261031/ on this same branch; copy into work/ when restoring. Original vendor source must be restored at source/research/tail-only-and-allocation-ablation-20261017/ from commit13443836649d0f107d2063eb7acc1039135d6e9b. Create selected -> source for the original helper path. Do not substitute a corrected kernel.

The delivered offline checkpoint includes all helpers, raw inputs actually used, native European Hybrid forecasts, annual Return-Rank model binaries/predictions, prepared states, all50paths and every daily ledger. The downloadable results-only ZIP includes report, code, tables and curves, excluding the large raw input/checkpoint directories. Large inputs and models were not silently claimed uploaded to this repository. Hash manifests document the exact delivered content.

Frozen US inputs: yfinance-repeatability-v1-raw.zip, run37121749852 artifact11272972639; compact21-tail-factorial-full.zip, run39058118631 artifact12110461075; tail-only-allocation-counterfactual-full.zip, run39060389253 artifact12111590600. EU input: ETF_TRADER_V5_GERARCHICA_EU165_20261031.zip from the user's Library, specifically source_v4/input/EU165_SPECIALISTS_20261029.

Commands after restoration, from work/: python us_control.py; python train_eu_return.py; python prepare_eu_state.py; python -m pytest -q; python run_audited_replays.py; python run_additional_diagnostics.py. Complete offline scripts diagnose_daily.py and verify_outputs.py reconstruct the per-day explanation and independent accounting/statistics checks. No optimization occurs in these commands. Clear or verify model checkpoints before requesting a fresh refit; never silently reuse stale predictions after changing code or data.

Observed environment: Python3.13, numpy2.3.5, pandas2.2.3, xgboost3.1.3, numba0.65.1, scikit-learn1.8.0. Exact pip freeze is preserved in the delivered checkpoint. Input prepared pickle files were generated in this run, not accepted from an unknown source; do not load arbitrary untrusted pickles.
