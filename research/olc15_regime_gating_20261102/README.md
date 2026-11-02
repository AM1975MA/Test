# OLC15 regime gating — reproducible prepared-input checkpoint

Research only, no live trading or production promotion. Read REPORT_IT.md, PROTOCOL_EXECUTION.md on GitHub(commit e6ae78bb016525645e72c3aaea61e7cc4b49f84d), and declared post-observation EXTENSION_FUSION.md(commit d0a03455a13ba2c9d653a146da06715337b8a00d).

## Restore and run
Extract OLC15_Regime_Checkpoint_20261102.zip to a fresh directory. Its root is olc15_regime_gating_20261102. The checkpoint is sufficient for this gate experiment from prepared historical forecasts; no base ETF models are refitted and no external data is downloaded.

Python3.13, numpy2.3.5,pandas2.2.3,scipy1.17.0,scikit-learn1.8.0. Other builds can produce small float-level differences; compare monetary outputs with the documented tolerance and discrete decisions separately.

```
python VERIFY_RESTORE.py
python -m pytest -q
python src/check_controls.py
python src/prepare.py
python src/run_gates.py
python src/run_fusion_gates.py
python src/evaluate.py
python src/replay.py
python src/coverage_and_trace.py
python src/analyze.py
python src/verify.py
```

Each annual model is a readable JSON; inputs and execution state are CSV/NPZ rather than externally executable pickle. Sources for the frozen engine are included. The chronological gate never receives current/future outcomes at prediction time. State proxies are local broad equities, not a complete macro taxonomy.

Historical simulations inherit price-survival,total-return/FX,cost and same-open assumptions. The full-year2023 portfolio diagnostics include January initialization; separate first-actual-order windows begin2023-02-01. Current/SMOOTH/FUSION roles and sparse expert disagreements are reported separately. No new regime benefit is claimed merely because a mixed portfolio outperforms a single expert.

Original data/files remain unchanged. Full binaries live in persistent Library; source modules, tests and readable protocol/results are committed to AM1975MA/Test on research/olc15-regime-gating-20261102. A manifest is not a binary upload. Sources are versioned individually under src/ and tests/. They are distinct from the entire prepared-input checkpoint.
