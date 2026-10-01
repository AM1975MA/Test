# EU120 P45 walk-forward refit

This is a new experiment on the quality-gated frozen EU120 snapshot, evaluated from February 2017 through July 2026. It is not historical parity with the original 149-ETF P45 result of 46.9632% CAGR.

- Source: `data/eu120/raw_ticker_csv/` from Actions run 36597035280; five risk/reference series from `etf-trader-raw-149` artifact, run 36551650325.
- Training: expanding walk-forward on the same 120 ETFs. At every annual or monthly cutoff, source-only model fits use only labels whose exit date is strictly before the cutoff. All prices are frozen. No outcome or strategy artifact is used as an input.
- Router: original P44 BOCPD constants and P45 continuous mapping; EU120 Annual and Monthly shadow intervals update posterior only after `outcome_end < signal_date`.
- Comparators: Annual, Monthly, static 50/50, equal-weight buy-and-hold; 10 bp traded notional is passed to the source simulation.
- The runner inherits a compact reproduction of the original research execution from `europe120/p45_zero_shot_56/`. Exact certified Stage19 parity must be checked separately before claiming the new CAGR is directly comparable to 46.9632%.
- The dataset has 120 European-exposure names, not 120 confirmed EUR-quoted instruments. Its manifest has no listing-currency field.
- The result must be read from `RESULT.json` after the run completes; never use a prior result as an input or declare success from a partial checkpoint.

Invocation with checked-out data and raw149:
```bash
ETF_TRADER_ROOT="$PWD/vendor/etf_trader_v2" \
FROZEN_EU120_ROOT="$PWD/data/eu120" \
FROZEN_149_ROOT=/path/to/extracted/raw149 \
OMP_NUM_THREADS=2 OPENBLAS_NUM_THREADS=2 MKL_NUM_THREADS=2 \
python europe120/eu120_retrain/run_eu120_retrain.py
```
