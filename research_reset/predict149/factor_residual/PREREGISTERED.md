# T149-H — As-of economic-factor decomposition + distributional residual predictor
Frozen 2026-10-19 *before* first T149-H test. Research branch `research/149-factor-residual-distributional-20261019`.

## Objective, no data-mining
The user requests a genuinely new factor-residual distributional model and empirical tests. Prior 149-F3 20.02% backtested CAGR, -29.74% daily-open MaxDD and 50.798% risk/category-matched pairwise concordance (95% CI [49.375%,52.379%]) FAILS evidence for exploitable independent direction; avoid calling a new model profitable from any one historical CAGR. 2017–26 Original149 is **hindsight/survivor selected and heavily mined**, so no fresh statistical holdout exists here.

Hypothesis: the future signed 21-session benchmark-relative log return of an ETF can be decomposed into a time-varying **factor payoff** and an **ETF residual**, where as-of historical exposures are estimated before the decision and the future factor payoff itself must also be predicted, not inserted from realized future factors:

`Y_i(t,t+21) = beta_i(t)^T Z(t,t+21) + residual_i(t,t+21)`

`Z` = 10 prechosen daily traded, historical ETF factor proxies `SPY, QQQ, IWM, VEA, EEM, TLT, HYG, GLD, USO, IEF` minus a 60/40 SPY/AGG benchmark, with no hindsight factor selection. They are **proxy ETFs**, not PIT publication-date underlying holdings or true orthogonal economic factors; future factor returns are used ONLY to label matured training outcomes. Collinearity and latent ETF exposure drift are potential limitations.

At EVERY as-of signal, `beta_i(t)` = 126-prior-completed-daily-Close returns ridge regression, benchmark-relative daily ETF log returns against 10 benchmark-relative daily factor log returns, centered as-of, coefficient penalty **0.005** (fixed). `beta` available for all 149 including factor ETFs and SPY; no source Close later than the signal. Force no nonfinite beta and bounded |beta| < 20. Observe ETF price-relative residual momentum `residual21=res_futureless_21 − beta_i × factor_past_21`, `residual63=...63`; these are as-of features. Parent N4/old F3 features 19+6, ten as-of loadings and two residual momentum = **37 inputs**.

Three distinct H models + frozen F3 and risk-only control, all on same 64 already-studied 2021–26 21-session anchors; 9536 ticker-anchor forecasts:
- **H1_FACTOR_ONLY**: factor premium predictor on next 21 sessions (10 output) via `StandardScaler+Ridge(alpha=60)`, trained only on MATURATED prior monthly factors and 30 lagged as-of factor returns (5,21,63) for each of the ten proxies; as-of `beta × E[Z_fwd]`. Compare factor forecast squared error with simple matured historical factor premium mean, **both measured in test**. A weak factor forecast cannot be portrayed as a regime breakthrough.
- **H2_RESIDUAL_Q**: three LightGBM residual quantile regressions (q10,q50,q90), `LGBMRegressor(n_estimators=80,learning_rate=.04,num_leaves=9,max_depth=4,min_child_samples=100,reg_lambda=25,random_state=20261019,n_jobs=1,verbosity=-1)`. Fit targets `clip(Y_i − beta_i(asof)^T * REALIZED_FORWARD_FACTOR, ±0.20)` for **matured** labels ONLY. Score `(q10+2q50+q90)/4`. This is a *proxy signed return score*, not an unbiased mean or fully calibrated density. No future factor signal fed to the prediction.
- **H3_COMBINED_Q**: H2 residual score + H1 factor forecast score, frozen additive identity factor decomposition, no fitted blend or posthoc parameter search.
- **H4_F3_EXPOSURE_NEUTRAL**: frozen F3 previously predicted score, subtract cross-sectional least-square projection on the ten as-of beta loadings *within each decision date*, with a fixed regression ridge 1.0 to avoid overfitting. As-of neutralization only; no future labels, not independently trained.
- **B0_F3_FROZEN**, **B1_N4_FROZEN**, **B2_VOL63_RANK**: already published comparator scores and exact F3 share-level economics; must reproduce previous F3 20.02% equity metrics with error <1e−10. No change in roster, 10bp each buy/sell, horizon, portfolio evaluation method or cost.

**Train/evaluate chronology**: 112 complete 21-trading-session blocks since 2017. Initial 48 matured blocks then exactly 64 evaluation anchors 2021–26. At time t use only labels with `label_maturity_open < current_signal_previous_close`; quarterly refit on evaluation anchors 0,3,6... using only allowed matured rows. Factor-regression label uses observed next-open return of each factor for the already matured training anchor, NEVER for current or future test row. Do NOT refit frozen parent F3.

**Primary scientific gate** (pre-frozen and stronger than previous):
1. at each test date compare **all as-of same-category and within 0.20 abs log 63day vol** ETF pairs (no future pair selection): mean pairwise signed future-return concordance >0.5 with **95% three-anchor circular bootstrap lower bound >0.5**, AND improve upon frozen F3 with bootstrap lower bound >0.0, and outperform F3 risk-matched rank in EACH 2021–23 and 2024–26;
2. above-old-F3 selected-top5 signed log excess in both eras AND no increase in future-bottom15 selections vs F3;
3. actual shadow costed equity net CAGR > original F3 with daily-open MaxDD no worse, and factor forecast proper MSE better than matured factor-mean null if promoting **H3**.
Failure on ANY implies scientific FAIL, no strategy promotion (even if historical CAGR happens to exceed 30%).

**Secondary**: average cross-sectional Spearman vs future signed excess, top10 future-top15 precision, pinball q10/q90 of *residual* compared to train-matured unconditional residual distribution, selected daily-open ES5, and overfitting diagnostics. Periods 2021–23 and 2024–26 separately. 3-anchor bootstraps resample **dates, not ETF pairs or 149 ticker rows**. Full forecasts, matched-pair diagnostics and time-series financial ledgers archived.

**Science limitations**: these ten risk proxies themselves are 149 survivors not actual economic exposures; other investor-region factors, fees, foreign currency, fund structure, real-time macro credit/news and ETF holdings vintages are missing. No claim of independent PIT/external info here. A positive gate is only a laboratory finding. To prove usable true positive prediction need new **untouched dates or PIT fund roster** and independent as-of external factors, with realistic EUR venue/spread and no meta-selection from repeated tests.

**Risk and software scope**: do not modify production `etf_trader`; archive all source and source hashes in `research_reset/predict149/factor_residual/results/` on this isolated GitHub branch. Negative results MUST be retained. 
