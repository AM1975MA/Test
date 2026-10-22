# ETF Trader V3 L10 — Ordinal pairwise mistakes at the top of the investment ranking

**Protocol fixed 22 October 2026, before reading any L10 outcome.** Research branch `research-v3-l10-topk-riskpair-20261022`. Original production V2 and selected V3 reference frozen. Historical 2018–2026 years reused many times; results are exploratory, NOT a virgin OOS holdout.

## Purpose and sequence

L09 showed that reducing absolute large-loss exposure via 21D regression sacrificed actual extreme future winners and portfolio performance. Retain the original **rank:pairwise** ordinal learning objective, 125 corrected input features, 127 leaves, 360 trees, 3 seeds and maturity-safe annual walk-forward. Examine in **two consecutive one-change contrasts** whether top-selection errors can be prioritized and then whether the same pairwise model can learn to treat absolute losses worse than -10% as the worst category. No CAGR-based tuning and no changes to future execution rules.

### Step 0 — Original frozen baseline

`CORRECTED` from Actions run **39515716383**, exact immutable out-of-year predictions with original pairwise labels `round(100 * future 21-trading-day ETF cross-universe percentile rank)`, default XGBoost pair construction, ranking params from `v3.COMPACT_PARAMS`. All prediction dates, ticker identifiers, future labels and 500 original 24-ETF baskets must be identical.

### Step A — Pair sampling only

`L10_TOP5_PAIR127`: **same original ordinal future21D rank label** and objective `rank:pairwise`, only pair construction explicitly `lambdarank_pair_method='topk', lambdarank_num_pair_per_sample=5`. In XGBoost 3.0 topk is a dynamic selection of high-predicted-score documents. No change to loss function, population, feature set, seeds or tree limits. Compare A against original `CORRECTED`.

### Step B — Cost-sensitive ordered-relevance labels only

`L10_TOP5_RISKTIER127`: same topk5 sampling and all parameters as A, **change only mature TRAINING labels** to integer tiers 0–4:

- tier 0: realized next-open +21 trading-day return **≤−10%**, regardless of its relative cross-sectional rank (including broad crash months);
- tier 1: non-catastrophic ETF but relative future return percentile ≤25%;
- tier 2: non-catastrophic ETF, percentile (25%,75%];
- tier 3: non-catastrophic ETF, percentile (75%,90%];
- tier 4: non-catastrophic ETF, percentile >90%.

This **truly changes pair preference and the set of tied examples**, unlike a monotonic transformation of continuous future returns that would preserve every `rank:pairwise` comparison. Labels are calculated only for training months whose observed 21-trading-day exit is strictly before the Jan1 model-refit cutoff. The future target is NEVER a contemporaneous input feature.

Important caveat: this label design intentionally reorders relatively high performers in crash months if their absolute loss exceeds 10%, so possible alpha sacrificed must be measured explicitly. Compare B against A to attribute the effect to risk-tier training, and both against original.

## Data, outcomes and trust gates

Exactly original 149 ETFs, identical fixed canonical **500 baskets of 24 ETFs**, original CSV SHA `36a45916b5d8191f3ccd206f39bf3fd3f1ed4bcaffd474e352b69c598f2b6a5e`, validated source [39482809691](https://github.com/AM1975MA/Test/actions/runs/39482809691), 125 correctly reconstructed source features, annual refits from 2018–2026, 101 maturity-complete monthly future21D evaluation dates.

Intrinsic prediction gate first: basket Top-1 and Top-3 future-best hit rate, basket nDCG@3, realized selected future ordinal rank, universe rank IC, actual next21D regret. Top2/Top3 **portfolio functional gate separately**: amount of capital committed to eventual absolute ETF loss <=−10%, eventual best ETF winner weight, basket bottom-three weight, actual selected mean rank, regret. Evaluate calendar-month blocks because baskets overlap, never 500 baskets as independent observations.

Only after these score streams are frozen, run an **economic consequence diagnostic** with identical original source-only LEGACY, CORRECTED, L10_TOP5 and L10_RISKTIER predictors under both existing **Top2 old gap rule** and **Top3 weights 50/30/20**, actual next-session adjusted-Open execution, fee 10bps traded notional, daily mark, calendar block bootstrap. Do not choose any coefficient or policy on explored CAGR. Cost of trading, Sharpe and drawdown are outputs, not training targets.

## Promotion rule

Do not promote an improvement on global Spearman IC alone; require economically task-aligned future Top-3/selected-rank and downside improvements without meaningful collapse of winner weight or severe increase in regret. Numerical and statistical evidence should be repeated on genuinely newer never-used data before approving any live release. A negative result is persisted alongside the code, runs and exact provenance in the central V3 ledger.

Engineering note: xgboost 3.0.5 documents `lambdarank_pair_method=topk` and the truncation parameter `lambdarank_num_pair_per_sample`; this changes pair sampling but not the fundamental objective `rank:pairwise`.
