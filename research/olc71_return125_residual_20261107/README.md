# OLC71 — Audit Return125 / information beyond FUSION

Research-only, 7 novembre 2026. Branch GitHub `research/olc71-return125-residual-information-20261107`. No modifications to OLC19, OLC67 or main. Every 2019–2026 backtest period is previously explored, not independently untouched.

## Dependencies

Python 3.10+ with `numpy`, `pandas`, `scipy`, `scikit-learn` and `xgboost` (for optional native XGB gain audit). Required original ZIPs already stored in the user's ChatGPT Library:

- `/ETF_Research/OLC08_Ripristino_20261101/OLC08F_01_FeaturePack_20261101.zip`
- `/ETF_Research/OLC14_Fitting_Ranking_20261101/OLC14_Fitting_Risultati_20261101.zip`
- `/ETF_Research/OLC19_Rischio_Rientro_20261102/OLC19_Rischio_Rientro_Checkpoint_20261102.zip`
- Original 125 feature-prior table `PRIOR_FEATURES_125.csv` (also included in this result archive).
- Optional native XGB gain audit: `/ETF_Research/OLC08_Ripristino_20261101/OLC08_03_RSI_Confronto_Verificato_20261101.zip`.

Copy files to one directory, set environment variable `OLC71_SOURCE_DIR` to that directory (default `/mnt/data/etf_source`). Do not use different historical price vintages without restarting source QA.

## Reproduce (in order)

```bash
python run_olc71.py
python run_family_diagnostics.py
python run_top10_residual.py
python feature_geometry.py
python original_xgb_gain_audit.py
python verify_olc71.py
```

`profile_inputs.py` is an optional schema/coverage inspector. The stage scripts validate source SHA256 and label/score keys. `results/OLC71_INDEPENDENT_QA.json` records completed post-run independent checks. The source-model gain calculation is available only for EU because the USA original UBJ models were absent in the examined archived RSI package; it is never interpreted as evidence for USA.

## Output and boundaries

- `OLC71_SUMMARY.csv` / `OLC71_MONTHLY_METRICS.csv` / `OLC71_BOOTSTRAP.csv`: score-only vs +125 prequential comparisons.
- `OLC71B_SUMMARY.csv`: pre-registered-after-A feature family diagnostic.
- `OLC71C_TOP10_SUMMARY.csv` / `OLC71C_TOP10_VS_FUSION_BOOTSTRAP.csv`: score re-ranking within original FUSION Top10.
- `OLC71_EFFECTIVE_DIMENSION.csv`, `OLC71_RANK_REDUNDANCY.csv`, `OLC71_FEATURE_QUALITY.csv`: structure, covariance dimension and missingness.
- `OLC71_ORIGINAL_XGB_GAIN_EU.csv`: EU only, internal model split importance.
- `OLC71_OOF_PREDICTIONS.csv.gz`, `OLC71C_TOP10_OOF.csv.gz`: per-row audit and recomputation of headline numbers.

Only 21/42-session *static forward* Top2 payoff and label-level errors are measured. **No new OLC19 portfolio replay, MaxDD or CAGR is claimed.** No live recommendation. See the detailed report for existing research OLC08F and Q/A limitations.

## OLC71D — original EU native-XGB family test

`python run_native_family_permutation.py` ricostruisce i Return XGB EU originali dal checkpoint `OLC08_03_RSI_Confronto_Verificato_20261101.zip` (oltre ai tre checkpoint originali OLC71A), verifica parità esatta Return e FUSION, quindi ricampiona insieme RAW/PCT/DEV per 46 gruppi in due repliche fissate. `python verify_native_family_permutation.py` ripete le verifiche indipendenti sui Top2 e riepiloghi. Output: `results/OLC71D_NATIVE_FAMILY_MONTHLY.csv`, `_SUMMARY.csv`, `_QA.json`, `_INDEPENDENT_QA.json`. Ricerca solo EU: gli originali XGB USA non sono nell'archivio disponibile.