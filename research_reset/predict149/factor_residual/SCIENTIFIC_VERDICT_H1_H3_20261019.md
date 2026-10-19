# Exact original149 — Factor–Residual Distributional (H) full experiment verdict
19 October 2026 | research/149-factor-residual-distributional-20261019

## Decision: a genuinely promising new *historical ranking signal*, but NOT a validated 30% CAGR strategy
Two real GitHub Actions **succeeded**, with every ETF-month prediction, daily next-open wealth path, strict conditional ranking and random-placebo trial permanently archived:
- Factor-beta plus signed residual quantiles: https://github.com/AM1975MA/Test/actions/runs/39225077114
- After-result factor forecast null vs 500 matched random portfolios: https://github.com/AM1975MA/Test/actions/runs/39225905272
Source `research_reset/predict149/factor_residual/run.py` and `stress/run.py`, frozen methodological decisions `PREREGISTERED.md` and `stress/PREREGISTERED_AFTER_H1.md`, SHA archives under corresponding `results/` folders.

**Strict result: all preregistered promotion gates FAIL**. No production deployment. Dataset fixed original 149 retrospectively surviving US ETFs, 112 total completed 21-session training/eval blocks, evaluation 64 anchors 2021–2026 and 9,536 ticker-month forecasts. All previous 149 and related periods extensively analyzed, so NOTHING is a truly new point-in-time or live out-of-sample holdout. Local EUR dealer spreads/FX, historic fund closures, distribution and tax, index actual exposures still unverified. Read all returns as shadow retrospective only with 10bp nominal one-way transaction fee.

## What was built (novel architecture)
1. Fixed 10 ETF proxy factor set: `SPY QQQ IWM VEA EEM TLT HYG GLD USO IEF` relative to 60/40 SPY/AGG benchmark. Proxy ETF returns are not distinct independent exogenous business data and not true PIT underlying holdings.
2. Per signal and ETF estimate a 10-exposure vector from **126 past daily closes** by centered ridge `β=(XᵀX + .005I)⁻¹ Xᵀy`. All posterior-asof invariance source-mutation tests passed.
3. Learn 10 projected future factor premiums with scaler+ridge `alpha=60` and 30 past factor-return predictors (5,21,63 closes; **fit only matured earlier anchors**, reuse quarterly); H1 score = βᵢᵀ predicted factor next21 premium. **Never use actual future factor returns at decision time**.
4. Compute label residual `future ETF benchmark-excess − βᵢᵀ observed realized future factor premiums` only for train anchors whose forward labels have fully matured. Train 3 LightGBM conditional q10/q50/q90 models on residual; H2 residual q weighted score, H3 sum factor + residual, H4 frozen old F3 after within-date as-of exposure neutralization. Original F3 backtest reproduced EXACTLY, no best-history parameter selection.

## Primary 64-anchor shadow economics

| Score | Net historical CAGR | Daily-open MaxDD | Daily log Sharpe | Conditional signed 21d ETF pair ordering |
|---|---:|---:|---:|---:|
| Frozen old F3 | 20.02% | −29.74% | .693 | 50.798%, 95% CI [49.33%,52.40%] |
| **H1 factors ONLY** | **24.62%** | −33.77% | **.793** | **52.974%, CI [51.04%,54.80%]** |
| H2 residual quantiles only | −5.28% | −56.93% | −.217 | 50.815%, CI [48.87%,52.68%] |
| **H3 factors + residual quantiles** | **23.53%** | **−28.78%** | .759 | **52.895%, CI [50.65%,55.05%]** |
| H4 factor-neutralized old F3 | 16.82% | −37.07% | .680 | 50.362%, CI [49.27%,51.51%] |
| Frozen N4 | 16.70% | −34.01% | .499 | 48.670% |
| Volatility-only selection | 6.14% | −36.36% | .197 | 50.316% |

H1 vs F3 mean matched pairwise signed concordance **+2.175 percentage points** (95% 3-anchor CI **[+0.183,+4.137]pp**), H1 paired risk-group per-era concordance 2021–23 **52.47%**; 2024–26 **53.58%**. Both selected ETF signed benchmark-relative log excess per 21-session anchor (before cost) positive: **1.11%** and **1.32%**, versus F3 **0.53%** and **1.11%**. H1 picks actual 15 worst ETF tail **15.63%** versus F3 **17.81%**. All positive directional indications within already-mined corpus, not fresh alpha.

H3 has numerically better MaxDD than F3, and its entire-period matched pairwise skill >50%; however paired H3-F3 uplift CI **[−0.022,+4.127]pp**, slightly includes zero, so no robust proof H3 beats F3 in ordering. H2 very bad economically (-5% annual CAGR, -57% DD): DO NOT pretend adding residual complexity helped.

**Factor amplitude validation failed**: H1 forecast factor future signed premium MSE **0.002454**, while a matured historical-mean factor premium would MSE **0.002069** (lower is better). This fact strongly limits interpretation: useful *relative ordering* does not mean correctly forecasting factor magnitudes or regimes.

**Residual quantile calibration:** pinball q10 **0.005799** vs unconditional historical residual q10 **0.006926**; q90 **0.005714** vs prior **0.006722** (both improved), median **0.011742** vs prior **0.011723** (not improved). q10 historical empirical coverage **10.025%**, q90 **88.9996%**. The residual distribution contains some useful conditional tail information in the mined history but fails to produce useful H2 rank/equity on its own. Do not translate marginal quantile coverage to deployable VaR guarantee.

## Explicit post-discovery adversarial stress, unchanged H1 weights or models

Because H1 24.62% looks so high on old data, an after-result protocol was frozen and executed. Same 64×149 forecasts, no retraining, with:
- **HM_MATURED_FACTOR_MEAN** score βᵢᵀ unconditional historically matured future factor mean: **12.18% CAGR, −43.18% MaxDD, 50.886% matched future pair ordering**.
- **HT_PAST63_FACTOR_TREND** score βᵢᵀ prior 63 completed Close factor return /3: **0.057% CAGR, −59.78% MaxDD, 48.826% matched ordering**.
- **H1** 24.62%, −33.77%, 52.974% paired rank.
- H1 vs HM conditional pairwise gain **+2.088pp** with interval **[+.144,+4.245]pp**, vs HT factor momentum **+4.148pp [1.168,7.160]pp**. However paired H1−HM *selected gross signed 21d excess* bootstrap interval **[−.831,+3.090] log percentage points** includes zero; and H1−F3 selected payoff interval includes zero.
- **500 independent RNG draws, not independent evaluation dates**: 250 same group/turnover null ETF quintets have median CAGR **9.97%**, 95th **17.00%**; 250 further matched as-of 63d volatility have median CAGR **14.47%**, 95th **20.35%**. **H1 24.62% beats 100% of those historical 250+250 placebo CAGR paths**. This is compelling diagnostic vs a within-sample conditional null but **not** evidence of prospective replicability.
- H1 daily-open DD **−33.77%** is worse than risk+class placebo median DD **−29.45%** and F3 −29.74%. Worst 5% daily returns for H1 **−4.11%** vs F3 **−3.70%**. Economic volatility/tail loss is a real defect and caused risk-science veto.
- Scientific null-stress **precommitted gate FAIL** even as its within-sample ranking and relative CAGR signals improve, because factor MSE < basic mean failed and required tail/DD limits failed.

## Main insight and next viable path

**New insight:** the factor component, not the idiosyncratic regression residual, is driving improvement in this corpus. The time-varying factor premium projection has some predictive *direction/ranking* signal beyond long-run mean and naive factor trend, even though point squared-error forecasting is worse. The actual usable target may be **ordering of relative factor opportunity** rather than perfect estimation of 10 future factor amplitudes. However looking at which method now won from many attempts is model-selection bias.

Immediate next research *on NEW untouched data*:
1. Freeze the full H1 and H3 forecasters and original F3, exact 10 proxies and parameters. Record genuine NEXT-OPEN predictions at each monthly anchor before their 21-session labels. Don't refit coefficients using future or use one outcome for selecting among these three; predeclare *one primary* (prefer H1 for scientifically demonstrated pairwise signal, with conservative risk model).
2. Source PIT tradable ETF list for an Italian/European investor and actual underlying holdings/market factor data publication/vintage for dates tested. US historical 149 can remain a feature engineering experiment but never a "149 European ETFs" live dataset.
3. Independently examine **risk-constrained** controls without choosing thresholds based on CAGR: as-of predicted Expected Shortfall and beta covariance; expensive improvement can only count when H1's MaxDD / daily ES improves without destroying matched pairwise skill. Don't create ex-post safety overlay based on known 2022 price outcomes.
4. Time risk and opportunity at 5/21/63 day horizons only after real independent data acquired. More price-only features or optimizer overlays in the same 2017–26 series have diminishing evidential value and risk performance cherry-picking.
5. If fresh data confirms factor ranking beyond as-of sector/vol controls, introduce agent/controller economic hysteresis to preserve winners and reduce unnecessary switches.
6. Goal >30% annual CAGR NET is ambitious and completely **UNPROVEN**, with potential risk escalation. Success judged by future net benchmark-excess and tail risk, not just total wealth.

Saved artifacts original source SHA `7bccf1b756bf3652280a254c7486fb43f1e805ebb4cdf10731cecc74007292e6`. Both jobs completed successfully and artifacts/commit immutable. Production `etf_trader` untouched.
