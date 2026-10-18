# Verdict — Independent stochastic ETF research / 18 October 2026

Status: `COMPLETED_EXPLORATORY`, NOT `PROSPECTIVELY_VALIDATED`, NOT `READY_TO_TRADE`.

## Why this experiment was genuinely different
User rejected further optimization of historical Return-Rank / Hybrid ML ranking. A separate branch `research/independent-stochastic-ergodic-20261018` contains nine end-to-end portfolio selectors/controllers that never read old ML scores, perform no XGBoost/LightGBM fitting, and select using only trailing daily closes. Subsequently extracted every numerical state-space function into a pure physics module and removed *all legacy machine-learning imports* from the strategy engine. A later Action `39120438390` reproduced the original results numerically without the old dependencies.

Scientific architecture:
1. Uncertainty about latent log drift: approximately robust Student-t(5) two-speed state-space filter, Bayesian evidence weighting, no return-label supervision.
2. Ergodicity/time-average welfare: long-run geometric log growth under multiplicative compounding, lower-bound conservative growth and diversification.
3. Random shocks: 384 monthly correlated Student-t scenarios from as-of shrunk daily covariance (exploratory correlated heavy-tail noise, no future).
4. Information/entropy: greedy correlation decorrelation as partial portfolio entropy proxy, not a physical thermodynamic measurement.
5. Game theory: exponential/multiplicative expert weights updated only when previous economic PnL is observable at the current signal close. IMPORTANT: the immediately preceding monthly exit at next opening is usually after the current signal, so the completed-shadow update is lagged by a month; exactly **111** matured updates across 113 signals.
6. Second-stage probabilistic control: filtered two-state Markov volatility HMM (no future smoothing) and model-scenario expected-shortfall equity budget.

## First independently executed nine-arm run
Definitive pure price-only rerun: [GitHub Actions 39120438390](https://github.com/AM1975MA/Test/actions/runs/39120438390), previous implementation corroboration: [39119879600](https://github.com/AM1975MA/Test/actions/runs/39119879600).

| Policy | CAGR 2017-26 | Monthly sampled MaxDD | Sharpe annualized | Interpretive note |
|---|---: | ---: | ---: | --- |
| D0 10 least-volatile ETF inverse-vol | 1.48% | -18.90% | 0.244 | low-return diversification benchmark |
| **D1 5 robust Student-t state-filtered ETF** | **9.19%** | **-20.43%** | **0.748** | strongest standalone independent Sharpe |
| D2 conservative geometric growth | 3.20% | -38.76% | 0.222 | growth estimation too uncertain |
| D3 contrarian | 3.36% | -26.19% | 0.233 | weak |
| D4 correlation-diversity | 4.36% | -27.86% | 0.330 | entropy not alpha by itself |
| D5 correlated Student-t scenario optimizer | 3.49% | -36.47% | 0.246 | scenario distribution not accurate enough to select expert |
| D6 causally matured Hedge online experts | 5.30% | -20.90% | 0.482 | adaptation diluted strong expert |
| D7 Hedge + common-market regime filter | 5.67% | -17.68% | 0.636 | defensive, weak CAGR |
| D8 uniform expert aggregation | 4.58% | -21.01% | 0.422 | game adaptation added ~0.72pp over uniform average, exploratory |

All above have 113 months, as-of EUR60 survivor cohort, monthly common opening execution with nominal 10bp one-way costs; sampled monthly maxDD misses within-month excursions, and no liquidity/slippage or validated EUR cash carry.

**Critical weakness:** D1 CAGR by evaluated historical slice was **0.25%** (2017–20), **9.63%** (2021–23), **25.14%** (2024–26); an apparent overall robust Sharpe hides extreme timing dependence. D1 beats D0 by bootstrap but D0 has very low economic return and is not an alpha standard. Older R_H fixed50/50 = **9.978% CAGR**, prior H7 research = **13.423% CAGR**, from the *same mineable historical cohort*. Novel strategy does **not** outperform H7 in CAGR.

## Second-stage predeclared after seeing D1 success (post-selection exploratory)
[Protocol](../independent_stochastic/H10_BAYESIAN_RISK_PROTOCOL.md) and [Action 39120298645](https://github.com/AM1975MA/Test/actions/runs/39120298645).
Frozen D1 securities and weights every month: altered **risk exposure only**, no reranking, no fit to realized labels.
| Risk envelope | CAGR | Monthly MaxDD | Sharpe | Defensive months |
|---|---:|---:|---:|---:|
| C0 original D1 100% | 9.186% | -20.433% | 0.748 | 0 |
| C1 static 90% equity | 8.301% | -18.508% | 0.754 | 113 |
| **C2 filtered 2-state volatility HMM** | **9.291%** | **-19.114%** | **0.780** | **6** |
| C3 Student-t estimated 10% ES risk budget | 9.182% | -20.433% | 0.749 | 6 |
| C4 HMM + Student-t ES | 9.288% | -19.114% | 0.781 | 6 HMM plus rare fractional reductions |

**C2 vs D1** paired monthly log return difference +0.00008036; 95% retrospective 12m-block bootstrap CI **[-0.000764,+0.001115]**, crosses zero. After >10 research candidate choices and old-panel mining, cannot infer statistical edge. C3 adds negligible useful risk prediction at frozen 10% loss budget; do NOT optimize tail budget using old evaluation returns. C4 adds almost nothing vs C2.

## A precise falsifiable thesis rather than a guaranteed winner
An **independent Student-t latent-drift selector**, five ETFs with diversity and capped position weights, paired with an **as-of two-state market volatility observer**, looks like a reasonable *risk-managed experiment*. This is `D1+C2`. It is distinguishable from ML ranker H7: its score comes from a stochastic filtering and tail-robust latent mean, and its trading decisions depend on only price history.

But historical CAGR of D1+C2 ~9.29% remains below H7 ~13.42%. It is NOT shown to have superior return expectation, and its gains cluster late in sample. No use of Kelly, Monte Carlo, thermodynamic metaphors or online games confers predictive alpha without an identifiable effect in untouched data. In this run, mixing experts reduced performance and Student-t simulated optimization selected wrong experts often.

### Expert/scientific conclusion
1. Preserve previous H7 as an independent **reference** for risk/return, not as a signal inside the new engine.
2. Freeze `D1+C2` as the independent **stochastic challenge model**, with no post-hoc threshold/ranking adjustment. Keep D1 alone and static 90% as mandatory controls. Avoid adding entropic gate or post-selected game layers until independent incremental proper-score validation.
3. Do not promote anything to actual trading yet; the cohort was selected knowing 2026 historical survivorship. If implementing a live engine, stop using historical snapshot universe and instead build verified PIT ISIN/currency/domicile/underlying exposure, including delisted funds.
4. Next decisive research: genuinely different cross-sectional cohort or new unseen months beyond the source 2026-07 snapshot; lock code now; forward paper-trading record with realistic EUR cash and cost; risk-specific diagnostic calibration proper log score; re-evaluate when statistical sample size justifies.
5. Compare matched capital risk/daily DD, not merely monthly MaxDD or favorable CAGR periods; record delayed disclosure and failure cases.
6. All calculations and full monthly ledger should be committed as SHA256-hashed permanent input-output research receipts; do not rely on Actions artifact expiry.

## Results / source locations
- `independent_stochastic/physics.py`: standalone numerical filters.
- `independent_stochastic/experts.py`: eight independent policy maps and Student-t scenario code.
- `independent_stochastic/run.py`: causal matured-payoff online ensemble and fixed next-open open ledger.
- `independent_stochastic/risk_stage2.py`: HMM and Student-t tail-control risk overlay.
- `independent_stochastic/PROTOCOL.md`, `independent_stochastic/H10_BAYESIAN_RISK_PROTOCOL.md`: hypotheses frozen before the respective runs.
- `independent_stochastic/results/RESULT_39119879600.json` and `research_receipts/stochastic_h10_results_39120298645.json`: durable final metrics.
- `research_receipts/stochastic_archive/`: SHA256 complete monthly ledger and states after archive Action.
