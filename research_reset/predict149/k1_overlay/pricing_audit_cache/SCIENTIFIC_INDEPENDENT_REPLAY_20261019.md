# T149-L — F3/H1 selects, K1 controls risk: INDEPENDENT EXACT-PRICE AUDIT
19 October 2026, 18:01 CEST. Original149 (149 fixed US survivor ETFs) and **86 distinct ETF names actually selected** by F3/H1, same 64 investment blocks, same **1345 daily Open** prices 2021–26. **No new predictor training and no retrospective parameter sweep**.

## Provenance and audit integrity
Original frozen 9536 ticker-month prequential `K1 P_DOWN5` forecasts (51 post-warmup months, first 13 months unchanged frozen F3/H1 50/50) in `research_reset/predict149/walkforward_stacking/results/ALL_9536_PREQUENTIAL_STACKING_FORECASTS.csv`; frozen 64×Top5 selections in `ASOF_64_MONTH_MODEL_SELECTIONS.csv`; 1345-day reference in `research_reset/predict149/complementarity/results/EXPERTS_AND_REAL_COSTED_MIXTURES_DAILY.csv`. Original quote source `evidence_v1/data/original149/{ticker}.csv` and exact common 1345 opening dates cached WITHOUT transformation under `pricing_audit_cache/quotes_0.csv..quotes_7.csv` on this audit-only branch. Source original149 universe file SHA256 `7bccf1b756bf3652280a254c7486fb43f1e805ebb4cdf10731cecc74007292e6`.

**Same actual self-funded next-Open cash/ETF share solver as `research_reset/m0b/enrichment.py::rebalance_exact`**: 0.1% on every buy/sale, update quotes at next-open at each 21-session start, solve `W_after = W_before − .001*sum|target_weight*W_after − marked_prior_shares|` by fixed point, zero leverage and zero residual cash, no rebalancing between 21-session anchors; cash-mark every daily Open. Exact original STATIC_F3_H1_50 daily revaluation reproduced against stored portfolio with absolute error **2.220446049250313e−15** across ALL 1345 daily values. This checks the financial path, not only terminal return. Reconstruction performed independently using connected original GitHub price files via JavaScript; **GitHub Action job `39280415327` in separate source branch was QUEUED when independent results were written**. Do not say the queued Action succeeded. Python research code and precommitted protocol are committed to `research/149-K1-risk-overlay-F3-H1-20261019`.

## Actual FULL 64-date historical self-funded results
| Portfolio | CAGR (nominal 10 bps) | MaxDD daily Open | Sharpe log annualized | ES worst 5% daily |
|--|--:|--:|--:|--:|
| Original F3/H1 50:50 | **23.2151%** | −24.8442% | **.88692** | −3.30233% |
| K1 redistribute within frozen 5 picks per expert (L1) | 22.5058% | −25.4015% | .87167 | −3.27962% |
| K1 allocate between F3/H1 (L2) | 22.4174% | **−24.5065%** | .86613 | −3.29318% |
| K1 both within and between (L3) | 21.5939% | −25.1104% | .84790 | −3.26548% |
| Invert K1 risk signal on same named picks (L4 adverse control ONLY) | 24.0494% | −26.9021% | .88797 | −3.38698% |

All five policies charge actual same next-Open 10bps bilateral fee on actual union of ETF holdings (five+five, overlaps merged), no fee-free arithmetic averaging of NAV curves, no new ETF selections, and reverse-control is an explicit falsifier, NOT a recommended investment method. The `L0` historical prior-only null had identical p across 149 within each date and MUST exactly replay 50/50; exact equal-probability code invariant tested in `test_run.py`. Independently reconstructed portfolio result is not full GH runner test output until job starts.

### 3-anchor grouped bootstrap of paired log net returns vs static 50:50, mean per 21-trading-session month
| Model | Mean log advantage / month | 95% CI | Early 2021–23 | Later 2024–26 |
|--|--:|--:|--:|--:|
| L1 within 5 picks | −0.000483 | [−0.001640,+0.000608] | +0.000093 | −0.001177 |
| L2 expert tilting | −0.000543 | [−0.001644,+0.000539] | +0.000693 | −0.002035 |
| L3 both | −0.001107 | [−0.002903,+0.000649] | +0.000730 | −0.003325 |
| Inverted signal control | +0.000564 | [−0.001275,+0.002436] | −0.001110 | +0.002584 |

Post-warmup only average paired 21d log advantage L1 −.000605, L2 −.000682, L3 −.001390. All post-warmup bootstrap intervals contain zero. Marginal expected shortfall improvement of L1/L2/L3 (~0.01 to 0.04 percentage points/day) is not sufficient when CAGR falls and L1/L3 drawdown worsens. L2 reduces maximum drawdown just ~.338 percentage points but gives up ~.798 percentage points of CAGR per year. Primary joint risk/economic gates FAIL for every overlay.

## WHY K1 Brier did not translate into portfolio risk skill
K1 originally improved probability of ETF UNDERPERFORMANCE **relative to benchmark 60%SPY/40%AGG by 5% over 21 sessions** on all 149 ETF rows:
- prior K1 whole149 Brier gain (negative tail) **+.005303**, 95% grouped anchor CI [+0.003005,+0.007777].
- among only the selected F3 and H1 actual 10 basket slots per date, including overlaps twice for their economic weight, the **510 selected ETF-slots over 51 K1-trained periods** have mean predicted P(relative<-5%) **14.585%**, actual event **15.882%**, stale matured-universe rate **11.836%**. Brier improvement K1 vs historical prior only **+.001506**, 95% 3-anchor grouped bootstrap interval **[−.003442,+.006799]**, includes zero; no convincing conditional selection-specific skill.
- Same selected held nominal actual Open-to-Open loss <-5% event rate **16.667%**; K1 P(relative<-5%) is NOT trained to predict this event. Applying a relative risk score as absolute risk budget is inherently questionable.
- Several F3/H1 picks are commodity future-linked and correlated (e.g. USO/BNO/DBO/USL). Independently low individual event risk is not the portfolio crash-tail distribution, and the K1 heads do not model **joint** tail dependence. 
- Reverse risk weighting outperforms K1 in historical CAGR but has the worst tail loss and maxDD; this is a falsification, not a positive risk policy.

**Decision:** Do NOT overlay frozen K1 with these prescribed formulas on real money; preserve F3/H1 STATIC 50:50 as provisional historical control, NOT live validation. Scientific confidence is low due 64 reused 2021–26 USD survivor dates, no independent holdout, no point-in-time ETF roster, no EU brokerage quote/fee/FX. K1 class-relative tails have some full-universe skill but **no verified incremental protection for held positions**.

### How to make this same idea genuinely useful without tuning on known outcomes
Train a wholly separate selected-position/portfolio-specific tail model for prospective tests, with target **actual 21-day nominal loss, intraperiod maxDD or portfolio ES/CVaR**, and as-of covariance / concentrated factor-beta exposures. Portfolio consequences must be tested on independent economic/price/vintage data not used to pick the transformations. Only then define a de-risking budget with uncertainty and transaction costs; don't optimize loss cutoffs, clamps or 50/50 weights on these 64 anchors to manufacture CAGR.

**Source status:** user experiment fully built as branch `research/149-K1-risk-overlay-F3-H1-20261019`; GH Actions run id `39280415327` was still `queued` at 16:02 UTC. The full independent matched next-Open numerical replay above IS executed and parity-tested. No modifications to production `etf_trader`.
