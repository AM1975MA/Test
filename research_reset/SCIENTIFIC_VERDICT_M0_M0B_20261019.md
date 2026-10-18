# 149 ETF — M0 + M0b foundational scientific verdict
19 October 2026 | Branch `research/149-opportunity-physics-m0-20261019`

## Verdict: STOP naive rank-first ETF rotation
This finding is based on two completed deterministic Actions on the EXACT `evidence_v1/data/original149` immutable roster, same source SHA256 `7bccf1b756bf3652280a254c7486fb43f1e805ebb4cdf10731cecc74007292e6`, 112 nonoverlapping 21-session blocks 2017-02-01 through 2026-06-11. The date interval and 149 members differ from previous Top150/EUR60 studies. The original survivor universe is repeatedly mined, not true PIT or untouched holdout.

- Action M0: https://github.com/AM1975MA/Test/actions/runs/39172392472
- Action M0b: https://github.com/AM1975MA/Test/actions/runs/39173085396
- Full sources, freeze documents, metrics, 250 matched random single-ETF paths and 500 five-ETF placebo portfolios are preserved in `research_reset/m0/results` and `research_reset/m0b/results`, with SHA256 manifests. All long-term code in research branch; `etf_trader` production unchanged.
- M0b was deliberately **proposed after seeing M0**, preregistered *before M0b*, and explicitly remains post-selection exploratory.

## Finding 1: exploitable hindsight is not observable skill

M0 per 21-session block picks single maximum ex-post 21d winner among 149. Oracle in this impossible game is >670% annualized CAGR with 0-delay, still ~197% annualized with +10-session recognition delay (the latter *still knows the future*; not a feasible timed execution). The mean hindsight monthly gross advantage over a 60/40 SPY/AGG reference is +0.16469 log return (16.47 log percentage points). 49/112 winning funds in C06 (real assets), 31/112 C02 (US sector/theme) and 27/112 C04 (emerging). Most winners are from high-tail-risk assets, not necessarily positive risk-adjusted opportunities. This oracle is NOT a mathematically exact globally optimal constrained switching DP, and these huge returns are **NOT** a feasible target or evidence of learnability.

Most importantly, as-of past63 full-cross-section ranking vs actual future 21d log returns has mean Spearman **−0.000404**, 95% 3-anchor circular bootstrap CI [−0.05582, +0.05394]. Causal past63 winner CAGR **5.82% / daily-open DD −66.43%**, against SPY buy-and-hold **15.03% / −32.05%** and 60% SPY 40% AGG static buy-hold **11.20% / −23.55%** on the aligned M0 horizon with simplified unequal buy/sell fee conventions. Causal prior21 **7.89% / −63.12%**; Top5-sticky single ETF **2.01% / −72.40%**; previous winning class then best in class **6.27% / −56.89%**. The previous 63d single leader beats only **62.4%** of 250 turnover-AND-category matched single-ETF random paths; null median CAGR 3.67%, 5/95 percentiles -6.07%/+16.82%. No evidence of a profitable general ranking signal. The interval's risk is unacceptable.

## Finding 2: potential rare-tail enrichment collapses against correct financial controls

M0 observed the perfect future 21d winner among previous Top5 in **15/112** historical blocks = **13.39%**, versus 5/149=3.36% naive uniform probability. But that null ignores high volatility and sector risk and makes the result look better than it is.

M0b saved fixed after observing M0. It selected 250 class-only and 250 same-class+nearest-8-as-of-volatility random five-ETF portfolios, *preserving original Top5 membership-retention counts in every 21d block*, with exact fee/cash/share accounting at 10bps one side:
- **Class only** placebo median number of captured future winners **6**, 95th percentile **11**, while actual Top5 **15**. Conditional empirical rank upper-tail fraction 1/(250+1) approximately **0.004**. This is exploratory retrospective conditional randomization, **NOT prospective p-value**.
- **Class AND 63d volatility** placebo captured median **10**, 95th percentile **15**, while original **15**. Empirical upper-tail fraction **~0.088**. The apparent 4x edge over naive random **shrinks substantially** after volatility conditioning; no reliable incremental alpha ranking of rare extremes.
- Top5 equal-weight five-share capital portfolio CAGR **2.07%**, max daily-open DD **−64.79%**.
- Category-and-vol placebo median CAGR **5.38%**, median max daily-open DD **−42.06%**; Top5 beats only **13.6%** of the 250 matched random portfolio CAGR outcomes.
- Category-only placebo median CAGR **5.50%**, median max DD **−36.13%**.
- Historical passive 60/40 ~11.20% CAGR and −23.55% DD, also superior. The cost of Top5 rebalancing is **lower** than the placebo median, so poor net outcome cannot be blamed only on excessive trading fees.
- A future clairvoyant restricted to only the prior Top5 would still CAGR **~148%** ex post; this showcases the enormous (unavailable) value of knowing which of the five will move, not a strategy.

The M0b prespecified GO gate for screening skill fails. This is powerful evidence the objective **cannot be solved by trying another Top5 threshold, sticky switch rule or stochastic controller with the same price ranking**.

## Findings 3: the actual science problem, not just model sophistication

These 149 names are not 149 orthogonal economic bets. USO/UNG, biotech, precious metals, emerging, broad US markets, bond duration etc have fundamentally different forward risk, asymmetric payoff tails and instrument mechanisms. The six inherited labels lump grossly heterogeneous real assets (commodity futures/physical gold/REIT) and duplicate market exposures.

A blind model trained to predict which of 149 has the largest 21-day gross return will often select highest *variance* and convexity even when expected *net risk-adjusted return* is negative. Extreme-return maximum is a large cross-sectional multiple-comparison artifact. Monthly highest-return leader by construction is not the most efficient feasible capital allocation.

Thus the stronger economic learning target is **robust, causal, after-cost EXCESS UTILITY to a replicable benchmark at controlled risk**, not the identity of the largest next monthly upside jump. Use factor ontology and investor-state-dependent action values, without optimizing them on the already mined 2017–26 panel.

### New program: avoid building a model until evidence improves

1. **ETFs/factors ontology first:** reconstruct underlyings/ISIN/inception, exchange, quote currency, exposures to value/growth, real duration, HY spread, oil term-structure roll, FX, region and beta, leverage and commodity futures vs physical. Collapse duplicate factor bets. Build as-of factor representation and actual investability for EUR holder. Current 149 stays reference dataset, not retrospective 'tradable ETF universe'. At each date add only funds listed *at that time*, include delisted funds.

2. **Prequential opportunity tests not ranking targets:** estimate economically meaningful, sign- and magnitude-asymmetric 5/21/63 day conditional benchmark-excess distribution for same-factor peers; explicitly model long-left-tail vs short-lived right-tail winner. Conditional performance of hard 'no trade' reference is an indispensable null. Learn only if calibrated decision utility exceeds baseline in fresh precommitted future data.

3. **Risk first, but don't mistake it for alpha:** original149 six-class diversification reduced Top2 deep DD; EWMA variance marginally improves risk weights. Both remained inferior to historical benchmark SPY/AGG 60/40 on matched risk/return evidence. For downside models require calibration of actual portfolio expected shortfall / drawdown hazard, not only variance QLIKE or fabricated option-PIT macro. Separate systemic vs idiosyncratic factor stress; note no filter can forecast an unprecedented overnight gap.

4. **Adaptive crisis response rather than magical turning-point foreknowledge:** model progressive widening/narrowing of spreads, loss of trend persistence and credit/liquidity shocks from timestamped independent sources; evaluate actual rapid reaction vs unnecessary transactions. Price-only HMM and Student-t crashes failed original149 tests; do not retune their thresholds.

5. **Stochastic impulse control last:** only if an as-of probability of real net action value is calibrated and stable, solve hold/rotate/reduce with realistic transaction costs and liquidity under risk budget. Financial hysteresis follows action-value gap and cost, not Top5 membership.

6. **Unbiased evaluation:** no more claims of 'independent holdout' from 149/150/69/EUR60 past data; prospective immutable new data and as-of vintage, benchmark consistent with European accessibility and investor FX/cash, multiplicity control and risk-adjusted significance. True GO if and only if a risk/broker matched solution improves frontier of terminal utility and crisis drawdown across *unseen* data.

**No alpha discovery from these two experiments.** The 'leap' here is quantitatively falsifying the old *information objective*, not pretending we found a high-CAGR winner. These limits leave open the existence of predictability from richer as-of external data and different objectives; they do not prove efficient-market impossibility.

## Follow-up question to research, not to the user
Can a trade-feasible, real-time factor-causal estimator distinguish the quality and duration of a relative return premium **after risk and transaction costs** rather than selecting the largest volatility outlier? This is M1. Work is blocked on a genuine PIT factor/ETF lifecycle source and an untouched evaluation interval; repeated retraining on this 149 will not cure the methodological defect.
