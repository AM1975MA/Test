# Second pre-registered attempt: Adaptive Online Expert Weighting, Oct 19 2026

The first 16-method discovery/2024–26 split yielded original MA3 as the 2021–23 discovery winner; 2024–26 momentum21 /126 and Ridge36 look better only after looking at those outcomes. Never select those ex-post.

This new study compares strictly causal online weights rather than retroactive switching. All forecast source scores are already committed and immutable.

- ADAPT_4_CAUSAL combines ORIGINAL MA3, momentum21, momentum126, and Ridge last36. At each signal, only the last 12 monthly signals whose next-month exit date has already matured STRICTLY BEFORE the present signal may train expert weights. Monthly reward is 0.5 times signed cross-sectional Spearman plus 0.5 times Top5 future log excess divided by same-month cross-sectional standard deviation. Softmax inverse temperature 4, every expert receives minimum 10%; remaining 60% is proportional to softmax. Before six matured observations, equal 25% across experts.
- ADAPT_2_CAUSAL combines ORIGINAL MA3 and momentum21 using the same last12/matured reward. Floor 20% per expert; remaining 60% softmax. Before 6 historical periods, equal 50/50.
- STATIC_MA3_MOM21_50_50 and STATIC_MA3_RIDGE36_50_50 are non-adaptive benchmark mixtures with exactly equal score rank weights.
- Final score at each signal is a weighted average of within-month centered percentile ranks across the 48 ISIN ETFs. No category quotas, no future labels, no ETF turnover model features nor fund selection choices based on the already viewed 2024+ outcomes.
- 65 monthly 2021–2026 ETF source signals, 48 distinct ISIN, pre-2017 warmup. Evaluate absolute signed Spearman, Top5/Top2 next-month forward log return vs equal-weight 48 benchmark. Paired differences vs unchanged ORIGINAL MA3 using 3-month circular block bootstrap across monthly dates. Report all intervals, dev 2021–23 and exploratory 2024–26. Existing 2024–26 market sample already previously studied, so NOT truly pristine OOS.
- Each top5 ETF ISIN gets 20% funding, cash self-financing actual European daily Open-price shares using archived original source costed_path, 0.1% cost on buy and sell notional, no stops. Do not use CAGR as an optimization objective for predictor discovery. Reconciliation with source original output required.
- Not a claim of statistical significance from a single 65-month run, no overstatement, no mutation of production or ETF Trader V2 canonical baseline. All source results and SHA256 archived on Test branch.
