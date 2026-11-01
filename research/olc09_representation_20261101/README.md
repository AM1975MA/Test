# OLC09 representation and feature-information audit

Read PROTOCOL.md and RESULTS_IT.md. Research only; no strategy promoted or main change.

All nine new experimental source modules and all six test files are readable here. Models, cached matrices and complete312paths are preserved in the Library checkpoint, NOT automatically in GitHub release assets. The old binary-archive gap remains explicit. The complete downloadable results also include the longer REPORT_IT.md, all tables, logs and curves.

## Required parent
Extract both authenticated OLC08F_Checkpoint_Completo_Volume1_20261101.zip and Volume2 into parent/ under this root, then run python parent/RESTORE_LAYOUT.py. SHA256 respectively e2a188488251a1db2c5d6db8c7188f95ca4ec6a9a5487aec45cb183017ac0aaf and 7afbd101606330179fcc558ffd645c9744ac17451f3c0b631319267d8c193efa. Parent verifies4026files. Restore all three NEW OLC09 checkpoint volumes into the same root. They do not contain the parent again. Do not load arbitrary untrusted joblib/pickle.

Runtime used: Python3.13.5,numpy2.3.5,pandas2.2.3,scikit-learn1.8.0,xgboost3.1.3,numba0.65.1,scipy1.17.0,pytest9.0.2. Exact environment in the checkpoint. Set OLC09_ROOT to this folder if needed; single-thread BLAS/OMP is configured.

Commands: python -m pytest -q; python src/verify_results.py. For all312curve replays and statistics: python src/replay_models.py; python src/analyze_results.py; python src/prediction_diagnostics.py; python src/verify_results.py. No fresh prices are downloaded. Training is explicit: python src/prepare_inputs.py (includes4baseline refits), then python src/train_models.py --workers 4 (544newfits unless matching complete checkpoints already exist).

Do not call312curves independent strategies, prediction reload checks new refits, or the canonical-schema fix new alpha. Historical data, same-Open execution and repeated model selection remain limitations. Unscoped recursive test collection reaches historical copies with112import errors; this project has28passing tests and parent feature-lab20passing tests, not a claim about the whole repo.
