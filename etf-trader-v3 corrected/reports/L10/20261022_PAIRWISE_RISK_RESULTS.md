# ETF Trader V3 L10 — cost-sensitive pairwise ranking, complete and rejected as standalone

**22 October 2026 — successful experimental 101-month OOS test and fee-aware daily economic replay.** The original V2 production system and frozen V3 model references are unchanged.

Completed [prediction workflow 39700865721](https://github.com/AM1975MA/Test/actions/runs/39700865721), artifact ID **12392758288**, and [economic workflow 39701813167](https://github.com/AM1975MA/Test/actions/runs/39701813167), artifact ID **12393515838**. See [preregistered study](./20261022_PAIRWISE_RISK_PROTOCOL.md), [train code](../../experiments/l10_pairwise_risk/evaluate.py), [intrinsic aggregation](../../experiments/l10_pairwise_risk/aggregate.py), [matched functional allocation](../../experiments/l10_pairwise_risk/functional.py) and [economic replay](../../experiments/l10_pairwise_risk/economic.py).

## Controlled interventions and causal limits

Frozen original corrected125 `rank:pairwise` XGB127 (360 estimators, 3 seeds, yearly mature-only future21D label training) from run **39515716383**, original 149 ETF adjusted OHLCV run **39482809691**, 500 fixed canonical 24-name baskets, 101 fully matured monthly OOS evaluation dates.

- **A: `L10_TOP5_PAIR127`:** original ordinal future 21D cross-universe rank label and same pairwise objective, but dynamic predicted Top-5 pair construction (`lambdarank_pair_method=topk, num_pair_per_sample=5`) instead of original default Top-1.
- **B: `L10_TOP5_RISKTIER127`:** same Top-5 pair construction, replace training label with ordered integer tiers `0: future absolute ETF next21D loss ≤−10%; 1: remaining future rank ≤25th percentile; 2: up to 75th; 3: up to 90th; 4: top decile`. Explicit ordering and ties truly change pair comparisons — unlike monotonically transforming future return labels, which would not change `rank:pairwise` preferences.
- Both labels are available **only after maturity of historical training rows** before each Jan1 annual cutoff, never as inference features. No L02 Tail, L03 RMT/macro, L04 score fusion, L05 allocation optimization, risk veto or CAGR-tuned hyperparameters in the model training.

## Intrinsic ranking result, 101 OOS months, 500 overlapping baskets

| Metric | Frozen corrected pairwise127 | Top-5 original rank | Top-5 with severe-loss tiers |
|---|---:|---:|---:|
| Basket future winner included in Top3 | 35.4713% | **42.3465%** | 37.7089% |
| Basket future winner in Top1 | 14.5525% | **16.7267%** | 15.2574% |
| Mean basket nDCG@3 | **0.542279** | 0.528815 | 0.539545 |
| Mean 21D Top1 oracle regret | **0.104115** | 0.111145 | 0.107476 |
| Universe Spearman IC | **0.038536** | 0.011502 | 0.015876 |
| Basket top1 selected return in excess of basket average | **0.007122** | 0.000092 | 0.003761 |

Paired bootstrap, calendar-month circular 6-month blocks, 6000 replications, 500 baskets averaged within each month first:
- A vs original **Top3 +0.068752**, exploratory 95% CI **[+0.037504,+0.099802]**, Holm-adjusted p <0.001.
- A vs original **Top1 21D regret +0.007030**, 95% CI **[+0.001672,+0.012673]** (worse), exploratory Holm p≈0.032.
- A vs original Spearman IC **−0.027033**, 95% CI [−0.043932,−0.010457].
- B vs original Top3 +0.022376 CI **[−0.009782,+0.053822]**, not established.
- B vs original regret +0.003361 CI [−0.002061,+0.008906], no established improvement.

**Task specialization, not Pareto improvement:** Top-5 increases how often at least one huge winner appears in the top three, but its other selected ETF positions are sufficiently inferior that Top1 regret, IC, average rank and downside worsen.

## Isolated investor-position selection with original fixed Top3 50/30/20

All same ETF universes and future outcomes, no risk overlay or ex-post ticker substitutions.

| Functional metric, 101 OOS months | Original corrected127 | Top-5 | Top-5 + risk tiers |
|---|---:|---:|---:|
| Actual future basket-best ETF's invested weight | 12.5818% | **14.9594%** | 13.3764% |
| Weight on realized ETF future21D absolute loss ≥10% | **8.4861%** | 10.9297% | 9.5883% |
| Weight on realized worst-three ETFs of 24 | **22.1313%** | 26.9018% | 24.2505% |
| Average realized invested ETF percentile-rank quality | **0.524852** | 0.510642 | 0.521732 |
| Average weighted regret vs future basket-best ETF | **0.105470** | 0.108084 | 0.107101 |

Top-5 minus baseline: severe-loss capital weight **+2.4436 percentage points**, calendar-block CI **[+1.6406,+3.2202] pp**; winner weight **+2.3776 pp**, CI [+1.1943,+3.5351] pp. Adding risk-tier to Top-5 reduces severe loss exposure by **1.3414 pp** (CI [−2.1018,−0.6009] pp), but also reduces winner weight by **1.5830 pp** (CI [−2.5606,−0.6969] pp). Risk-tier remains worse than original baseline on absolute-loss weight by **+1.1022 pp** (CI [+0.3093,+1.8977] pp). This is **not** a superior safety head or alpha head for investment selection.

## True self-financing 10bp execution, source-only V2 oracle parity

All alternatives use same next-open execution, daily adjusted-open marks and turnover-based fees; baseline original independent LEGACY Top2 replay exact to absolute 1e−10. Full scores use 2018–July2026, common recent Feb2022–July2026.

| Candidate with fixed Top3 | Aggregate basket-capital CAGR 2018–2026 | Aggregate CAGR 2022–2026 | Recent aggregate MaxDD | Recent mean basket Sharpe |
|---|---:|---:|---:|---:|
| Original CORRECTED pairwise127 | **13.883%** | 17.777% | −19.457% | **0.679** |
| L10 Top-5 | 11.080% | 17.165% | **−19.076%** | 0.623 |
| L10 Top-5 with risk tiers | 11.156% | **18.090%** | −19.901% | 0.670 |

With original **Top2 policy**, 2018–26 aggregate CAGR original corrected **14.729%**, Top-5 **9.877%**, Top-5 with risk tiers **10.537%**; 2022–26 CAGR 19.634%,16.190%,18.421%.

Paired 21-business-day calendar-block bootstrap (1500 draws; basket log returns aggregated before resampling), recent Top3 L10 RiskTiers minus original corrected annual log return delta **+0.00602**, exploratory 95% CI **[−0.04851,+0.05555]**. No demonstrated improvement in returns, and older years show economic degradation. Recent Top3 Top-5 original pair vs corrected delta **−0.00907**, CI [−0.07138,+0.05247].

## Final decision and future research hypothesis

**DO NOT PROMOTE L10_TOP5_PAIR127 or L10_TOP5_RISKTIER127 as standalone investable rankers.** The sample reveals a genuine useful **candidate-retrieval property** of the Top-5 pair model — more future basket-best ETFs are included — but the same candidate list also increases absolute large-loss exposure and lowers portfolio quality. This is an intriguing *complementary expert* property, not a proven profitable layer.

The next logically isolated research experiment (not executed or promoted here): freeze ORIGINAL corrected pairwise as the **final buy-order/risk-quality head**, and allow the Top-5 model only to propose additional names for assessment (training-only predeclared candidate-pool/confirmation rule). Evaluate whether this increases realized winner discovery **without replacing the low-downside filtering of the original ranker**. Do not blend 50/50 or rerank based on hindsight in already examined years.

**No virgin independent future test exists; all 2018–26 calendar outcomes have been used repeatedly during research. The experimental intervals and backtest comparisons are descriptive. No V2 deployment or automatic trading change.**
