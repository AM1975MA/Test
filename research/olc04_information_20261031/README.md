# OLC04 reproducibility and actual storage scope

Read PROTOCOL.md and RESULTS_IT.md. This is a matched information experiment, not a live trading release. Main is unchanged.

The repository contains the core feature module, model training, bank integration and persistent replay, feature tests and summaries. Complete auxiliary analysis, temporal verification, regression tests, model binaries,104paths and daily decisions are preserved in the delivered results/checkpoint ZIPs. This is NOT an implicit claim that all large parent inputs and model binaries were uploaded to GitHub.

Use the complete downloadable project for full reproduction. Restore source/olc03_selective_20261031/ from OLC03_Veto_Selettivo_Checkpoint_20261031.zip, SHA256731e6652a88ba5272753ff65faad8a9d984a4d851d7e30f3f135d1144bf63543. Validate the archive and its parent input manifests before deserializing any pickle/joblib. Run from the project root, with PYTHONPATH=src, OPENBLAS_NUM_THREADS=1 and OMP_NUM_THREADS=1: build_and_fit.py EU USA; replay.py EU USA; analyze.py; verify_paths.py; verify_information.py. Full commands and restoration script are in the ZIP. Output directories must exist (results,models,logs).

Observed Python3.13.5,numpy2.3.5,pandas2.2.3,scipy1.17.0,scikit-learn1.8.0,numba0.65.1. Accurate CSV round-trip parsing is required for exact refit parity; the report documents the detected precision failure and regression test.

Theoretical context only: Residual Momentum, Blitz/Huij/Martens2011, Erasmus repository https://repub.eur.nl/pub/22252/; Dynamic Trading, Garleanu/Pedersen, NBER15205 https://www.nber.org/papers/w15205. These works do not validate this ETF application and were not replicated here.
