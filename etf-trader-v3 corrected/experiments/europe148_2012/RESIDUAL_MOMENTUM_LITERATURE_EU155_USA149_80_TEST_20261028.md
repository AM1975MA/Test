# Residual momentum: academic papers, fixed B0 benchmarks, 80 paired economic tests

**28 ottobre 2026 — experiment completed, negative on the user's objective. No production update.** Source code, 80×2076 EUR daily NAV, original ETF data and analyses are available in the conversation archive `EU_US_RESIDUAL_MOMENTUM_PAPERS_80_TEST_20261028.zip`.

## Paper basis
- Blitz, Huij, Martens (2011) *Residual Momentum*, Journal of Empirical Finance, https://doi.org/10.1016/j.jempfin.2011.01.003: residual stock momentum conditioned on Fama–French factors; our ETF single-market-beta implementation is NOT an exact replication.
- Moskowitz, Ooi, Pedersen (2012) *Time Series Momentum*, JFE, https://doi.org/10.1016/j.jfineco.2011.11.003: raw momentum benchmark.
- Daniel, Moskowitz (2016) *Momentum Crashes*, JFE, https://doi.org/10.1016/j.jfineco.2015.12.002: downside and risk.
- Barroso, Santa-Clara (2015) *Momentum Has Its Moments*, JFE, https://doi.org/10.1016/j.jfineco.2014.11.010: volatility conditioning.
- Moreira, Muir (2017) *Volatility-Managed Portfolios*, Journal of Finance, https://doi.org/10.1111/jofi.12513.
- Gu, Kelly, Xiu (2020) *Empirical Asset Pricing via Machine Learning*, RFS, https://doi.org/10.1093/rfs/hhaa009: walk-forward, ML regularization, benchmark discipline.
- Hansen, Lunde, Nason (2011) *Model Confidence Set*, Econometrica, https://doi.org/10.3982/ECTA5771: caution about repeated backtest specification search.

## Fixed experimental design (before viewing outcomes)
101 common monthly 2018–26 signals; 2076 shared EU/US trading days in account EUR, exact historical next Open, no invented prices, 10bp fee per traded side. Fully frozen 148 original European legal ISINs, EU148 with 6 issuer-verified same-ISIN Yahoo venue repairs, EU155 complete (those six + seven country index UCITS), USA149 original. Selection Top3 and Top5, BASE and LIQ50 (as-of 90% volume positive and median ADV>=50k EUR for last 63 sessions). Total **4 cohorts × 2 eligibility × 2 top-N × 5 fixed strategies = 80**, all retained and disclosed.

- Momentum252: trailing 252 sessions simple return.
- Momentum12−1: log-return 252 sessions *skipping most recent 21*.
- Main residual: prior 252−21-day ETF log-return minus beta×prior index log-return, beta OLS from last 126 days known at signal, index EU `DE0002635307` EXSA.DE, USA SPY.
- Residual/SNR: divide by 126-day residual-volatility SD×sqrt(231).
- Fixed 50/50 rank blend raw252+residual12−1.

Only past observations enter signals; future 21d outcomes used in diagnostics after portfolio construction. **The stock-market-factor version of residual momentum is deliberately a simplified ETF adaptation, not the stock multi-factor paper's model.**

## Actual TOP5, trailing LIQ50 (CAGR % EUR)

| Rank rule | EU148 base | EU148 repaired | EU155 complete | USA149 |
|---|---:|---:|---:|---:|
| MOM252 | **8.22** | **8.02** | **8.64** | **21.23** |
| MOM12−1 | 6.07 | 5.93 | 6.03 | 13.57 |
| RESID12−1 | 7.37 | 7.58 | 7.68 | 11.74 |
| RESID/SNR | 6.53 | 6.42 | 6.61 | 1.56 |
| MOM/RESID half ranks | 7.32 | 7.35 | 7.67 | 15.61 |

Drawdown EU155: MOM252 **-35.57%**, RESID -29.10%, RESID/SNR -19.19%. The lower drawdown is accompanied by worse CAGR. Drawdown USA: MOM252 -37.28%, RESID -39.88%.

Average monthly cross-sectional Spearman predictive IC for MOM252 vs RESID, n=101 months: EU148 +0.03420 vs +0.02903; EU155 +0.03720 vs +0.03236; USA149 +0.00261 vs −0.01755. **No predictive IC improvement.** Paired 6-month block bootstrap 6000 replications: EU155 RESID−MOM252 ΔIC −0.0048, nominal 95%CI [-0.0606,+0.0455]. EU155 economic annualized paired log return Δ -0.89pp, nominal 95%CI [-4.34,+3.09]pp; USA Δ -8.14pp, [-20.02,+2.16]pp. Intervals nominal, **NOT multiple-comparison corrected** and historical dates previously inspected.

Subperiod split EU155 Top5: 2018–21 MOM252 +0.98%, RESID +4.35%; 2022–26 MOM252 +15.78%, RESID +10.67%. USA same: MOM252 +8.09/+34.50%; RESID +3.05/+20.16%. No stable EU advantage and clear failure to preserve USA CAGR.

**Reconciliation:** EU148 original MOM252 Top5 LIQ50 +8.22% and USA149 +21.23% match prior B0; EU155 +8.64% versus earlier EU155 +8.79% due to common full eligibility requirement of a computable rolling beta and residual-vol score for all arms. No unavailable BUY quotes and no held-position future price used in selection. A subset of EU trades have Yahoo zero-reported volume despite the filter and venue liquidity is not verified with an independent quote feed.

## Decision

**Do not promote residual momentum or its risk-scaled score.** The European predictive and economic benefit is not demonstrated, and the US benchmark loses 9.49 CAGR points in the main residual variant. Do not backfit beta window or mixing percentages after looking at this history.

Candidate for a genuinely new independent research protocol: **within-asset-class factor modeling and category-specific conditional excess return**, rather than projecting equity index beta onto European bond/sector/country ETFs together; must be tuned in earlier vintages with future held-out signals, issuer/venue source audit, bid/ask realism and factor-matched risk benchmark. The main production V2 and original canonical 500 baskets remain untouched.

Full reproducible source and data: ChatGPT conversation `EU_US_RESIDUAL_MOMENTUM_PAPERS_80_TEST_20261028.zip`; includes `residual_momentum_experiment.py`, `postprocess.py`, complete original EU, repaired EU155 and US market series, selection/NAV/IC/bootstrap manifests.
