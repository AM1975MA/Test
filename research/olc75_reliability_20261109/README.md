# OLC75 — Top2 leader reliability and allocation

**9 novembre 2026. Research-only.** The study does not alter original OLC19, OLC67, or the repository main branch. All windows are already researched and are not new out-of-sample evidence.

## Inputs from the preserved user Library

Place the exact archives at:

- `/mnt/data/OLC74_Causal_Allocazione_Top2_20261108_VERIFICATO.zip`
- `/mnt/data/etf_source/OLC16_Input_Code_Checkpoint_20261102.zip`
- `/mnt/data/etf_source/OLC14_Fitting_Risultati_20261101.zip`
- `/mnt/data/etf_source/OLC19_Rischio_Rientro_Checkpoint_20261102.zip`

Input SHA256 is recorded in `results/OLC75_QA.json`; the original OLC19 source hash is enforced on restoration. The archives are not duplicated into this ZIP. The latest OLC16 signal_date is 2026-06-30; no August–October 2026 research data were available. EU May/June 2020 have missing next-event pair labels, intentionally omitted from training.

## Reproduce exactly

Python 3.10+ with numpy, pandas, scipy, scikit-learn. Recreate the native OLC19 code and state without mutating the original archive:

```bash
python prepare_native.py
OPENBLAS_NUM_THREADS=1 python run_olc75.py
OPENBLAS_NUM_THREADS=1 python verify_olc75_independent.py
python build_report.py
```

`prepare_native.py` extracts unchanged OLC19 engine sources, parent dependency files, the EU/USA native Top2 state arrays and frozen control ledgers. `run_olc75.py` recovers the original 90 monthly signals per market, the original ET/XGB and Return scores and 3 seed snapshots, then trains monthly, with `pos <= t-2`, before running 40 account simulations under FAST_LOCK3. It writes 180 event forecasts, 40 daily paths, annual and period metrics. `verify_olc75_independent.py` reconstructs scorecard/annual/Brier calculations without importing the simulation engine.

## Outputs

- `REPORT_OLC75_IT.md`: decision, periods, forecast skill, allocation and PIT-source feasibility.
- `PROTOCOL_PRE_RESULTS.md`: immutable hypotheses, policy weights and promotion rule (registered on GitHub before viewing the new results; later pre-outcome correction of EU missing labels).
- `results/OLC75_CONSENSUS_PANEL.csv`, `OLC75_EVENT_FORECASTS.csv`: date-stamped features, labels, 3-vote consensus, seed dispersion, previous-month score, and prequential probabilities.
- `results/OLC75_CONSENSUS_DIAGNOSTIC.csv`, `OLC75_FORECAST_SKILL.csv`, `OLC75_PAIRED_BRIER_CI.csv`: diagnostic counts, Brier/log loss and month-block uncertainty.
- `results/OLC75_EVENT_WEIGHTS.csv`, `OLC75_SCORECARD.csv`, `OLC75_ANNUAL.csv`, `OLC75_DAILY_LOGRET.csv.gz`: native policy weights, CAGR, drawdown and full daily returns.
- `results/OLC75_QA.json`, `OLC75_INDEPENDENT_QA.json`: source lineage, exact OLC19 control, maturity QA and independent recomputation.

## Interpretation

H1 unanimity is not an independent-vote ensemble: Return, ET and XGB are trained on overlapping prices. The changes to weights are controlled simulated interventions with frozen O/H/L/C, not proof that the signal causes future relative outperformance. Holdings, flows and valuations remain **unavailable as point-in-time verified input data** for this historical cohort; modern holdings must not be backfilled into old event decisions. USA original observation mask, live bid/ask and total-return assumptions are not certified. No strategy was promoted.