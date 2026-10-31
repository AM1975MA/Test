# OLC-01 research implementation

Read PROTOCOL.md, PROPOSAL_FILTER_DIAGNOSTIC.md and RESULTS_IT.md. Initial model predictions and subsequent stateful portfolio experiments did not earn paired USA/EU adoption. Main and production unchanged.

The repository preserves the core model/feature/controller/runtime generator/replay files. The complete delivery ZIP includes those exact files plus generated action_engine.py, tests, full analysis and independent verification scripts, restore helper, source hashes, 72 models, forecasts, 88 NAV/ledger paths and all decisions. The checkpoint additionally includes prepared input panels and states. No implicit claim that all large inputs/models were uploaded to GitHub.

To rebuild from raw sources, use the supplied restore_sources.py with the four authenticated prior ZIPs: ETF_Opportunita_Permanenza_20261031.zip; ETF_Frontiera_USA_Europa_Risultati_20261031.zip; EU_Original39_RH50_Checkpoint_20261031.zip; ETF_Rimedi_2020_2023_USA_Europa.zip. REQUIRED_ARCHIVES.json in the delivery pins their SHA256. Set OLC_SOURCE_ROOT to restored opportunity_lifecycle_20261031. Execute RUN_ALL.sh in a new copy; it refits the models and overwrites generated outputs. Do not load unverified pickle/joblib files.

Runtime observed: Python3.13.5,numpy2.3.5,pandas2.2.3,scikit-learn1.8.0,numba0.65.1,xgboost3.1.3,scipy1.17.0. Exact environment and scoped test logs in delivery. The 431 historical test-collection errors are explicitly recorded, not suppressed as a passing whole-repository test.

SOURCE_CODE.tar.gz in the delivered package contains every new source/test and restoration file; it is not implicitly claimed uploaded here. The local complete report has more detailed provenance and interpretation than the concise repository summary. No model probability forecast, live fill certification or universal best strategy is claimed.
