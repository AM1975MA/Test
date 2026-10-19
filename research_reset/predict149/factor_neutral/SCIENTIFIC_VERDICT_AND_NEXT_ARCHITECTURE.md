# Frozen F3 as-of factor/vol matched directional skill: EXECUTED verdict
Date: 19 Oct 2026. Branch `research/149-f3-factor-neutral-diagnostics-20261019`. All results source-backed from Action https://github.com/AM1975MA/Test/actions/runs/39223308774 — no model refit, no new portfolio, and no tuning after metrics.

## Falsification experiment
Frozen F3/N4/F2 forecasts for the exact same original149 universe, 64 matured evaluation anchors 2021–26 and 9,536 ETF-months. At each signal choose every pair within the same coarse macro category AND as-of 63-session volatility difference within **0.20 in log units**, a precommitted risk-matching restriction. Evaluate whether the forecast with higher score also has higher **actual forward 21-session benchmark-relative log return**. Future outcomes are used only to score (NEVER to select pairs). Bootstrap circular blocks of 3 calendar anchors, equal weight to each anchor because within-date ETF pairs are NOT independent. Exactly **40,396** matched comparisons overall, minimum 525 per date, median 631.

### Measured *matched conditional* directional concordance
- F3 frozen signed q10/q50/q90: **50.798%**, 95% 3-anchor interval **[49.375%,52.379%]**: NOT significantly better than random 50%.
- Original N4 classifier for winning raw Top15: **48.670%** [47.688%,49.634%].
- F2 conditional probability-of-positive times signed magnitude: **50.860%** [49.699%,52.082%], not significantly better than chance.
- As-of volatility rank: **50.316%** [48.977%,51.706%].
- F3 minus N4 = **+2.128 percentage points**, paired CI **[+0.737,+3.622]pp**: a genuine within-historical-study incremental ranking improvement against N4 but *does not establish absolute predictive skill*.
- F3 minus F2 **−0.062pp**, CI [−1.212,+1.153]pp: no evidence F3 better than F2 once risk matched.
- F3 minus vol-only **+0.483pp**, CI [−1.337,+2.341]pp: no evidence stronger than as-of risk-only matching.

By era, F3 same-risk/group concordance 2021–23 50.510%; 2024–26 51.146%; N4 48.316% and 49.096%. Both F3 point estimates >50% but weak. Preregistered conditional directional evidence gate **FAIL** because F3 lower CI <=50%. This is not a proof future F3 will fail; it bars claims of confirmed skill from the already-mined 149 study.

### Quantile uncertainty calibration
Observed empirical P(Y < q10) **10.717%** (nominal 10%) and P(Y < q50) **49.140%** (nominal 50%); P(Y < q90) **87.720%** (nominal 90%). Thus central predicted 10–90% interval covers roughly **77.0%** instead of nominal 80% (from marginal rates, assuming coherent q10<=q90 and no ties). Upper tail undercovered by ~2.28pp overall and much more in 2024–26, when q90 coverage falls to **86.137%**; q10 cover 11.201% in 2024–26 vs 10.316% in 2021–23. Calibration drift exists, so the old q-weighted pseudo-mean is not a guaranteed true mean, and marginal uncertainty intervals cannot be assumed calibrated in markets after distribution shifts.

### Result: candidate not a confirmed independent alpha engine
F3 20.02% historical CAGR on selected Top5 previously beat archived N4 16.70%, with −29.74% instead of −34.01% MaxDD, but when class/volatility were matched F3's 20.02% was only **86th percentile** of 250 conditional random wealth curves (median 15.34%, 95th 23.03%) and 3-anchor bootstrap excess payoff CI included zero. Present paired audit **supports rejecting price-only feature-model shopping** on same corpus. Positive F3-N4 paired uplift does not imply 30% CAGR possible.

## New framework that addresses missing information (research plan, NOT an executed predictor)
**A: PIT economic exposure ontology first**:
1. Each ticker mapped as-of to index/holdings, issuer, benchmark, sector/country/duration/FX/commodity futures carry, fee, fund inception/delisting, hedged vs not and leverage status. This must not use today's known ETF holdings as historical if changed. Stronger exposure map than six coarse classes. Verify ISIN + actual exchange+quote currency before calling investment feasible for Italy. Public holdings snapshots useful only from their stamped publication date.
2. Market factor return and volatility as-of vectors `f_t` including equity beta/growth, credit, real duration, commodity curve/carry, USD FX, liquidity risk and option term structure. Timestamp original publication and availability + release lag; no retrospective revised macro values without vintage proof. First check provider connectivity/coverage before fitting.

**B: hierarchical distributional return signal**:
Model ETF future signed benchmark-relative log return as `Y_{i,t}=beta_{i,t}^T Z_{t→t+h} + e_{i,t→t+h}`. Estimate past `beta_{i,t}` only using data known <=t. Independently predict distribution of *future factor shocks* and *ETF peer residual alpha* with per-asset partial pooling to control 149 x 64 overfitting. Never plug realized future factor shocks into an as-of forecast. Fit 5/21/63 horizon **with frozen weights/priors**, train only matured labels and proper scores. Use heavier-tailed conditional distributions, risk mean and ES; do not assume tail 5/95 extrapolation empirically validated by only 64 dates. Model predictability within true economic peers must survive future risk-matched placebo.

**C: structural shifts / calibration, not automatic HMM trading**:
When uncertainty widens or credit/factor stress changes, apply online drift detection (CUSUM/change-point or Bayesian filter) to *calibration and variance* rather than secretly picking a better ranker ex post. Test coverage of VaR/ES during 2022 and 2024–26 separately. Adaptive conformal prediction on nonstationary data carries no unconditional naive exchangeability promise; report conditional coverage. Research foundations: Gibbs & Candès JMLR 2024; Retzlaff et al PMLR 2025; Liu & Luger IJF 2026.

**D: valid chronology and selection control**:
This original149 price history 2017–June2026 has been repeatedly used for research; no more 'best CAGR' tuning here. Freeze F3 and an independently defined A+B candidate on new true PIT historical ETF vintage or on post-lock observed dates; record every prediction before corresponding future Open; proper scoring (CRPS/WIS/pinball, calibration), risk- and factor-matched positive net payoff, and economically matched 60/40. If no new independent signed-alpha information, stop; optimizing an impulse/hysteresis controller cannot manufacture it.

**Strict future gate:** relative rank skill >0.5 even within risk-and-factor matched tickers with grouped 95% CI, quantile coverage credibly near nominal and better proper scores, and net economic edge vs same-cost broker-feasible benchmark not driven by regime picking. Otherwise no alpha claim, no switch strategy, no model promotion. Objective 30%+ net CAGR remains unproven and is not a calibration target.

Saved whole numeric source `research_reset/predict149/factor_neutral/results`, `SHA256_MANIFEST.txt`, and untouched `etf_trader`.
