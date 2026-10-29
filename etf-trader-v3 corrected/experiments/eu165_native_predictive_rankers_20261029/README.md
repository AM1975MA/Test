# EU165 native source V2/V3 predictive performance comparison (2026-10-29)

**RESEARCH ONLY. Frozen production unchanged. No portfolio-layer/CAGR optimization conducted.**

Recovered original V2, V3 corrected and MA3 source code, price and PIT basket inputs. Independently fitted annual **2018–2026** EU165 source-native rankings: Titanium V2, V2 Leaves127, V3 Corrected Pair127, V3 logistic 45-feature Event Tail and Ridge45 Tail, source MA3 ET/XGB, 3 seeds where specified. Previously archived European V2 Titanium 2025 scores 1816/1816 exact match; 2025 MA3 ET/XGB component scores 1814/1814 exact match. Every fit trained only labels matured before annual cutoff. Evaluated same **500 baskets x24** on valid 101 monthly PIT dates (4 per each of six macro-groups); **91 months with complete matched data, 75/84 in 2018–24**. 2025/2026 separate. 500 highly overlapping portfolios DO NOT create 500 independent observations.

**Pre-2025 75 paired months, 21-session forward open returns, basket best-ticker Top3 capture:**
- MOM252 21.28%; IC +.0329; average top3 future return +0.16%
- V2 Titanium 28.34%; IC +.0081; average top3 +0.28%
- V2 Leaves127 26.87%; IC +.0085; average top3 +0.33%
- V3 Pair127 28.50%; IC +.0210; average top3 +0.48%
- V3 Tail Event45 29.15%; IC +.0070; average top3 +0.27%
- V3 Tail Ridge45 29.08%; IC +.0262; average top3 +0.40%
- experimental Pair25/Event75 blend 30.09%; IC +.006; average top3 +0.28%.

**Inference:** Six-observed-month circular month-block bootstrap. Nominal V3 Event45–MOM Top3 difference **+7.87 pp**, 95% CI **+1.65 to +14.64 pp**, but exploratory Holm over 23 candidates p **0.267**; V2 Titan difference +7.06pp, 95% CI +1.05 to +13.35 pp, Holm p **0.342**; V3 Pair difference +7.22pp, CI +.24 to +14.02 pp, Holm p **0.651**. Neither beats MOM in top3 future return with confidence (V3 Pair +0.314pp, 95% CI [-.515,+1.109]pp, Holm p 1). This is ranker skill, **not** realized tradeable strategy net returns.

**Separate six-macro-group choice**: 2018–24 MOM best-group hit 15.79%, V2 Titanium 28.95%, V2 Leaves127 31.58%, V3 Pair127 30.26%; source-derived full V3 Pair25Hybrid (65 months) 30.77% vs matched MOM 12.31%, difference **+18.46pp**, block CI +6.15 to +30.77pp, *within seven group-model comparisons* Holm .042 exploratory. Macro-group is not verified PIT industry taxonomy. Not generalizable proof.

**2025 contrasts**: MOM rank IC +.2624; V3 Pair +.1142. Top3-future-return MOM +2.57%/21d vs V3 Pair +2.25%. Historic 2025 widely mined.

**Limitations**: 2026-defined survivors, no delisted ETFs, dividend / total returns uncertified, price-only forward labels and real executable spreads unverified, 9 pre2025 signal dates excluded due incomplete pan-European calendar, six macro-clusters not real economic sectors; original V2/V3 downstream portfolio layer NOT rerun for 2018–26, portfolio CAGR comparisons NOT provided; historical data already heavily used so no untouched holdout claim. Native trained group score no group-specific capital allocation policy tested. NO production change.

**Downloadable full reproducible archive**: `ETF_TRADER_EU165_CONFRONTO_PREDITTIVO_NATIVO_20261029.zip` (44MB), SHA256 `6156c361778fe293d36671d23db0f09d04d4fdc5b3cc7bc49081b8e0ec5bc045`, 197 internal files: source, daily EU165 input, full PIT dynamic baskets, all annual score/fit audit, monthly paired 21-day outcomes, bootstrap with Holm, group-vs-within, report and plots. This branch stores summary and compact figures; large input retained in conversation artifact.

**Decision:** keep native rankers for next test of decision utility vs HOLD/SWITCH on matched EU165 and 2018–24. Do **not** rewrite portfolio conversion layers until incremental net expected return/conditional regret with real costs is demonstrated in source-backed walk-forward.
