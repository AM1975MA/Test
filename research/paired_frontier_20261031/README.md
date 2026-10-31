# Paired frontier: USA149 and EU165

Read PROTOCOL.md, RESULTS_IT.md and SUMMARY.json. All research is historical and no strategy is deployed.

The repository preserves actual feature, model-fit, replay, inference and verification source. The conversation packages additionally preserve 1,440 full daily paths/ledgers, all forecast audits, 80 annual model binaries, 16 imputers, prepared panels, environment and file hashes. Large binary/data outputs are NOT claimed uploaded to this Git tree. Full REPORT_IT.md and build_report.py are in those packages; RESULTS_IT.md is the compact source-backed repository narrative.

## Restore authenticated dependencies
Download the previously delivered EU_Original39_RH50_Checkpoint_20261031.zip and ETF_Rimedi_2020_2023_USA_Europa.zip. Run `python restore_dependencies.py --archives /path/to/downloads`. It checks SHA-256, restores sources/raw data and creates Linux/WSL symlinks. Python 3.13.5; principal observed versions numpy2.3.5 pandas2.2.3 xgboost3.1.3 numba0.65.1 scikit-learn1.8.0. Full freeze is in the delivered package. Do not load untrusted pickle/joblib files.

## Reproduce from project directory

```
export OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1
PYTHONPATH=src python -m pytest tests -q
python src/native_screen.py
python src/calendar_rebuild.py EU
python src/calendar_rebuild.py USA
python src/calendar_train.py EU
python src/calendar_train.py USA
python src/verify_calendar.py
python src/calendar_replay.py
python src/execution_sensitivity.py
python src/verify_outputs.py
python src/analyze_frontier.py
python src/predictive_attribution.py
```

Training overwrites generated models in this research directory. Regenerate all downstream data after any source/input change; do not silently reuse scores. Original native references stay unchanged. Each newly evaluated configuration is run in both markets. Neither new coverage nor passing tests certify dividends, survivorship, spread or live fills.

## Implementation deviations recorded
Initial cluster validator required future-label column names even though membership only uses historical identities/prices. NaN/NaT placeholders were supplied instead of future outcomes. EU sovereign instruments are recorded as SOVEREIGN_EUR and were mapped to the source defensive cluster, not cash. Initial failures produced no economic outputs. The final summary initially collided with an existing stage column; renaming it source_stage fixed summary assembly without changing forecasts or NAV. Logs are retained in the delivered package.

No process is assumed to continue after this response; this experiment lot is complete. No production/main change.
