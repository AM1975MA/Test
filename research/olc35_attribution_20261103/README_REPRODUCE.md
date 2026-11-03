# OLC35 – Frozen USA performance reference and opportunity attribution

## Run

1. Unzip `OLC35_Attribution_USA_Guardrail_20261103.zip` to a writable directory.
2. Install Python >= 3.11, numpy, pandas, matplotlib (`pip install numpy pandas matplotlib`).
3. Run `python src/run_olc35_attribution.py`, then `python src/verify_olc35.py`.
4. See `RESULTS_IT.md`, CSV files in `results/`, and PNG figures in `figures/`.

Original archives in `input/` are immutable and checksummed before analysis. If any SHA mismatch occurs, computation fails closed. No external market-data downloads, no model fits, no orders or strategy changes. Generated outputs are deterministic. The verification re-derives oracle maxima independently from raw labels and cross-checks the two U.S. CAGR values.

The 'oracle gap' is only an EX POST upper-bound statistic; it cannot be interpreted as forecast skill, achievable profits, or the lost NAV of an execution variant. OLC17 and OLC19 use distinct execution assumptions and must not be mixed. U.S. original observed-price certification was missing in OLC32.
