# METEOR Titanium V2 — recovered official package

Start with `RECOVERY_REPORT.md`.

The historical selector recovery is exact: 56,500 / 56,500 decisions match the official frozen matrix. The authoritative strategy path is `frozen_paths/TITANIUM_CONCENTRATION_FRONTIER_PATHS.npz`, key `BALANCED`.

## Reproduce the audit

Install Python dependencies `numpy`, `pandas`, `matplotlib`, `pyarrow` and `numba`, then run from the package root:

```bash
python code/titanium_recovery_results.py \
  --frozen-paths frozen_paths/TITANIUM_CONCENTRATION_FRONTIER_PATHS.npz \
  --panel authentic/ORTHOGONAL_SCORE_PANEL.pkl \
  --membership authentic/SUPER_GOLD_BASKET_MEMBERSHIP.csv \
  --reg-paths frozen_paths/REG_W24_F005_S008_PATHS.npz \
  --daily /path/to/DAILY_OHLCV_ACTIONS_150ETF.parquet \
  --output-dir results_reproduced
```

The official 500-basket distribution does not require the daily parquet: it is computed from the original frozen paths. The parquet is required only for the separately labelled unrestricted-universe counterfactual.

Run `sha256sum -c SHA256SUMS.txt` to verify package integrity.
