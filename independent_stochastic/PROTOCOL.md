# INDEPENDENT STOCHASTIC / ERGODIC ETF EXPERIMENT
Frozen: 2026-10-18, pre-results. New branch: `research/independent-stochastic-ergodic-20261018`.

## Explicit correction of previous direction
Old Return-Rank XGBoost and its Hybrid/Titanium predictions are **not inputs** of any novel strategy in this experiment. They are frozen comparison metrics ONLY (CAGR 9.9780% on 60 EUR historical ETF cohort and H7 13.4231%, on distinct original code). Existing prior 113-month decisions/predictions are NOT used for research signal formation, models or online payoff. This experiment directly consumes daily Close as-of signal date, and next month Open only for post-decision accounting.

We study stochastic *log wealth*, diversity, regime-aware uncertainty and online *expert game* rather than optimizing the next winner. No fitted supervised labels, no XGBoost/LightGBM, no old signal scores, no hyperparameter search.

## Market model and structure
Economic problem: multiplicative, nonergodic wealth growth under partial information with time-varying volatility and correlated shocks, costly trading and adaptive competing policies.
- Causal as-of daily positive close series; trailing 252 sessions required, current active names with recent closes. Historical cohort membership still hindsight-selected, not PIT/delist inclusive.
- Each expert is a different, fully specified map from observed historical prices to long-only monthly weights.
- Two innovations: A) **Monte Carlo posterior-predictive log utility**: 384 seeded multivariate Student-t(5) monthly innovations with 252-day shrinkage covariance; choose among prespecified defensible diversified candidate portfolios via lower-decile log growth penalized by turnover, never use realized outcomes for winner. B) **online multiplicative weights across genuinely independent experts**: only last completed month net returns update expertise; formal sequential competition, no ex-post parameter fit. This is not a complete mathematical Cover universal portfolio or exact Bayesian posterior; it is a transparent, finite expert controller.
- Risk dimension: risk-free asset = non-remunerated 0% cash, for comparability; not an investable validated EUR product.

## Frozen standalone experiment arms
- `D0_BROAD_LOWVOL`: historical inverse-vol distribution among 10 lowest 126-day-volatility ETFs (broad, diverse baseline). Equal candidate cap 30%, risk weights capped at 20%, exact normalization, missing histories excluded. No directional model.
- `D1_ROBUST_STATE`: independent approximate Student-t robust latent-drift filter, five highest *posterior mean / total predictive volatility*, inverse-vol and 25%-max weight. Diagnostic of standalone state-space; earlier independent Kalman experiment was disappointing and that prior information is already known.
- `D2_LOG_GROWTH`: empirical robust log growth from clipped trailing 252 daily log returns, with 126-day emphasis; variance and shrinkage penalize uncertain overbetting, select 8 highest conservative posterior score, inverse-risk prior weights. Motivated by long-run geometric growth, not return-label fitting.
- `D3_CONTRARIAN`: short-term mean-reversion using preceding 21d relative to 126d log drift, volatility-scaled, long-only 8, volatility weights with 20%-max. May be weak; deliberately diversified mechanism.
- `D4_ENTROPIC_CORRELATION`: covariance shrinkage and greedy residual-dependence selection among 12 broad growth-qualified candidates, 8 holdings, limited maximum pair correlation; choose via independent as-of covariance only. Avoid use of hindsight outcomes.
- `D5_STUDENT_T_SCENARIO`: choose a *single whole portfolio* from D0–D4 each month by simulated lower-tail log-utility minus 0.25x 12m return std and trading-cost penalty using shared correlated t(5) scenarios. Use same prior observed market parameters across all candidates. No reranking by old LM, no retrospective optimization.
- `D6_HEDGE_GAME`: convex weight-mix of D0–D4 independent expert monthly holdings, with expert weight updates **after** previous month's next-open-to-next-open PnL is fully realized. Fixed log-wealth learning rate 5, exponential forgetting factor 0.97, expert-weight cap 45%, cost-aware net expert shadow payoffs; no future data. Portfolio capped at 20% per ETF and has no leverage.
- `D7_HEDGE_REGIME`: D6 plus frozen regime gate (same 21/126 volatility and prior index-under-200 mean condition); equity cut to 50% during gate, 0% yield cash. Tests risk-control orthogonally; still no old selector.

Market breadth proxy uses only the current EUR60 hindsight cohort and observed returns; never claim it's a real Europe market index. Entropic weights are *regularization / diversification*, not literal thermodynamics. Monte Carlo means model-implied projections, not realized forecasts.

## Costs, execution, controls
Same 113 monthly signal-date calendar from oracle artifact 39084898663, final historical price snapshot, next common monthly entry and exit open. Costs 10bp one-way based on half-L1 portfolio weight change; ledger cost-accounting includes residual cash weight changes (first month mimics old benchmark convention). If selected asset unavailable at entry/exit, block test; do not silently select using future existence. All expert-only policies scored under identical calendar. Selection and online weighting must be invariant to future Close mutation after signal date; no smoothing/relabel.

Compare against frozen old H0, H5 and H7, BUT note their as-of eligibility could differ; a like-for-like reproducible local baseline is equal weighting of 10 least-volatile eligible names. Check monthly missing/tradability and reject lookahead attempts.

Report full metrics and split-period returns, model-implied scenario score vs realized subsequent outcomes, turnover, max drawdown sampled monthly, drawdown recovery, tail ES5 monthly, concentration and number of positions, return paired 12-month block CIs vs D0. Compare an equal-weight mixture of all five experts as a fixed model-uncertainty baseline, `D8_UNIFORM_EXPERTS`, to prevent attributing gains to online game weights when simple averaging suffices. Simulated-score optimization is single-pass and precommitted; no after-result tuning.

**A hypothesis failure is a scientific result. No guarantee a novel strategy beats old H7; old market 2017–2026 panel is contaminated by repeated exploration.** Do not change strategies because first results are disappointing. Further design can address identified causal flaws but performance-driven refinement needs new untouched data.

## Required output and scientific gates
- Source code + workflow + SHA source manifest, test proving no future close influences as-of weights, 113-month full ledger and source hashes in Git. Use failures as diagnostics.
- Proper feasibility: source file 60 names historical survivors; verify point-in-time unavailability/dead and fund/ISIN/currency as independent step before prospective recommendations. External index/B&H controls require validated underlying EUR venue data.
- Explicitly estimate how many months expose risky ETF weight <1 for D7; disclose risk proxy.
- No promotion of historical winner: require forward PIT unseen period, other Europe funds, realistic EUR cash, spreads, UK/FX distinctions, covariance regime stress.
- Theoretical anchors: Fernholz (2002) *Stochastic Portfolio Theory*; Cover (1991) *Universal Portfolios*; Hazan & Kale (2015) online portfolio regret; Kelly (1956) log growth; Hamilton (1989) changing states; robust Student-t modeling. These inspire approximations, they do NOT grant finite sample positive alpha.
