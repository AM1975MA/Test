# OLC72 — 125 feature native XGBoost family-aware test

Research-only, November 8, 2026. No production or main changes. Outcomes 2021–2025 mined historically, not independent OOS. Sources from `/ETF_Research/OLC08_Ripristino_20261101/` and `/ETF_Research/OLC19_Rischio_Rientro_20261102/` must be materialized into `/mnt/data/etf_source` (or change `SRC` in scripts). The new zip contains code, 30 XGB UBJ family-weighted models, predictions, QA, report, **not** the parent multi-hundred-MB source data.

## Rerun

```
python verify_exact_native_recipe.py
python run_olc72.py
python verify_olc72.py
python conditional_family.py
python verify_conditional.py
python diagnose_family_usage.py
python build_report.py
```

`run_olc72.py` verifies source SHA256, original EU/USA Return/FUSION score parity, then refits 30 models under original objective/hyperparams with only DMatrix feature_weights changed (1 / count of raw/pct/dev siblings). `conditional_family.py` reuses the frozen original XGB model binaries in parent source volumes and runs approximate matched conditional family swap (six prespecified families, 2 reps). Summaries in `results/`. The baseline original Return/FUSION is only a *ranking signal*; it differs from OLC19 context and trading strategy. No CAGR or trading recommendation is produced by this work.

Methodological differences from OLC71: USA original native models recovered from split checkpoint; exact re-training QA both markets; original XGB `colsample_bytree=.8` and original native economic rank labels; full 125 features with 46 equal family sampling weights; two-seed matched family perturbation (approximate conditional), both markets.

Run reproducibility environment: Python 3.10+, numpy 2.3.5, pandas 2.2.3, xgboost 3.1.3. Change in XGBoost version may perturb numeric results or the exact model parity check; do not claim parity if environment differs.