# TEST — Causal ETF market-regime gating experiment: FINAL results (2026-10-20)

**Completed, audited, not promoted.** Branch: research/original149-regime-gating-20261020. All source experiments and final artifacts retained as GitHub Actions 39485726248 and separate same-date/weight/year audit 39486130971. Frozen production untouched. Original frozen Original149 ETF dataset and full OOS cross-sectional scores from three previously trained experts; NEVER retrained any expert for this test.

## Question and rigor

Can a time-t market regime identify which among MOM21, TinyTCN125 daily-training and XGBRanker125 will score/return best at t+5? Is RMT spectral structure useful beyond volatility, trend, breadth and average correlations?

Full scores available for 476 original OOS signals 2017–June 2026. Use 2017–2019 *matured* past OOS expert outcomes solely for meta-history. **Evaluate all strategies on exactly 325 original weekly dates January 2020–June 2026**, all same ETF eligibility, five long-only ETFs, same next-session adjusted-open entry, five-session holding period, 20bp roundtrip, daily marked net NAV; no cash and no leverage.

Signal-time regime features from trailing prices: SPY 21/63 momentum, trailing 21 volatility, universe mom21 positive breadth, mom21 dispersion, mean 126-session contemporaneous ETF correlation; RMT adds 126-day first correlation eigenvalue/trace, normalized effective rank and ratio to heuristic iid Marchenko–Pastur upper bound. Complete 126-date history per ticker, no forward fill. Avoid interpreting MP edge as exact financial significance threshold.

Each year's 3-state diagonal Gaussian HMM fitted on *pre-year* market states and StandardScaler fitted pre-year only. Online posterior from explicit Hamilton **forward** filter, no smoothed future-backward posterior. Fixed temperature .01; returns only from prior matured OOS experts within last 104 weekly dates, half-life 52 weeks; conditioning similarity by state posterior dot product; shrink 24 pseudo observations to unconditional historical mean; blend 50% static equal/50% dynamic softmax. Other strategies: individual frozen experts, same-score equal 1/3, return-conditional trailing without regimes, low/high-vol × low/high-correlation buckets, BASIC_HMM, and RMT_HMM. No hyperparameter selection after evaluation.

## Primary results, exactly 325 weekly OOS decisions, Jan 2020–June 2026

| Strategy | Net CAGR | Daily path MaxDD | Daily Sharpe | Mean nominal 5-day cross-sectional RankIC | True nominal Top5 overlap |
|---|---:|---:|---:|---:|---:|
| MOM21 unchanged | **+18.8751%** | -34.9415% | **0.7472** | +.00317 | **14.34%** |
| B_DAILY_BASE TCN125 frozen | +8.2836% | **-33.5400%** | .4366 | +.05421 | 7.32% |
| E_XGB_BASE XGB125 frozen | +14.4791% | -41.5696% | .6306 | +.05322 | 11.14% |
| STATIC_EQUAL 1/3 ranking | +8.3551% | -34.9238% | .4466 | **+.05840** | 6.09% |
| TRAILING_ONLY no regimes | +9.6681% | -37.6726% | .4955 | +.05800 | 6.22% |
| SIMPLE_BUCKET volatility and mean corr | +9.9256% | -37.5026% | .5051 | +.05829 | 6.28% |
| BASIC_HMM six traditional state features | +8.1555% | -36.5411% | .4389 | +.05805 | 6.15% |
| RMT_HMM traditional + three spectral state features | **+8.1188%** | -36.9699% | .4398 | +.05803 | 6.09% |

**No RMT regime lift**: RMT_HMM produces costed CAGR +8.12% vs BASIC_HMM +8.16% vs same-score equal +8.36%, and less than the trailing-only +9.67%. Strongest frozen individual model over this span is MOM21 +18.88%; XGB +14.48% and TCN +8.28%. RankIC for STATIC_EQUAL higher than any expert despite worse economic Top5; as found in prior full experiments, global ranking not necessarily long-only profit.

Paired 5-week circular-block bootstrap descriptive 95% intervals of RMT_HMM *nominal 5-day Top5 return* delta:
- vs STATIC_EQUAL: **−0.00389 percentage points per weekly decision**, 95% interval [−0.0421,+0.0347] percentage points.
- vs BASIC_HMM: **−0.00106 percentage points**, 95% interval [−0.0363,+0.0380] pp.
- vs TRAILING_ONLY: **−0.02932 percentage points**, 95% interval [−0.0640,+0.00084] pp.
- vs MOM21: **−0.20244 percentage points**, 95% interval [−0.5882,+0.1876] pp.
Intervals are not valid for claims after extensive model mining, and do not prove equality.

## What the independent audit reveals

All 325 dates, eight strategy instances per date and unit-summing convex expert weights independently verified (Action 39486130971). Regime detectors *do* adjust weights, but are **strongly anchored near equal 1/3**:

| Meta-selector | average weight MOM21 | TCN | XGB | weekly std of MOM weight |
|---|---:|---:|---:|---:|
| STATIC_EQUAL | .3333 | .3333 | .3333 | 0 |
| TRAILING_ONLY | .3313 | .3319 | .3368 | .0279 |
| BASIC_HMM | .3345 | .3311 | .3344 | .0302 |
| RMT_HMM | .3268 | .3312 | .3420 | .0322 |
| SIMPLE_BUCKET | .3292 | .3313 | .3395 | .0362 |

The gate therefore changes the ranking mix only modestly; small differences between BASIC_HMM and RMT_HMM could reflect intentional conservative 50% static/24 pseudo-observation shrinkage as well as genuinely weak regime information. **Do not interpret this null as proof that regime recognition cannot work.**

Ex-post next-5d winning-expert identification using largest regime-allocated weight:
- RMT_HMM **30.46%** of weeks.
- BASIC_HMM **30.46%**.
- TRAILING_ONLY **32.62%**.
- Always predicting MOM21 would be correct **38.15%** of weeks (MOM21 is the most frequent ex-post best among three).
These are descriptive ex-post realized nominal portfolio comparisons, never used as time-t inputs.

## Annual diagnostic weekly costed returns (2026 partial year)

| Year | MOM21 | TCN125 | XGB125 | Equal | Trailing | Bucket | Basic HMM | RMT HMM |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| 2020 | +62.18% | +32.09% | +6.21% | +3.18% | +6.04% | +2.48% | +5.67% | +0.44% |
| 2021 | +6.00% | +20.53% | +18.55% | +24.04% | +21.08% | +28.11% | +20.34% | +21.48% |
| 2022 | +3.60% | +19.48% | +8.70% | +13.77% | +12.10% | +12.50% | +8.21% | +7.52% |
| 2023 | -13.10% | -1.42% | +1.90% | +2.30% | +2.93% | +4.11% | +4.86% | +3.30% |
| 2024 | -10.02% | -0.20% | +18.54% | -3.89% | +1.24% | +1.26% | -1.71% | +0.83% |
| 2025 | +35.26% | +17.72% | +18.37% | +11.90% | +12.43% | +9.61% | +7.27% | +12.19% |
| 2026 YTD | +62.23% | -24.18% | +22.35% | +4.71% | +7.54% | +7.90% | +8.96% | +7.90% |

These figures strongly show **ex-post complementarity**; in 2020/2026 MOM21 dominates, in 2024 XGB outperforms MOM strongly. But the causal gates DID NOT predict those leadership changes accurately. Annual returns are weekly-costed compounded within year, while headline CAGR/MaxDD/Sharpe use original daily path methodology; do not mechanically conflate them.

## Source, rigor and negative results

- Pre-registered experiment frozen before observing gate outcomes: tensor149_tcn5d/REGIME_PREREGISTRATION.md
- As-of 126d RMT features and pure forward filter: tensor149_tcn5d/regime_features.py
- Fixed 3-expert state gate and costed/economic replay: tensor149_tcn5d/regime_gate_run.py
- Temporal future-truncation and signal/label maturity tests: tensor149_tcn5d/test_regime_gate.py.
- Full actual executed run & ALL weekly scores/regimes/weights/costed NAV and REPORT.json: https://github.com/AM1975MA/Test/actions/runs/39485726248 (green)
- Independent audit, annual returns, weight distributions, winner forecasts: https://github.com/AM1975MA/Test/actions/runs/39486130971 (green)
- Immutable expert full runs: B TCN https://github.com/AM1975MA/Test/actions/runs/39478752782 (B job succeeded; original mixed workflow overall failed on two XGB jobs); XGB https://github.com/AM1975MA/Test/actions/runs/39479754815; MOM https://github.com/AM1975MA/Test/actions/runs/39455244701.

## Decision and next falsification

No promotion to production. This HMM + RMT Bayesian-style conservative gating **does not produce improved global RankIC, returns or drawdown**. The data still suggest different expert strengths over time, but detecting a regime is not equivalent to *predicting next week's winning expert*. 
Next preregistered *new* experiment, if pursued: a small directly supervised meta-expert classifier/regressor trained only on matured historical OOS expert basket return differentials, with 1) simple vol/correlation features, 2) spectral RMT features in ablation, 3) strong expert-prior and turnover penalty and a constant-weight benchmark, 4) strict inner chronological model selection and 2020–26 rolling evaluation; avoid fitting high-dimensional gating on 325 total weeks. Explicitly compare hard switching against soft weighting; hard switching increases turnover and estimation risk. Independent later or disjoint-universe evaluation is still necessary.

**Limitations**: retrospectively fixed survivor roster of 149 ETFs, Yahoo-adjusted open economics, fixed execution costs, extensively mined 2017–26; bootstrap intervals exploratory, not robust live forecast validation. The current fixed 0.5-static mixing and pseudo-count24 may mask true structure; cannot claim absence of useful regimes from this one conservative protocol.
