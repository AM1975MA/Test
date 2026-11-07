# OLC69 — Research package

This is an isolated, non-production replay of a pre-specified monthly policy route. No source data is fetched from the internet. All included data are original project checkpoints; results are heavily mined historical research, not clean independent OOS.

## Contents

- `PROTOCOL_PRE_RESULTS.md`: preregistered on GitHub before test outcomes (commit d3c7290808ccdf5a574467d29ce6ffbf788b66db).
- `run_olc69.py`: rebuilds causal market-specific ridge forecasts, chooses action A/B/C/D, injects event-dependent weights and timing into OLC19 native engine, verifies constant-policy seven-array parity, and saves full daily accounting.
- `verify_olc69_independent.py`: independent NumPy Ridge matrix calculation and financial reconciliation.
- `make_report.py`: stable results comparison and 2024–26 annual table generator.
- `OLC67/native/`: only frozen original OLC19/OLC56 engine/inputs and support files needed for execution.
- `OLC68_PRESIGNAL_EVENT_DIAGNOSTIC.csv`: original OLC68 as-of features/paired policy outcomes.
- `OLC67_Strategia_ETF_Verificata.zip`: original frozen scorecard and daily return reference.
- `results/`: all fitted forecasts, pre-signal choices, event actions, daily returns, CAGR, drawdown, QA.

## Reproduction

Python >=3.10, numpy, pandas, scikit-learn. From this directory:

```bash
python run_olc69.py
python verify_olc69_independent.py
python make_report.py
```

Do not promote OLC69. The next meaningful implementation change is a *same-state event-level counterfactual simulator*, not optimization of this failed Ridge gate.