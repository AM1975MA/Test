# OLC11: task-native top-opportunity selection

Research only. Read PROTOCOL.md and RESULTS_IT.md. The native target, probability of its top quintile, rank output and portfolio return are distinct contracts. No new CAGR is produced here.

This folder contains all 11 used source modules, two test files, fixed learner parameters and compact evidence. New complete binary data/model checkpoints are saved in Library, not silently claimed uploaded to GitHub. Restore the delivered OLC11 checkpoint to run on the authenticated prepared annual matrices. Do not load arbitrary untrusted joblib/pickle files.

Commands from this directory:
```
python -m pytest -q
python src/train.py --parity-only
python src/train.py --workers 3
python src/evaluate.py
python src/evaluate_learners.py
python src/audit_target_availability.py
python src/uncertainty.py
python src/verify.py
```
`train.py` verifies and resumes complete matching checkpoints; changing code/parameters creates a new contract and can trigger actual refits. `prepare.py` additionally requires original OLC09 and OLC10 parents to reconstruct prepared arrays; these parents are not needed for the other commands once arrays are restored. Existing main and production are unchanged.

Environment used: Python3.13.5, numpy2.3.5, pandas2.2.3, scikit-learn1.8.0, xgboost3.1.3. Do not claim bit-level reproduction in different numerical environments without a new verification.

Key outputs: NATIVE_LEARNER_SUMMARY.csv, NATIVE_OPPORTUNITY_SUMMARY.csv, TARGET_SUMMARY.csv, PAIRED_UNCERTAINTY.csv, TARGET_AVAILABILITY_AUDIT.json and VERIFIED_SUMMARY.json. Per-month records and every seed are retained in the delivered package.
