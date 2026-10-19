# EU48 ISIN F3 H1 H3 — genuine retrain and comparative verdict, 19 Oct 2026

**GitHub Actions [39314273739](https://github.com/AM1975MA/Test/actions/runs/39314273739): SUCCESS**. Full actual model fitting (never reused trained EUR60 F3/H1/H3 parameters) and accepted validation, forecasts and portfolio backtest archived on separate Test research branch.

## Exact evaluation and models
2021-01-29 first test signal to 2026-07-01 final exit, 65 monthly periods, **1,331 daily Euro ETF Open marks**, 10bp of gross buys and sells; six Europe macro categories, 48 distinct ISIN (no multiple venue double-counting), 19 frozen original F3 explanatory features plus 6 group onehot variables. H1 original ten historical USD ETF factors converted at last *prior day* EURFX, 126 preceding common Close factors, quarterly Ridge alpha60 with beta-ridge .005. F3 quantiles .10/.50/.90 LightGBM 80 trees, lr .04, leaves 9, depth4, 100 minimum child, lambda25, seed20261019. H3 original F3-independent residual quantile plus predicted factor payoffs. Original source modules preserved; only code checks fixed to 60 were generalized to N and SHA-tagged. All training labels must exit **strictly BEFORE** the prediction signal date. 113 historical label blocks, 65 evaluated. Regressors refit quarterly. The model uses data from Jan2016/earlier for 2017 feature warmups. 48 ETF identity is mapped to the legal ISIN and price source rather than exchange ticker to prevent concentration duplicates.

## Costed next-common-Open portfolio results (all on identical EUR48 common dates)
| Portfolio | CAGR net | MaxDD Open | Sharpe daily log | ES5 daily | Mean fund positions |
|---|---:|---:|---:|---:|---:|
| F3 EUROPE48 | +3.5109% | -24.8650% | .2219 | -2.3706% | 5 |
| H1 EUROPE48 | **+7.8922%** | -21.8145% | .4442 | -2.6622% | 5 |
| H3 EUROPE48 | +5.6467% | -31.0504% | .2991 | -2.7906% | 5 |
| F3/H1 50:50 EUROPE48 | +6.0512% | **-19.6964%** | .3863 | -2.4181% | 9.46 |
| EUR60 old annual R_H predictive scores **mapped to 48 ISIN**, Top2 (NOT a new 48 REFIT) | +7.1452% | -27.5941% | .3351 | -3.0330% | 2 |
| Passive IMEU MSCI Europe 60% + EUNH EUR Sovereign 40% | +6.5008% | **-18.4484%** | **.6581** | **-1.4968%** | 2 |

The *old archived EUR60 F3/H1/H3 predictions* are replayed at exactly matched 1,331 daily EUR quotes here for a methodological check: F3 -1.6321% CAGR / -35.6094%DD, H1 +4.4092% / -33.1460%, H3 +7.5854% / -24.4427%. EUR60 original F3/H1 blend +1.6674% / -32.3394% (archived original scientific report); original cohort suffered multiple traded tickers of same ISIN, 52/65 combined Top5 portfolios duplicated same legal fund. New F3 improves historic descriptive results, new H1 improves, but new H3 is worse; this is not causal evidence that *only* ISIN dedup improved models, since universe composition, ticker venues and revised Yahoo data changed simultaneously. Original149 US F3/H1 +23.2151% / -24.844% across 64 DIFFERENT date-anchors and much wider economic opportunity (world/emerging/commodities) is context, NOT like-for-like matched comparison.

## Predictive skill on 65 independent monthly time blocks (48 ETF cross-section each)
| Model | Mean signed Spearman vs actual next period EUR benchmark-relative log return | 95% 3-block bootstrap CI | Mean Top5 benchmark-relative future log return |
|---|---:|---|---:|
| F3 | **-0.005608** | [-0.078476,+0.066281] | -0.004013 |
| H1 | +0.022953 | [-0.052659,+0.095969] | -0.000996 |
| H3 | +0.024336 | [-0.031657,+0.080154] | -0.002645 |

Old60 F3: Spearman -0.082410, CI [-0.145785,-0.017486]; new F3 no longer statistically inverse but also not significantly POSITIVE. H1/H3 overlap zero. 65 months (NOT 3,120 independent samples) is the correct inference sample; 48 labels per month share correlated market environments.

Original F3 quantile proper scores: q10 pinball .008037 vs matured unconditional benchmark .008228, q90 pinball .007271 vs matured null .007492, both slightly better than null. Factor timing H1 ridge MSE **.002223 vs matured historic mean .001972**, H1 forecast factor amplitudes remain weaker than null despite positive historical strategy profits. Predicted Top5 forward EUR ETF excess payoff negative or near zero for all methods; full-proxy EUR benchmark is a lagged 60% SPY /40% AGG reference, *not* an investable Europe benchmark.

## Net matched monthly log growth DIFFERENTIAL vs old60_RH mapped to eligible 48 funds
| Model | Mean paired monthly log advantage | 95% CI | 2021–23 | 2024–26 |
|---|---:|---|---:|---:|
| F3 | -0.002872 | [-0.011843,+0.006024] | -0.003558 | -0.002020 |
| H1 | +0.000578 | [-0.007247,+0.008118] | -0.003267 | +0.005352 |
| H3 | -0.001172 | [-0.008343,+0.006013] | -0.004316 | +0.002730 |
| F3/H1 | -0.000854 | [-0.008000,+0.006344] | -0.003110 | +0.001946 |

CIs are monthly-block circular 3-anchor bootstrap, 2,500 samples. None positive significance. H1 maxDD improved +5.78 percentage points vs mapped R_H, F3/H1 +7.90 pp; H3 DD worsened -3.46 pp. F3/H1 blend does not beat R_H on CAGR nor the passive on maxDD / ES5. Both eras do not simultaneously show paired alpha.

## Scientific decision
**F3/H1 50/50 automatic GO = FALSE**. Promotion requires higher CAGR than mapped RH, no worse DD or ES5, paired log-growth bootstrap lower>0, both eras >0, and one of F3 or H1 cross-sectional positive Spearman lower>0. Several fail. Do not deploy. H1 historical reward and F3 elimination of marked negative ranking motivate a next controlled causal experiment, not reoptimizing this same already reused sample.

## Source and files
All data recorded in branch: source and frozen protocol in the refit48 folder; results/RESULT.json; ALL_48_ISIN_F3_H1_H3_MATURITY_PURGED_FORECASTS.csv, DAILY_COSTED_EQUITY_SAME_EUROPE_DATES.csv, MONTHLY_HOLDINGS_UNIQUE_ISIN.csv, SIGNED_RANKING_BY_MONTH.csv, H1_FACTOR_FORECAST_SKILL.csv, MONTHLY_*.csv, EUR60 replay on joint days, SHA256_MANIFEST. The comparative RH annual scores from successful action 39071370480 were mapped by ISIN without pretending that 48 R_H was fitted; historical U.S. explanatory factors source action 36551650325. 111/113 source monthly entry/exit blocks had exactly the same dates as old60; 65 evaluation anchors share 1,331 daily marks.

**Non-PIT limits:** retrospective 2026 survivor stocks, selection based on ex-post price QA, Yahoo adjusted historical revised prices, 2017 fund-share-class and spread requirements not fully audited, different broad US 149 opportunity set. No source price fabrication, no trade execution evidence, no taxes/spreads, no changes to production etf_trader; these are development outcomes not prospectively validated investor alpha.
