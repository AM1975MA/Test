# Original149 TCN listwise objective ablation — frozen protocol (2026-10-20)

**Goal:** test whether grouping ETF predictions by same signal date and optimizing rankings jointly improves positive future Top5 selection relative to already executed Pointwise TCN 30×125, Ridge125 and past21 momentum. Research branch only: research/original149-tcn-listwise-20261020. No production changes or post-hoc hyperparameter search.

## Data integrity and unchanged model
- Exactly 149 adjusted OHLCV Yahoo frozen CSVs in evidence_v1/data/original149/ with SHA manifest gate; original roster SHA 7bccf1b756bf3652280a254c7486fb43f1e805ebb4cdf10731cecc74007292e6.
- All 125 *daily* Compact21 features with exact monthly canonical parity; (ETF,30 sessions,125 features). Original TinyTCN architecture, seed 20261020, 24 channels, 35% dropout, learning rate .001, weight decay .003, maximum 5 epochs, patience 2. No changes to parameter budget.
- Train-only feature normalization and missingness; one signal date per Listwise group, ETF ordering stable; valid 30-day history. At signal close t, returns Open(t+6)/Open(t+1)-1. Fixed five-session spaced decision grid. Train label maturity before Jan 1 (Y−1) and validation maturity before Jan 1 Y for test Y, as in pointwise.
- Same 149-ETF as-of eligibility and signal dates, 5-session next-open Top5 equally weighted strategy with 10 bp one-way commission each full rebalance; full 20 bp round trip every week. No leverage. No beta-neutralization claim.

## Three prespecified training objectives
1. LISTNET_ALL: true **date-grouped** ListNet top-one probability cross-entropy, target softmax(3.5×future rank in [-1,+1]); logits raw TCN scores. Optimizes full cross-sectional distribution, all ETF groups.
2. LISTMLE_TOP5: genuine **date-grouped Top5 listwise** Plackett–Luce negative log likelihood of realized five top-ranked ETFs, each selected from full ETF group; discounts 1/log2(k+2) over k=0..4. Unlike ApproxNDCG/LambdaLoss this is a genuine Plackett–Luce ListMLE@5 surrogate; not an exact NDCG gradient.
3. LISTNET_RETURN_HYBRID: LISTNET_ALL + 0.30 SmoothL1 of predicted score vs forward five-day return minus same-date median, scaled by max(q90-q10,1e-5), bounded ±3. Uses only matured forward outcomes as training labels. No future returns as input.

All objectives backpropagate groupwise. Each gradient step accumulates 4 randomly shuffled temporal groups before AdamW update; never mix groups inside loss. Epoch validation uses the same groupwise criterion, not backtest CAGR. Save all fitted model checkpoints (one per year), entire ETF score vectors, per-week selections, daily open-to-open wealth and per-year training/validation manifests.

## Comparison
First fast reliability pilot 2024–2025, 100 identical frozen decision dates; following this apply same unchanged recipe to annual 2017–2026 folds and compare with frozen completed original Pointwise run 39455244701. Metrics: weekly equally-date-weighted RankIC, future realized Top1 rank percentile, true Top5 overlap, future top-decile return regret, costed CAGR, maximum drawdown, Sharpe and selected/realized five-day returns. Demand comparable date counts and matched eligibility; group loss alone does not establish superiority. Full-period retrospective evidence is in-sample *research*, not prospective evidence: these 149 survivor-based ETFs and market regimes have been examined previously.

Two critical limitations: proxy adjusted open prices do not represent actual spreads, and rank target only subtracts cross-sectional market trend; it does not neutralize beta or other risks. No model qualifies for production from this experiment alone.
