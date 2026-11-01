# OLC14 chronological fitted ranking

Read RESULTS_IT.md and PROTOCOL.md. Research only; no main/production changes.

All17 runtime modules and4 test files are here. Prepared inputs,480 fitted base models, complete result tables and96 paths are in two complementary archives in persistent Library:
`/ETF_Research/OLC14_Fitting_Ranking_20261101/`

Extract BOTH `OLC14_Heads_Checkpoint_20261101.zip` and `OLC14_Fitting_Risultati_20261101.zip` into the same directory, preserving root `olc14_fitted_ranking_20261101`. Metadata and hashes: CHECKPOINT_03.json. They are not GitHub release assets.

From restored root:
```
python VERIFY_RESTORE.py
python -m pytest -q
python src/verify_models.py
python src/build_scores.py
python src/evaluate.py
python src/replay.py
python src/analyze.py
python src/verify.py
```
For explicit base-model refit:
```
python src/train_heads.py --prepare-parity
python src/train_heads.py --workers 4
```

Environment: Python3.13.5,numpy2.3.5,pandas2.2.3,scipy1.17.0,scikit-learn1.8.0,xgboost3.1.3,joblib1.5.3. Trusted joblib/pickle only. The pair restores prepared panels, not the entire original raw-data construction. Retain archived outputs before rerunning. No active process is implied by old logs.

TARGET_SELECT is a bounded four-candidate selection. Fitted beta/alpha combine predicted scores, not a search over every possible target formula. No CAGR in parameter fitting. Full report and packaging utilities remain in the final archive; repository scope is explicitly distinguished from binary persistence.
