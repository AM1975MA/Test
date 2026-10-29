# EU165 structural allocation audit: model TopK versus eligible PIT union (2026-10-29)

Research-only. Frozen 2026-survivor EU165 historical set; source-trained V2/V3 forecasts unchanged; 500 historical as-of baskets × 24 tickers, 6 macro-clusters, 4 each. Original V3 Top3 raw next Open, cost 10bp each side and mark-to-market NAV reconstructed against original immutable archive **max abs difference 4.44e-16**.

**Decision question:** Is weak 2021–24 CAGR due to V3 ranker, or to TopK/weights and the 500 constrained baskets?

**Matched 500 basket replay, 2021–24:** V3 Top3 8.174% CAGR, -25.775% MaxDD, 14.810× annual gross turnover; V3 Top1 9.217%/-24.744%/19.171×; Top2 8.702%/-26.344%; Top5 7.019%/-24.577%. V2 Leaves127 Top3 6.644%; V2 Titanium Top3 3.864%. Original score engine is entirely unmodified. V3 Top1 - Top3 annual log return diff +0.866 pp, monthly 6-month block 95% CI [-2.599,+4.224]pp — not significant.

**Different portfolio architecture (do not pretend identical):** Form **one** monthly portfolio from union of the 500 as-of eligible baskets, mean 115.48 ETF candidates actually with quotes and complete forecasts. V3 native Pair127 Top5 global portfolio 12.785% annual CAGR, -21.647% DD; V2 Titanium global Top3 10.988%, -23.268%; V3 global Top3 7.716%, -26.967%. V3 global Top5 averages **2.26 macro-clusters**, turnover **16.50× annually**, and does not guarantee true sector/factor diversification. Difference against mean of 500 overlapping V3 Top3 baskets 4.023 pp annualized log, 6-month month-block 95% CI [-2.416,+11.067] pp. **No statistically established gain** and different portfolio structure.

**Subperiod global V3 Top5**: 2021–22 CAGR +2.870%, 2023–24 +22.158%, 2025 +27.949%. This regime sensitivity undermines generalized superiority. Market risk overlay chosen as previously studied EXSA.DE Close<200d SMA using *past signal date only*, 50% cash with 0% cash interest, shifts global V3 Top5 from 12.785%/-21.647% to 12.814%/-19.026%; improvement in return negligible, downside moderate in sample, boot CI of log difference [-3.173,+3.442] pp/year.

**Buy-and-hold passive price-only controls 2021–24**: XMEU.DE (broad European equity) 9.256%/-19.298%; EXSA.DE 8.879%/-20.674%; SXR8.DE S&P500 UCITS EUR 17.639%/-17.104%. Note SXR8 is U.S. equity and NOT risk-exposure-matched European benchmark. Even global Top5 does not dominate SXR8 on the sample.

**Major limitations**: ETF universe curated in 2026 (survivorship), dividend/total return not certified, synthetic forward-filled prior closing marks, real spreads/slippage unknown, many prior tests on this exact span, global union vs 500 baskets structurally different and statistical units only months (46 pre-2025 returns), three calendar gaps with no forced trades (2022-01, 2025-01, 2026-01). P-values and block CIs exploratory. No source or production modifications.

Complete conversation reproducibility archive **ETF_TRADER_EU165_STRUTTURALE_TOPK_PANIERI_V3_20261029.zip** SHA256 **57881016253ed12efe853db3e4bfc42744e7eb950f5a0aac667f0f688c022b6d**, ~7.6 MB, contains 3 standalone code scripts plus scorecards, NAV, historical trades, month-block bootstrap, passive benchmark controls, plot and Italian report. Requires original EU165 frozen OHLCV / native trained forecast data from preceding archived ZIPs; these are not duplicated in 7.6MB artifact.

No production promotion. Next pivotal question is PIT real economic sector coverage and whether broad union selection with risk budget can produce reproducible *net of cost* advantage over XMEU, not merely cherry-picked CAGR, with another truly future unmined holdout.
