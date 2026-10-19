# T149-M final scientific decision — 19 October 2026

**GitHub Action:** https://github.com/AM1975MA/Test/actions/runs/39291773731 — success, including Python tests, original 1345 daily next-Open equity parity, scientific conditions and SHA256 results. All sources and findings stored only on research branch research/149-selected-nominal-tail-20261019. Production etf_trader untouched.

## Primary risk forecasting result
Original 149 frozen US ETF survivor panel, original F3/H1 five-plus-five holdings (merged duplicates), 64 nonoverlapping 21-session 2021–2026 blocks, strictly causal one-block-embargo walk-forward; 43 scored portfolio periods with 408 distinct selected-ETF evaluations. Target individual 21-session next-Open gross nominal loss < -5%, NOT benchmark-relative underperformance as in K1. Bootstrap resamples three consecutive entire dates; ticker observations are clustered, not independent.

- Selected-name M_TAIL 8-factor logistic **Brier improvement vs matured selected-name historical frequency = -0.01503599**, 95% block CI **[-0.02405428,-0.00610722]**. This is a statistically meaningful **deterioration**, not skill.
- Selected-name volatility-only logistic **Brier improvement = -0.00756322**, CI **[-0.01663995,+0.00249654]**. No statistically established skill.
- Basket 21-session gross loss5 **3 events in 43** anchors. Portfolio-head Brier **0.06915425 vs prior 0.06915425**, improvement zero. Diagonally shrunk past-covariance Gaussian comparator Brier **0.06708689**.
- Basket max adverse opening mark from entry <-8% **2 events in 43** anchors. Model-head Brier **0.15506727**, prior **0.06651172**, Gaussian **0.05680559**; model/prior gain **-0.08855555**, CI **[-0.12155099,-0.04324901]**. Predicted mean occurrence 37.52% versus observed 4.65% indicates poor regime transfer / calibration, not an investable risk forecast.

## Exact economic replay with bilateral 10 bp trade costs
Full Feb 2021–June 2026, real merged underlying ETF shares, 1345 common Opens, 64 rebalances:
| Strategy | Net CAGR | Daily maxDD | Daily annualized Sharpe | Daily ES5 |
|---|---:|---:|---:|---:|
| Original F3/H1 50:50 | 23.2151% | -24.8442% | 0.8869 | -3.3023% |
| M_TAIL_WITHIN | 23.4554% | -24.9095% | 0.9057 | -3.2568% |
| VOL_ONLY_WITHIN | 23.4746% | -24.5523% | 0.9109 | -3.2355% |

M_TAIL mean monthly net log improvement vs static +0.00016281, 95% three-anchor CI **[-0.00034134,+0.00064394]** includes zero. Early mean +0.00031052 but late mean -0.00001547; drawdown is worse. VOL_ONLY mean monthly +0.00017581, CI **[-0.00017228,+0.00052987]**; not significant. Do not select either model based on retrospective CAGR alone.

**Precommitted three-part science gate FAIL / NO DEPLOYMENT.** Frozen original baseline remains a historical reference only, not a validated live strategy.

## Substantive consequence
Consecutive model expansions have not beaten well-chosen simple volatility baselines in conditional held-name absolute downside forecasting. Crucial scientific constraint is the scarcity of independent portfolio tail events and the reuse of a historical survivor cohort after multiple prior experiments, NOT a lack of candidate algorithm sophistication. An elaborate classifier cannot fabricate missing crisis observations.

For the next independently designed **predictive** study, avoid tuning binary tail cutoffs (5%, 8%) on this cohort. Consider forecast distributions/quantiles of **continuous** 21-session ETF absolute returns, downside semi-volatility and realized basket covariance/conditional expected shortfall; compare to pre-specified shrinkage/historical controls and test on genuinely new point-in-time chronology. Condition future risk on factor exposures and correlated clusters, not independent per-ETF event counts. Require positive proper-score/cost gates on new not-mined holdouts before allocator changes.

Mandatory caveats: original US ETF survivor list is not European-eligible/PIT; live bid-ask, trading availability, forex and taxes untested. Dates, membership, strategy construction and labels have been reused in earlier research and are not an independent holdout.
