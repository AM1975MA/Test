# Research decision — 2026-10-18: scientific agent team, three executed experiments

**Classification:** `PROMISING_RESEARCH_ONLY` / `NOT_PROSPECTIVELY_VALIDATED`. Historical results are *not* expected future CAGR or personalized investment advice.

## What was actually executed
1. Multi-role deterministic Python coordinator with synthetic as-of test and frozen historical-parity gate: [run 39089621741](https://github.com/AM1975MA/Test/actions/runs/39089621741). Source: `scientific_lab/run.py`, `models.py`, `ledger.py`, charter `scientific_lab/AGENTS_AND_PROTOCOL.md`, receipt `research_receipts/eur60_scientific_run_39089621741.json`.
2. Independently coded H5 validation including 0/10/50/100bp one-way fee scenarios, 60 frozen-score jitter trials, calendar-year attribution: [run 39089923977](https://github.com/AM1975MA/Test/actions/runs/39089923977), `adversarial_tests/hysteresis_stress.py`, `research_receipts/hysteresis_adversarial_run_39089923977.json`.
3. Explicitly post-selected risk interaction H7 vs permanent 90% equity control: [run 39090132221](https://github.com/AM1975MA/Test/actions/runs/39090132221), `interaction_tests/HYPOTHESIS_H7.md` committed before execution, `interaction_tests/h7.py`, `research_receipts/h7_interaction_run_39090132221.json`.

The eight `.github/agents/*.agent.md` profiles are **configurations for compatible coding-agent environments**, not a claim that eight independent remote LLM agents were instantiated during these runs. Their corresponding Python science/audit functions **were executed**; GitHub Actions runs prove this. The profiles are on this isolated research branch; do not assume GitHub Copilot lists them until appropriately selected or merged into a supported branch, and do not merge them as part of this study.

## Main quantitative evidence — exact 113-month 2017–2026 EUR60 replay

| Arm | Historic CAGR | Monthly MaxDD | Monthly Sharpe annualized | Annual turnover | Cash months |
| --- | ---: | ---: | ---: | ---: | ---: |
| H0 frozen Return-Rank top2 50/50 | 9.9780% | -26.6441% | 0.4906 | 8.496 | 0 |
| H1 same H0 top2, 63d inverse vol | 9.7225% | -26.1281% | 0.4835 | 8.823 | 0 |
| H2 same H0 top2, Kalman uncertainty weights | 9.2527% | -26.9127% | 0.4569 | 8.797 | 0 |
| H3 same H0 top2, state-driven 50% equity / 50% 0%-yield cash | 9.4147% | -20.7335% | 0.5175 | 8.363 | 16 |
| H4 same H0 top2, shrunk covariance eigen-entropy gate | 5.8653% | -20.7335% | 0.3508 | 8.416 | 45 |
| **H5 prior top-5 hysteresis, top2 equal weight** | **14.0888%** | -27.9257% | 0.6913 | **6.478** | 0 |
| H6 same H0 top2, Kalman weights + H3 gate | 8.6010% | -21.0828% | 0.4739 | 8.626 | 16 |
| **H7 H5 hysteresis plus unchanged H3 gate** | **13.4231%** | **-22.1183%** | **0.7452** | **6.611** | 16 |
| H8 H5 fixed 90% equity / 10% cash | 12.7840% | -25.2750% | 0.7003 | 5.830 | 113 |

**H7 vs H5:** CAGR sacrifices ~0.666 pp/year, while monthly DD improves by ~5.81 pp and Sharpe increases by ~0.054. **H7 vs H0:** historical CAGR +3.445 pp/year; monthly MaxDD ~4.53 pp less negative; Sharpe +0.255. These metrics are descriptive, based on one highly mined retrospectively filtered sample, not statistically demonstrated live improvement.

**Counterexamples to tempting stories:**
- H2 Kalman allocation **failed** vs H0 and even simpler historic inverse vol. The descriptive Spearman correlation with realized next-month absolute returns on 226 selected asset-months is ~0.2315 for Kalman predictive uncertainty vs ~0.2921 for lagged vol. Do **not** advertise Bayesian sophistication as improved risk estimation.
- H4 entropy defensive gate generated ~5.87% CAGR because it cut equity exposure in 45 months, and did not establish an incremental alpha signal. Keep eigen-entropy as a diagnostic rather than an always-active filter.
- H5's lower turnover is not sufficient to explain most of its return benefit: even **zero fee** leaves 14.83% vs 10.92% CAGR. Under 10bp one-way fees, 14.09% vs 9.98%; at 50bp, 11.16% vs 6.29%; at 100bp, 7.60% vs 1.85%. These are sensitivity simulations, not measured broker spreads.
- Across 60 small Gaussian frozen score-noise trials (30 at 0.1% and 30 at 1% of each month's score cross-sectional standard deviation), the H5 selection rule beat the correspondingly perturbed H0 **in all trials**; this does NOT cover full price-vintage revisions, market disruption or delistings.
- **Dependence on a few winners:** three monthly positive differences account for ~0.274 of ~0.346 total cumulative monthly log-return gain (roughly 79%). H5 outperformed H0 in 26 months, underperformed in 19, and was nearly identical in 68. The paired H5-H0 mean monthly log-return difference is +0.003058, circular 12-month-block exploratory bootstrap CI **[-0.000136,+0.006421]**, still including zero.
- For H7-H0 the paired mean monthly log excess is +0.002570, approximate 95% circular block bootstrap **[-0.001804,+0.006683]**, also includes zero. H7-H5 mean -0.000488, CI [-0.002584,+0.001686], also spans zero.
- H7 performance by historical slice: 2017–2020 10.758% annualized vs H0 10.953% (underperforms); 2021–2023 11.086% vs H0 8.444% (outperforms); 2024–2026 21.064% vs H0 10.289% (strongly outperforms). The 2024–2026 region is conspicuously influential and includes an incomplete 2026. Forward persistence is unknown.

## Concrete candidate strategy and exact behavioral specification
**Research H7:**
1. Begin with *frozen* as-of R_H rank scores of eligible ETFs, monthly signal at last observed month-end close.
2. Hold each of the prior month's ETFs only if its rank remains within current Top5; fill any vacated positions from current ranking until holding exactly two ETFs. Do not reoptimize H5 top5 on the same panel.
3. Calculate a synthetic broad-European-market equal-weight daily log-return index from **as-of price history**. When (a) synthetic index below its own 200-daily-observation moving average **and** (b) 21-observation daily return volatility exceeds 126-observation volatility, scale risky ETF weights to **25% + 25%** and hold other 50% as zero-yield cash. Otherwise scale selected Top2 to **50% + 50%**. Gate known only from data as of signal date.
4. Enter at next common tradable open, exit/refresh next common monthly open; assume one-way fee 0.1% on half L1 weight turnover plus later changes in the cash sleeve. **Full implementation must reconcile initial funding convention, real EUR cash returns/FX, spreads and market impact before any deployment.**
5. All signals presently depend on the hindsight-chosen EUR60 snapshot and on old refitted ranker artifacts. This is NOT yet a standalone live operational signal.

## Scientific decision and stop rule
1. **Retain H5** as the lean, primary research candidate: simple, stable under tiny score noise, materially lower turnover, strongest retrospective CAGR.
2. **Retain H7** as the risk-constrained research candidate: better sampled DD and Sharpe with moderate CAGR cost, more desirable when avoiding severe losses is important. Its H3 overlay was tested AFTER H5's standout result and is even more selection-biased.
3. **Reject H2 and H4 for trading until they independently beat simple proper-score risk controls.** They may remain instrumentation/diagnostic modules.
4. Do **not** further sweep hysteresis ranks, thresholds or vol horizons on the burned EUR60 history. Doing so would turn the lab into noise fitting.
5. The decisive next experiment is **new independent point-in-time fund data** including ETF start dates/delistings, verified Europe underlying region, ISIN uniqueness, EUR trading venue, actual defensive cash proxy, and raw-price versioning. Freeze both H5/H7 code and all thresholds *before* forward evaluation, report monthly paired outcomes and daily drawdowns, proper risk scores and real net execution.
6. Only promote after genuinely independent prospective evidence, broad-market benchmark comparison, fees/FX and risk governance review. No truthful assertion of robust future alpha can be made from a handful of mined historical tests.

## Evidence retention
Full source, branch and committed receipts persist on Git beyond 90-day Actions artifact expiration. The raw 113-month ledgers, all monthly state snapshots and score perturbation trials remain in the cited Actions artifacts for 90 days only; preserve any that are required later before expiry. Main repository `etf_trader` and default branch are unchanged.
