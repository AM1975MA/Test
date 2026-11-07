# OLC62 — Upstream temporal features, 2026-11-07

Research-only OLC62, fixed protocol saved before outcomes. This folder contains 10 fitted temporal 126-feature LightGBM models, 18,099 historical predictions, monthly and Top2 results, and independent QA.

**Result: NO PROMOTION.** EU/USA MAIN 2021–2024 static Top2 21d mean return deteriorates versus both original FUSION and OLC61 static ECON21. The separate 2025 retrospective performance is favorable but NOT a fresh holdout. No portfolio NAV or CAGR from this experiment.

## Inputs (not redistributed)

Original ChatGPT Library:
- `/ETF_Research/OLC14_Fitting_Ranking_20261101/OLC14_Heads_Checkpoint_20261101.zip`
- `/ETF_Research/OLC61_Upstream_20261107/OLC61_Upstream_20261107_VERIFICATO.zip`, extract `results/OLC61_PREDICTIONS.csv.gz` and `results/OLC61_MONTHLY_METRICS.csv`.

Requires Python 3.10+, numpy, pandas, scipy, lightgbm, joblib and scikit-learn. Use a clean environment to preserve dependencies.

```bash
python run_olc62.py --heads /path/OLC14_Heads_Checkpoint_20261101.zip \
    --olc61-predictions /path/OLC61_PREDICTIONS.csv.gz \
    --olc61-monthly /path/OLC61_MONTHLY_METRICS.csv \
    --out results
```

`verify_olc62_independent.py` is included; its default paths assume the folder lives under a project root alongside `etf_source/` and `OLC61_Upstream_20261107/results/`. For an independent check in another directory adjust those three source paths at the bottom of the script, not the arithmetic.

`olc61_parent_unchanged.py` is an exact byte-for-byte copy of the prior OLC61 runner, imported for immutable eligibility, target and weighting semantics (SHA256 `d23d5efbf5de3ef59700a5356108364c29afc420c23c171699ef87f9ff4ec4ad`).

All CSV output is a **historical research diagnostic**. No inputs or dates beyond 2025 are independently prospective. Changes after outcomes are limited to QA bug fixes (handling two missing historic future labels and filtering OLC61 month-compare methods), without changing any model recipe, fitting data, target or thresholds.