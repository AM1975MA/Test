# V3 — Traiettorie future 21/42/63 sedute in luogo del ranker: confronto USA149 vs EU148

**26 ottobre 2026 — esperimento completo, analisi diagnostica, NON produzione.** Interpretazione di «LM»: **linear model Ridge** multiorizzonte; un **LightGBM** robusto è stato incluso come controllo ML non lineare. NON è stato usato un generative language model/LLM.

## Evidenza e riproducibilità

- Training 18/18 annual fits PASS (due universi x 2018–2026): [Actions run 40394516018](https://github.com/AM1975MA/Test/actions/runs/40394516018).
- Economic evaluation corrected and validated (single account EUR, 101 signals, 2076 daily marks, same opening-price cost engine as original V3): [Actions run 40395611231](https://github.com/AM1975MA/Test/actions/runs/40395611231).
- Original V3 127 comparison, untouched models: [Actions run 40227417589](https://github.com/AM1975MA/Test/actions/runs/40227417589).
- Code: [annual LM and LGBM training](fit_multihorizon_trajectory_lm_20261026.py) and [economic/predictive evaluation](evaluate_multihorizon_trajectory_lm_20261026.py).
- GitHub Actions artifacts: 18 per-year files v3-signed-trajectory-US149/EU148-YYYY (each predictions + maturity audit) and final v3-us-eu-signed-trajectory-lm-lgbm-vs-frozen-ranker-economics (60 economic rows and 20 predictive rows + daily NAV, trades, trajectories).

All 125 original corrected V3 features, same historical US and EU prices, common 101 monthly dates, no training leakage. **For every annual fit only historical examples whose forward 63-session entire path matured before January 1 of that year**. All test ticker-months preserved, no screening by outcome labels.

LM_RIDGE_PATH = median-imputed standardized 125F -> multi-output Ridge(alpha=250) fit with equal month weights, absolute signed future21/42/63 returns, not cross-sectional rank-percentiles. LGBM_MEDIAN_PATH = 3 separately fitted conditional-median regression LightGBMs with 220 trees, 15 leaves, L1 loss. P21 policy = predicted +21session signed return. PATH policy = **fixed a priori** score: 0.70*R21 + 0.20*(R42/2)+0.10*(R63/3)-0.30*max(0,-min(R21,R42,R63)). This path score is a portfolio selection functional derived from the predicted trajectory, not additional model fitting. 10bps one-way turnover cost.

## Full universe net EUR Top5 results (2018-02-01 to 2026-07-01)

| Model | US149 CAGR | US MaxDD | EU148 CAGR | EU MaxDD |
|---|---:|---:|---:|---:|
| Frozen V3 127 ranker | +13.86% | -41.31% | +3.91% | -46.97% |
| **Ridge LM P21** | **+19.65%** | -44.44% | +4.34% | -30.02% |
| Ridge LM PATH | +19.44% | -46.85% | +3.18% | -30.95% |
| LightGBM L1 P21 | +18.07% | -37.21% | +6.77% | -33.35% |
| LightGBM L1 PATH | +15.12% | -37.03% | +5.04% | -34.84% |

Equity-only Top5:
US V3 +11.81%, LM P21 +12.46%, LightGBM P21 +11.21%;
EU V3 +10.96%, LM P21 +8.27%, LightGBM P21 +8.80%.

**Crucial observation**: Combining P21 with P42/P63 has NOT improved consistently over P21 alone in either country, despite predicting all three horizons. No hyperparam selection was performed on this comparison. The 21d target better matches the approximately monthly execution cycle.

## Forecast skill and calibration (mean of all 101 monthly cross sectional scores)

| Scope full | US V3 | US Ridge P21 | US LGBM P21 | EU V3 | EU Ridge P21 | EU LGBM P21 |
|---|---:|---:|---:|---:|---:|---:|
| Spearman IC against signed future21 | +0.0343 | **+0.0795** | +0.0656 | +0.0036 | +0.0240 | +0.0002 |
| Top5 signed 21d excess vs monthly universe mean | +0.806% | **+1.361%** | +0.873% | +0.205% | +0.071% | +0.287% |
| Top5 selections landing future worst decile | 22.18% | **17.03%** | 8.91% | 17.82% | 15.45% | 11.68% |

**Absolute forecast MAE** (all candidates, relative to naïvely forecast zero return): US Ridge **4.4865%** vs zero **4.4233%**; US LGBM **4.3354%** vs zero **4.4233%**. EU Ridge **3.8626%** vs zero **3.6326%**, EU LGBM **3.6562%** vs zero **3.6326%**. Ridge can improve rank selection in US *without* being a calibrated numeric price forecast. Neither EU model shows robust point forecast skill over zero return.

Paired 20,000 circular block 6-month bootstrap, same 101 signal dates, each comparator V3 127 (source CSV stored with report download):

| Difference of LM Ridge P21 minus original V3 FULL | Observed | 95% paired bootstrap |
|---|---:|---:|
| US mean monthly IC | +0.0452 | **[+0.0061,+0.0827]** |
| EU mean monthly IC | +0.0204 | [-0.0376,+0.0749] |
| US CAGR net difference (pp) | +5.79 | [-5.32,+17.44] |
| EU CAGR net difference (pp) | +0.44 | [-7.94,+9.30] |

The US directional IC improvement clears zero **within this fixed test**. Neither US nor EU CAGR gap excludes zero. These CIs do **not** adjust for exploratory and previously viewed 2018–2026 returns or hypothesis selection; they do not validate future alpha.

## CRITICAL investability audit: EU forward trajectory models select many zero-volume names

From corrected exact NAV/economic replay, among 101 Top5 monthly rebalances:

| EU FULL model | Count of traded lines reporting zero execution-day volume |
|---|---:|
| Frozen V3 127 | **4** |
| LM Ridge P21 | **67** |
| LightGBM P21 | **15** |

Therefore comparing EU CAGR from raw Open-filled backtests without gating liquidity **is not an executable profitability claim**. Note that vendor-reported zero volume alone does not prove a trade impossible, but the Open fill is unverified.

A separate **causal as-of filter** using the PREVIOUS 63 observed Xetra trading sessions: 90%+ have positive reported volume, median (close*reported volume) >= specified threshold EUR. Each portfolio, same 101 months. Two policies: CASH_REJECT retains empty 20% slots in zero-interest cash; RERANK replaces an ineligible ETF with the next highest predicted-score candidate *known to be eligible at signal*, without using future returns or execution-day volume for ticker selection. Original unfiltered NAV **exactly replayed** for each model and V3; same 10bps transaction cost engine.

| EU FULL Top5 with as-of €250k median traded and >=90% positive-volume sessions | CAGR | MaxDD | execution-day zero reported volume |
|---|---:|---:|---:|
| **V3 RERANK** | **+9.85%** | -42.06% | 0 |
| **LM Ridge P21 RERANK** | +3.68% | -32.99% | 0 |
| **LightGBM P21 RERANK** | +5.49% | -35.75% | 0 |
| V3 CASH_REJECT | +5.07% | -27.84% | 0 |
| LM Ridge CASH_REJECT | +2.20% | -17.74% | 0 |
| LightGBM CASH_REJECT | +2.87% | -19.53% | 0 |

As-of €50k floor plus RERANK: V3 +7.56%, LM +3.62%, LGBM +6.97% CAGR; each has 1 or 2 execution-day volume zeros. **The nominal EU gains from path regression evaporate under this liquidity eligibility sensitivity** while the original V3 itself changes significantly as eligibility improves. The threshold is illustrative and tested on already inspected history; it is NOT an independently optimized/prevalidated target threshold or verified market-depth limit.

## Honest conclusion

1. Directly forecasting the signed 21d **return** via a simple linear model gives considerably better US directional ordering than the original 127-leaf ranker, with similar timing and no future-label leakage. Strong hypothesis worth testing on true unseen vintages.
2. **Predicting a 21/42/63 return trajectory does not automatically outperform the 21d forecast** for monthly rebalancing.
3. The same LM does **not** solve the EU weakness; on EU, forecast point MAE remains worse than zero baseline; most original LM EU pick economics rely on very thin liquidity/zero reported-volume. Risk-adjusted conclusions require actual quotes and book depth.
4. The **full 148 EU vs 149 USA** universes differ in asset classes, issue dates, feature missingness, ETF correlations, trading volume and opportunity dispersion. The US Ridge improvement cannot be transported to the EU population automatically.
5. No model is ready for production: US LM vs V3 CAGR difference lacks robust bootstrap statistical significance; EU strategies require point-in-time investability and tradability; the entire inspected 2018–2026 period is not an untouched test set.
6. Next defensible test: point-in-time liquidity eligibility BEFORE model ranking/regression, stratify comparable equity category/cohort, directional and MAE calibration by forward horizon, false positive worst decile, beta/factor exposure; freeze one version on pre-2018 and test unseen additional future periods without posthoc selection.

**Correct source handling:** branch research/v3-europe148-historical-20261024, production branch/model unchanged. Data and scripts also packaged in the conversation ZIP including European as-of liquidity replay and paired bootstrap diagnostic.
