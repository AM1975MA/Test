# Opportunity lifecycle — diagnostic and proposal, not a new trading model

Read RESULTS_IT.md and PROTOCOL.md. The downloadable conversation package adds the extended REPORT_IT.md, complete diagnostic CSVs, four reference curves/ledgers and verification logs. The repository stores this summary, source, tests and essential verification. Large input archives are not implicitly uploaded here.

Place the three previously delivered archives named by REQUIRED_ARCHIVES.json in one directory. Verify and restore with:

```
python restore_inputs.py --archives /directory/containing/the/three/zips
PYTHONPATH=src python -m pytest -q tests
PYTHONPATH=src python src/run_diagnostic.py
PYTHONPATH=src python src/summarize_diagnostic.py
PYTHONPATH=src python src/verify_diagnostic.py
```

The inherited ten tests can be run in inputs/frontier with PYTHONPATH=src:previous/work:legacy/work. Tested Python3.13,numpy2.3.5,pandas2.2.3,scipy1.17.0,numba0.65.1,scikit-learn1.8.0,xgboost3.1.3. Exact environment in offline package. Do not load arbitrary pickle files; the restored inputs are authenticated by archive SHA256.

The four reference accounts retain legacy CL01 execution. Labels are static holding-at-horizon diagnostics, not future portfolio sequences and not a new CAGR. Actual incumbent extraction is verified against the saved ledger. Opportunities use same-date features; realized winners are labels only. The last flat NAV row is not a new investment event. A candidate missing an outcome is not replaced with another hindsight winner.

No new predictive model fitted, no production changes, no promised future performance. The proposed residual-return/action model still requires implementation and paired USA/EU validation. The research is historical and already selected, not a pristine holdout.
