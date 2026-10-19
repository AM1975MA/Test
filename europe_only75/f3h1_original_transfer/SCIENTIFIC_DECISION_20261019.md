# Original F3 / H1 / H3 retrained on EUROPE-only EUR60 — final scientific verdict
**19 October 2026 | GitHub Action [39297876064](https://github.com/AM1975MA/Test/actions/runs/39297876064) SUCCESS.** Code, preregistration, as-of FX history, forecasts, full costed European daily ETF-share portfolio trajectories, source checksums and experiment artifacts saved on isolated research branch. Production etf_trader unchanged.

## IMPORTANT: this is the missing original F3/H1 comparison, not R_H with a risk layer
Europe-only **60 candidate EUR trading lines with exclusively European underlying ETF exposure** selected from audited 75 geographically Europe candidates; the 45 other legacy EU120 mixed geographically or non-UCITS exposures stay excluded. It is an original July-2026 retrospectively selected survivor cohort, **not a PIT UCITS investible roster**; FX venues, same-ISIN duplicate funds, brokerage spread/tax need external checks. Training is fresh on EUR60 historical target prices; NONE of the original149 US ETF model weights or target labels were trained into European F3/H1.

Recreated original F3 (19 price/vol/group features+6 Europe classes, 3 fixed LightGBM quantiles q10/50/90, (q10+2q50+q90)/4), H1 (ten original US proxy factors relative to 60/40 SPY AGG benchmark, 126 Close historical ETF betas ridge .005 + 30-attribute momentum context Ridge alpha60), H3 (original F3-independent factor-conditional residual quantile regression summed with H1), quarterly re-estimation on STRICT earlier matured training labels. To avoid illegal information use of US after-close data at European decision time, original 11 US-factor ETF proxies and EURUSD=X are converted to EUR using LAST CLOSE AT LEAST ONE CALENDAR DAY BEFORE THE EUROPEAN SIGNAL; U.S. proxy ETF positions never appear in portfolio. FX source downloaded using yfinance and SHA archived. The very first January 2017 anchor lacked enough prior synchronized 126 trading-day closes and was excluded from F3/H training labels **before scoring**, all 60 candidates kept. Of 113 monthly source anchors 112 were retained for prior-data panel, and **65 forecast/outcome dates 2021-01-29 to 2026-07-01** were scored. EUROPE monthly horizon is VARIABLE ~19–23 sessions, not US exact 21-session original. This is necessarily a faithful *architectural adaptation*, not numerically the identical American model or US market clock.

Frozen R_H control: original 10-fold annual EUR60 scores from Action [39071370480](https://github.com/AM1975MA/Test/actions/runs/39071370480), R_H=.475 European return-aware percentile +.525 European hybrid residual/tail score, 2 highest ETF each half weight. Original historical approximate-cost R_H 113-period terminal 2.448863449071208 was exactly reconstructed (absolute error **2.22e-15**). Previously *recomputed self-funded ETF-share R_H 2277 daily Open values* matched in this run max abs error **4.44e-16**. Same exact ETF share/10bps each way cash-neutral execution engine for all five strategies and identical 65 anchors /1331 European common Opens.

## Matched 2021–July 2026 cash funded economics (same dates & same cost rules)
| European algorithm | 2021–26 net CAGR | Daily Open MaxDD | Annualized daily-log Sharpe | Worst 5% daily ES | Mean positions |
|---|---:|---:|---:|---:|---:|
| R_H European-only model | +8.3122% | -25.6954% | .3950 | -2.9880% | 2 |
| **F3 genuine EUR60 refit Top5** | **-1.6321%** | **-35.6094%** | -.0975 | -2.5764% | 5 |
| H1 genuine EUR60 refit Top5 | +4.4092% | -33.1460% | .2551 | -2.6806% | 5 |
| H3 genuine EUR60 refit Top5 | +7.5854% | **-24.4427%** | **.4307** | **-2.5635%** | 5 |
| F3/H1 50:50 merged Top5s | +1.6674% | -32.3394% | .1063 | -2.5078% | 9.63 |

Earlier R_H 2017–2026 -44.02% MaxDD /9.05% CAGR refers to LONGER 113-month period, NOT comparable with these 65-month figures. The original old 9.978% European R_H CAGR used an approximate *different* fee/holding convention; do not conflate.

## Key actual signed predictive score diagnostic (65 independent monthly anchors, 3900 ticker-label rows clustered by anchor)
Cross-sectional Spearman vs future next-period signed EUR ETF excess log return, three-month circular block bootstrap date-level 95% CI:
- F3 **-0.08241**, CI **[-0.14578,-0.01749]**. Statistically negative direction on this reused sample. It did NOT preserve signed ranking efficacy.
- H1 **+0.03452**, CI [-0.03552,+0.10146], not significant.
- H3 **+0.00636**, CI [-0.06195,+0.07435], not significant.
- Selected five per-date mean signed relative log payoff: F3 -0.008262, H1 -0.003524, H3 -0.001053. These are benchmark-relative, NOT absolute investment returns; no proof of positive signed alpha.

Original F3 q10 conditional pinball .007791 vs historical matured null .007823 (tiny model advantage), but F3 q90 conditional pinball .007094 vs matured null .007025 (worse). H1 next-period ten-factor payout MSE **.002206** vs train-matured unconditional factor-mean **.001973**: clear factor amplitude forecast weakness, as in US study.

## Paired net log growth vs frozen European R_H
Each month samples entire date not ETF rows, 2500 three-anchor circular-block bootstrap:
- F3 mean -0.008015, CI [-0.016748,+0.000531] per month; DD **worse 9.914 percentage points**.
- H1 mean -0.003055, CI [-0.010925,+0.004860]; DD **worse 7.451 pp**. EARLY 2021–23 -0.012164 monthly, late 2024–26 +0.008254 monthly.
- H3 mean -0.000560, CI [-0.008558,+0.007096]; DD **better 1.253 pp**, daily ES better +0.424pp. EARLY -0.005535, late +0.005615 monthly.
- F3/H1 50/50 mean -0.005269, CI [-0.012836,+0.001790]; DD **worse 6.644 pp**. EARLY -0.010496, late +0.001219 monthly.

**Preregd F3/H1 50:50 scientific GO: FALSE.** It underperforms R_H in net CAGR and DD and does not show reliable ranking. H3's modest historical risk benefit is a research lead, **not** statistical proof of superior future investment benefit (paired CI includes zero). DO NOT DEPLOY. Do not retune new models on these mined 2017–2026 outcomes or interpret all 3900 ticker rows as independent.

## Causal and transferable conclusions
1. The prior original149 USA 2021–26 portfolio F3/H1 50:50 +23.215% CAGR/-24.844% MaxDD is **NOT reproduced by newly refitted original architectures on these 60 European ETF lines**. This does not prove market geography itself caused the difference; horizon, price vendor, factor proxy currency/lag, six macro groups, universe size/asset coverage and target all differ.
2. The US F3 quantile-based selector exhibits *negative* European signed ranking in the retrospective sample, undermining its portability. A 50:50 mixture cannot rescue a consistently misordered expert.
3. Original European H3 residual/factor integration historically preserves more capital than F3 or H1 alone, and H3 has modestly better DD/ES than R_H, but no established alpha.
4. Focus on fresh *European* economic factor signals, genuine fund-level exposure and usable EUR trading data; validate H3 and R_H on a **new prospective vintage** rather than tune the old sample. The EUR60 list was selected from 2026 survivors with possible duplicate ISIN and historical Yahoo revisions.

Files: results/RESULT.json; results/EUROPE60_F3_H1_H3_REAL_COST_DAILY_NAV.csv; results/EUR60_ALL_60_F3_H1_H3_WALK_FORWARD_FORECASTS.csv; results/ALL_EXPERT_MONTHLY_REAL_ETF_SHARES.csv; results/MONTHLY_TRUE_FUTURE_SIGNED_RANK_SCORE.csv; results/ASOF_FACTOR_REGRESSION_MONTHLY_PROPER_SCORE.csv; results/MONTHLY_*.csv; results/EURUSD_PRIOR_US_CLOSE.csv and manifest; SHA256_MANIFEST.txt. Changes only on this branch. 
