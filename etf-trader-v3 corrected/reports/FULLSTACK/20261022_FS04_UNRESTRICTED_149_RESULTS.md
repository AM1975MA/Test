# ETF Trader V3 fullstack FS04 — unrestricted global 149 ETF source-only comparison

22 October 2026. Successful matched source-only global single-portfolio backtest [GitHub Actions 39841769495](https://github.com/AM1975MA/Test/actions/runs/39841769495), artifact **12453945376**. Exploratory historical only, NOT promoted. Refer to [preregistered protocol, including before-results software-gate fixes](./20261022_FS04_GLOBAL149_PREREG.md) and [source](../../fullstack_legacy/experiments/fs04_unrestricted149.py).

## Exact input contract and provenance

Original 149 ETF RAW snapshot from run 39482809691, identical source-only Titanium/S3B/Hybrid24 MA3 model predictions from full-stacked FS02 raw-rebuild run 39836842157. 114 monthly signal dates Jan2017–June2026; exact execution 2017-02-01 through 2026-07-01, 2366 market sessions.
Before any new global results the script reconstructs every original 500-basket Top1/Top2 holding from source-only predictions and certifies EXACT original FS02 500×2366 basket ticker identity; both original HighCAGR24 adjusted portfolio weights and macro systemic gross agree within 1e−12. Original 500-basket SHA256 36a45916b5d8191f3ccd206f39bf3fd3f1ed4bcaffd474e352b69c598f2b6a5e.
All three global arms run original unchanged V2 Hybrid24 producer 60% ET + 40% XGB; 40/30/30 smoothing, 1.10 power, .475/.525 Titanium/Tail mix; original continuous dynamic Top2, original DD-first, V6, HighCAGR24, 10bp actual traded dollar fee and original intraday engine. Only 149 eligible names unrestricted in one portfolio, not 500 separate baskets.
Arm (1) original V2 Hybrid24; (2) original ETF_TRAINER_V2 C4/SEVERE riskoff concentration to Top1 only if margin ≥.03 and both original ET and XGB prefer original Top1; (3) new V3 two-of-three ET,XGB and untouched CORRECTED Pair127 vote, same original chosen Top1/Top2 and exposure/risk. V3 Pair127 scores from frozen run 39700865721; without valid V3 OOS (2017) fall back to original ET+XGB. No added ETF search, leverage increase, model refit, label leakage or threshold optimization.

## Fee-adjusted results: ONE global 149 ETF portfolio

| Metric, single portfolio | Original complete Hybrid24 | ETF_TRAINER_V2 Stage19 | V3 majority 2/3 |
|---|---:|---:|---:|
| Full 2017–2026 CAGR | 33.4944% | 34.4741% | **34.7846%** |
| Full max drawdown | −31.3328% | −31.9313% | **−31.2195%** |
| Full Sharpe, rf 0 | 1.1761 | 1.1927 | **1.2015** |
| Full annualized traded notional | 13.191× | 13.061× | **12.930×** |
| Development 2017–2022 CAGR | 26.5758% | 28.0540% | **28.5239%** |
| 2023–2026 CAGR | **46.1421%** | **46.1421%** | **46.1421%** |
| 2022+ CAGR | 37.1885% | 38.1855% | **38.5400%** |

**Within the exact same current RAW, V3 majority exceeds the best original ETF_TRAINER_V2 by +0.3105 percentage points of compound CAGR**, better maxDD by ~0.712pp and Sharpe ~+0.0088. This modest advantage is descriptive and must not be compared with historical 43.14595% old-vintage global or fresh raw 31.603995% from 2 October, neither identical to this FS02 RAW/model snapshot. The historical global 43.15% is not lost or replicated here.

## Concentration / risk of overinterpreting improvement

Original ETF_TRAINER_V2 riskoff conviction acted on 13 trading days in 2019, 21 in 2020 and 17 in 2022; V3 majority on 13 in 2019, 22 in 2020 and 49 in 2022. There were **ZERO** concentration decisions in all arms for 2023–2026. The daily return series after January 2023 are exactly the same, and therefore 2023–26 46.14% CAGR provides NO fresh evidence of V3 superiority. The historic difference is confined to a small set of older 2020/2022 risk episodes.
Post-result descriptive 21-session calendar-block bootstrap 6000 draws of the global 149 single-portfolio daily paired log return difference V3 minus ETF_TRAINER_V2: mean annualized log-alpha **+0.002307**, 95% CI **[−0.003768,+0.008769]**. Zero inside interval; no convincing general uplift. Paired log alpha is not the arithmetic difference between geometric CAGRs. The 2017–2026 calendar has been repeatedly inspected and is not a virgin holdout.

## Validations and QA chronology

GitHub FS04 attempts 39841253358 and 39841439728 failed before global economics due missing scikit-learn runtime imported by original V2 source. Run 39841545315 failed during 500-basket reference guard because the initial diagnostic accidentally compared raw continuous producer weights against AFTER-HighCAGR24 weights from FS02 PATH.npz. These checks were corrected and recorded in the prereg protocol *before* FS04 portfolio outcomes. Successful run 39841769495 certifies exact original member ordering/selected ETF parity, positive source references and label/price causality. No changes to the tested 2-of-3 strategy or 10bp execution.

## Decision

FS04 is a **positive same-source full-global historical finding**, not production approval. The full 500-basket companion FS03 did NOT beat ETF_TRAINER_V2 in full mean-basket CAGR (22.4545% vs 22.4593%). FS04 global +0.31pp is concentrated in 2020/2022 and paired uncertainty includes zero. Therefore the target of robustly surpassing V2 across both market definitions is NOT yet demonstrated. Keep original Hybrid24/ETF_TRAINER_V2 as benchmark and all source code frozen; seek future not-yet-inspected market vintages and preregister later conditional risk calibration. Full 149 global must always be analyzed as a single portfolio, separate from 500x24 constrained basket mean/aggregate.

## Source and data

- Original 149 as-of FS02 fitted-source snapshot: [FS02 result](./data_run_39836842157/RESULT.json)
- FS04 complete source: [fs04_unrestricted149.py](../../fullstack_legacy/experiments/fs04_unrestricted149.py)
- Raw original matched 149 source, identical 500 trade names and risk budget checks: [GitHub Actions 39841769495](https://github.com/AM1975MA/Test/actions/runs/39841769495), artifact 12453945376
- Full exact daily NAV, as-of monthly holdings, risk, annual scorecards, manifest expected at data_run_39841769495, archived independently.