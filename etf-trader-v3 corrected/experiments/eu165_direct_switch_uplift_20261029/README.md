# EU165 direct expected candidate-minus-incumbent return — multi-horizon research

**29 October 2026. RESEARCH ONLY. No production V2/V3/B0/USA149 changes.**

Study: EU165 original natively fitted annual V2/V3 ETF scores, 500 historical PIT 24-ETF baskets, 6 macro clusters and same monthly Momentum252 previous-month Top1 incumbent across 21/42/63 day counterfactuals. Direct target is **future Open-to-Open return of proposed candidate minus return of current ETF**, net of 0.10% per side (0.20% full SWITCH). This is **NOT** self-financing multi-month NAV/CAGR.

**Raw event gate:** 890,568 candidate/basket pairs including HOLD, 137,801 unique month-incumbent-candidate pairs. Fit uses deduplicated pairs, maturity embargo to 1 January of each fit year, yearly expanding source-only training 2021–26; principal historical diagnostic 2021–24 has 43 months for 21/42-day tests, 42 for 63-day. Overlapping baskets are **NOT** independent statistical observations.

Executed **four complementary families**:
1. 24-way direct Ridge MOM / Ridge ALL / LightGBM mean / profit-probability / 20th percentile quantile with an ex-ante pairwise relative-volatility penalty;
2. independent economic accept/reject meta-learning on source-native Top1 specialist proposals;
3. same meta-learning on native V2/V3/MOM Top3 proposal union;
4. separate absolute 5% loss LightGBM risk model whose predicted probability is used only as a veto for native V2/V3 swaps.

**Pre-2025 outcomes; mean incremental NET return over holding (pp per 21-day decision, not CAGR):**

| Policy | mean Δ net pp | switch rate |
| --- | ---: | ---: |
| HOLD | 0.000 | 0.0% |
| MOM252 Top1 automatic | -0.200 | 38.3% |
| V3 Pair127 Top1 automatic | -0.572 | 89.2% |
| Top3 specialist shortlist + meta LightGBM mean | +0.057 | 65.9% |
| Top3 shortlist + meta P(profitable after costs)>60% | +0.054 | 11.3% |

**No positive advantage is robust:** block 95% CI for Top3 meta GB mean [-0.536,+0.620] pp; for P60 [-0.062,+0.211] pp. Direct lower 20th percentile rule performs almost no trades, therefore cannot be promoted as forecasting superiority. Full 24-way model chosen freely overtrades. Conditional expected-return OOS R2 vs zero is low; AUC of profitable switching classifier ~0.492,0.508,0.572 at h=21,42,63. Predicted lower 20th percentile undercovers downside (empirical below ~23.3%,27.9%,30.5%).

**Separate risk finding** (pre-2025, V3 Pair127, 42 day future loss ≤-5%): absolute-loss event among chosen ETF falls **19.19% → 11.56%** after a simple veto when predicted loss risk >20%; switch rate **89.21%→37.21%**. Difference -7.64pp, 6-month bootstrap interval [-14.61,-2.01]pp; exploratory within-family Holm p=.011. BUT mean net switch-vs-HOLD remains **-0.115pp** vs **-0.680pp** unfiltered. Risk-model Brier score does not consistently beat constant historic event frequency, hence probability calibration is NOT production-ready.

All 2018–26 vintages have already been extensively used for research, the 2026-defined ETF universe has survivorship bias; dividends/total-return, spread and true execution price not certified; 42/63-day forward outcomes overlap; prior-incumbent definition is MOM only and favours momentum. No untouched holdout, no independent statistically validated positive alpha, no proposed deployment.

**Reproducible full package**: `ETF_TRADER_EU165_DIRECT_INCREMENTAL_PAIRWISE_20261029.zip`, SHA256 `763e6d5ba3cc57c4920b91e676a033c1c8193175613ff21ffd61c18a731d9889`, 30,853,566 bytes, **210 files** with all inputs incl. 165 daily price series, source-native frozen ETF-month model scores, PIT baskets, model code, calibration and statistical result tables, bootstrap, standalone report, plots, source SHA manifest. ZIP integrity and 12 portable Python source-compilation checks PASS. Complete source-native ETF model training provenance is in prior `ETF_TRADER_EU165_CONFRONTO_PREDITTIVO_NATIVO_20261029.zip`.

Research decision: preserve V2/V3 as opportunity specialists; study calibrated downside-aware accept/reject (and the full path of incumbents for MOM, V2, V3) before portfolio layer changes; test positive incremental return on truly unseen data. **No source/production merge.**
