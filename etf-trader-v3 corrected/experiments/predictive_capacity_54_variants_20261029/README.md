# ETF Trader — statistical first-stage predictive-skill audit, 29 October 2026

**Research-only; original production V2/V3/USA149/B0 untouched. No new model fit.**

**Goal:** compare predictors as ETF-month forecasts before rewriting the investment/portfolio layers. Strictly separate universes; historical 2018–2026 has already been used for research and is not an untouched holdout.

Recoverable per-instrument variants in frozen archives: **24 USA149** (V2 raw/post-score six each, V3 Legacy/Downvol/Corrected, L01 Pair63/NDCG127/Lambda16, L02 Tail45 regression/event, L04 blend variants, MOM252); **14 EU155** (nine fixed, 3 annual Ridge, 2 annual relative-return Ridge); **10 native EU165 fitted 2025** (Titanium, ET and XGB tail, V2 full score, V3 actual Pair127/Pair25, momentum horizons); **6 EU165 2021–26 proxy** (never called genuine V2/V3). This is **not a census of all historical project variants**; many experiments have no retained date×ETF OOS score record.

**Primary USA149 design:** identical 149 instruments and forward 21-trading-session return, 101 evaluated signal months from 2018 through 2026; canonical 500 fixed ×24 baskets SHA `36a45916b5d8191f3ccd206f39bf3fd3f1ed4bcaffd474e352b69c598f2b6a5e`. Monthly Spearman rank IC over 149; Top1 and Top3 actual-winner capture averaged over baskets. Time is the **statistical unit** (500 baskets are overlapping, NOT independent). Six-month circular block bootstrap nominal CI, Holm across candidates/metric, exploratory because many prior model selections were made on this history.

| USA149 archived variant | mean IC | basket Top1 | basket Top3 |
|---|---:|---:|---:|
| Random 24 candidates | 0 | 4.17% | 12.50% |
| MOM252 raw price-only | −0.0002 | 14.99% | 27.64% |
| V2 depth4 post-score | .0662 | 12.65% | 30.13% |
| V2 127 leaves post-score | .0464 | 15.19% | 38.17% |
| V2 127 raw = V3 Legacy | .0428 | 15.09% | 35.74% |
| V3 Corrected Pair127 | .0385 | 14.55% | 35.47% |
| V3 Tail Event45 | .0264 | **17.51%** | **42.75%** |
| V3 Blend Pair50/Tail50 | .0360 | 16.70% | 41.90% |
| V3 Blend Pair25/Tail75 | .0309 | 17.41% | **42.62%** |

**2018–2024 without 2025:** Top3 capture MOM252 25.93%, V2 127 37.14%, V3 Corrected 34.70%, V3 Blend25/75 **41.77%**. Blend–MOM difference +15.84 pp (month-block 95% interval +10.85 to +20.86 pp); note US and EU sample cannot be swapped. V2 RAW leaves127 is exactly identical to V3 LEGACY on the full 15,198 ETF-months, with equal forward labels. V2 RAW and V2 post-processed SCORE have distinct cross-sectional rankings; never equate them.

**Pairwise:** V3 Blend25/75 vs V3 Corrected +7.14 pp Top3 (95% block CI +3.38 to +10.56 pp; survives within-panel exploratory Holm). V2 127 score vs V3 Corrected +2.70 pp Top3 (+0.66 to +4.57 pp nominal CI), **not robust after Holm**.

**Crucial economic qualification:** Top3 hit can be improved *without improving realized average next-21-day return of the 3 ETF picks*. Mean future Top3 equally-weighted open-return: MOM252 +1.11%/21-session; V2 127 +1.31%; V3 Corrected +1.30%; Blend50 +1.32%; Blend25/75 **+1.21%**; Tail Event45 +1.20%; average of all 24 candidates +0.78%. Blend25/75 vs V2 127 difference -0.092 percentage points per month (95% block CI -0.334 to +0.153). This is a *forward-return diagnostic*, **not a tradeable NAV backtest**.

**Macro-category attribution (original USA149 six groups, not proper industry sectors):** mean group-ranking IC MOM252 -0.0135, V2 127 +0.0982, V3 Corrected +0.0775, Tail +0.0959, Blend25/75 +0.0919; within-category ETF-ranking IC MOM +0.0351, V2 -0.0139, V3 -0.0166, Tail -0.0192, blend -0.0209. Interpretation: signals may be stronger at choosing **macro group leadership** than choosing very similar ETF wrappers; needs an actual PIT industry taxonomy for a banking claim.

**EU155 on 65 matched 2021–26 months:** MOM252 IC +0.0836, KALMAN_IDIO +0.0800, Ridge momentum +0.0087, Ridge momentum+Kalman +0.0036; no evidence Kalman is better than momentum. EU165 2021–26 *proxies* have Ridge IC +0.0773, MOM252 +0.0636, V3 proxy +0.0191, V2 proxy +0.0076. Actual *2025-only EU165* native scores: MOM252 +0.2672, V3 Pair127 +0.1438, V3 Pair25 final +0.1271, V2 final +0.1196, MA3 Tail +0.0119. These groups are never pooled or used to claim comparable universal outperformance.

**Decision gate:** retain V2 127, V3 Pair127, V3 event Tail45 and Blend50 as separate research specialists. Before rewriting CAGR layers, verify cross-year/month regime stability and cost-adjusted next-21/42/63-day return *conditional on HOLD vs SWITCH*, true PIT asset and sector membership, actual ETFs with liquidity/closing data, and matched EU165 yearly fits. No model/portfolio layer promoted yet.

Downloadable self-contained *audit results/source scripts* (excluding unchanged large original model/raw data inputs) in conversation artifact `ETF_TRADER_CONFRONTO_STATISTICO_54_VARIANTI_20261029.zip` SHA256 `e0e30c196d48e8a48064bf93b319e5c0f7df3a2d06c22889fb6884ed3a9ead49`. Archive includes complete month-by-month scorecards, per-year statistics, pairwise CIs, group vs within attribution, prospectively matured source fit references, price-only control, explanatory report and SHA source manifest. All archived original score source pointers in `SOURCE_ARCHIVE_HASHES.csv`.

Original models and production unaffected.
