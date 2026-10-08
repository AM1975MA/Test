# L2-H — fixed smooth nonlinear ranker with explicit feature-consistency penalty

**Frozen on 2026-10-08 before fitting either new candidate.** Only repository `AM1975MA/Test`; `Etf_trader` unchanged. All Original149 history is heavily explored: diagnostic evidence, never a production promotion.

## Objective and fixed alternatives

Can an **explicit, convex, perturbation-consistency penalty** stabilize nonlinear ranking without eliminating XGB's ability to find unusually good ETF candidates? We construct two matched nonlinear random Fourier ridge rankers. All preprocessing, missingness and Fourier features are identical. They differ **only** by one positive semidefinite penalty built from perturbed causal training features:

1. `FOURIER_DIRECT`: ridge solution without consistency, `gamma=1/250, random Fourier 128 components, random_state=47`, append 125 standard-scaled original features divided by sqrt(125), intercept; L2 penalty alpha=20 on weights, intercept unpenalized.
2. `FOURIER_CONSISTENCY`: same as control but add `lambda=300 * mean_{j=1..3} ||prediction(Xtrain+epsilon_j)-prediction(Xtrain)||²`, with `epsilon_j ~ Gaussian(0,0.05²)` in **train-standardized feature** units. Use three fixed random generators based on vintage index, fit cutoff and seed 89. Only training X is perturbed, targets and future data never enter penalty. The resulting quadratic Tikhonov problem has a unique closed-form solution (given ridge regularizer). No hyperparameter adjustment from results.

`Stable abstention overlay` is **NOT another fitted model**: for each signal, use the consistency model's selected ETF only if its *within-date predicted score* exceeds its score for Ridge's best ETF by at least `0.05` absolute rank-target points; otherwise choose Ridge. This uses same-date **pre-trade predictions only**, no realized future performance nor cross-vintage means. The threshold is a fixed hypothesis, never varied.

Important: perturbation size 0.05 standardized units is a *stress regularizer*, not a calibrated estimate of real Yahoo errors (which are much smaller); do not misrepresent this as exact Yahoo-noise reconstruction. The penalty measures local smoothness of a fixed learner; it may not suppress retraining-vintage differences. Only empirical held-input diagnostics decide that.

## Protocol

- 149 Original149 ETFs, three frozen Yahoo vintage repeats from GitHub Actions raw artifact `11272972639`. Exact 125 Compact21 features from the earlier source-only L2-C reproduction, no ticker identity, no label-dependent eligibility.
- Train annual expanding Jan1 2019–2026, `signal_date < cutoff` **and** `exit_date_21 < cutoff`; target 21 trading session realized continuous within-date percentile rank. Train simple imputer median then StandardScaler **only on past rows**. At least 30 finite original features, same cohort for both learners.
- Infer on all dates in fit year, evaluate **2019-01 through 2026-06** whose 21-session returns matured by 2026-07-31; 90 dates. Native vintage and **fixed common Repeat2 inference input** predictions by independently fitted learner, with per-ETF score files retained.
- Controls: frozen original XGBoost and Ridge native predictions from L2-D and/or L2-G; never retrain/tune.
- Outcome metrics: per-date equal weight after averaging 3 vintages, NDCG@5, rank IC, Top5 winner hit, exact Top1 hit, realized 21-session net return, return regret, annual and high-vol vs low-vol diagnostics (regime classification from *past* SPY vol only). Three acquisitions are NOT three market tests.
- Robustness: native and fixed-Repeat2 common-input Top1 agreement, Top5 overlap, percentile-rank MAD for 3 vintage pairs. Trade: 89 contiguous monthly periods matched 2019-02 to 2026-07 using exact no-phantom terminal switching cost 0.1% per side; monthly sampled DD caveat.
- Statistical uncertainty: 10k paired 3-month moving block bootstrap on date-averaged differences of consistency vs direct, consistency vs Ridge and XGB for Top5, selected return, NDCG; unadjusted exploratory descriptive intervals.
- Success for diagnostic continuation: ALL three held-input vintage pairs Top1 agreement>=90%; native rank-MAD<0.01; realized Top5 hit >=15%; realized selected next-21 return >= Ridge mean on matched dates. Overlay gets separately evaluated, but a stable anchor alone does not establish the new ranker fixed the problem. If fails, **report failure, no threshold adjustments**.

## Independent QA lenses

- ML: exact convex solver parity, feature standardization trained only on strictly mature rows; perturbation penalty PSD and activated; no label leakage.
- Econophysics: clustered volatility regime, heavy-tailed outcome and sensitivity to data vintages; regime is diagnostic not fitted switch.
- Statistics: paired monthly cluster and repeated-vintage dependence, confidence bands and significance caveats.
- Execution/risk: fee only for real trades at next OPEN, monthly DD and no canonical Hybrid24 claims.
- Engineering: source hashes, cutoffs, date/ETF keys, independent recomputation, baseline reconciliation.

No candidate can be adopted from this historically overused development sample.
