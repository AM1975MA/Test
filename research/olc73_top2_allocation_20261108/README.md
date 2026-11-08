# OLC73 — Fixed native Top2 weight experiments

Research date 2026-11-08. All eight policies were preregistered before their outcomes in `PROTOCOL_PRE_RESULTS.md` (GitHub branch `research/olc73-top2-allocation-20261108`). No live adoption or change to OLC19/OLC67/main. Original 2019–July 2026 history has been extensively explored.

## Input dependencies and reproduction

Python 3.10+ with pandas and numpy. Requires the *original, immutable* OLC19 and OLC56 archives already stored in the user's Library, placed in these paths:
- `/mnt/data/etf_source/OLC19_Rischio_Rientro_Checkpoint_20261102.zip`
- `/mnt/data/files/OLC56_TESTS_20261106_VERIFICATI.zip`
- `/mnt/data/OLC67_Strategia_ETF_Verificata.zip` (existing audited OLC67 bundle; for OLC73 archived parity checks).

From this output folder, extract the OLC67 original bundle into a child `OLC67/` folder; then run:
```
python OLC67/extract_inputs.py
python run_olc73.py
python analyze_olc73.py
python build_report.py
```
The package includes `OLC67/extract_inputs.py` and `OLC67/run_olc67.py` for source restoration, but does not duplicate the original 165 MB OLC19 source archive or the original 0.86 MB OLC67 zipped histories. The script checks the SHA-256 of OLC19/OLC56 sources and reproduces the OLC67 baseline daily histories.

## Output contracts

- `OLC73_SCORECARD.csv`: all 64 native paths × 9 periods, CAGR, MaxDD, turnover, stop events and exposure.
- `OLC73_ANNUAL.csv`: 64 paths × 2019–2026 cumulative calendar-year returns (2019/2026 partial).
- `OLC73_EVENT_WEIGHTS.csv`: 90 events × 8 allocations × 2 markets, weights and fallback.
- `OLC73_DAILY_LOGRET.csv.gz`: daily net log-return ledger, each path.
- `OLC73_MONTHLY_LOGRET.csv`: calendar month aggregation for paired comparison.
- `OLC73_PAIRED_BLOCK6.csv`: paired descriptive 6-month circular bootstrap, seed 73008 and 4000 resamples.
- `OLC73_GATE.csv` and `OLC73_RANK_FLIPS_2024_2026.csv`.
- `OLC73_QA.json` and `OLC73_INDEPENDENT_QA.json`.

All returns are backtested under the source engine's stop fill/fee convention, not broker-executable returns. USA source lacks original `observed` mask; dynamic history checks fall back to finite-valid-close as in historical OLC56, a data limitation. No model hyperparameters or asset selection changed.