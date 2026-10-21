# V3 L01.2 — fixed 127-leaf ranker, regularization lambda 8 → 16

**21 October 2026, completed; candidate NOT promoted.** [GitHub Actions success 39675577723](https://github.com/AM1975MA/Test/actions/runs/39675577723), completed artifact **12382386873**. Corrected125 feature/149 ETF schema, 500 canonical 24-ETF baskets; same 101 fully mature chronological OOS months, annual refits, 360 rounds, 127 leaves, 3 ensemble seeds, unchanged pairwise objective. **Only lambda changed from baseline 8 to 16.** No CAGR.

| Intrinsic rank task | Frozen lambda=8 | Lambda=16 |
|---|---:|---:|
| Basket Top-3 actual winner | **35.4713%** | 34.3881% |
| Basket Top-1 actual winner | **14.5525%** | 14.4792% |
| Basket nDCG@3 | **0.542279** | 0.538769 |
| Universe Spearman rank IC | **0.038536** | 0.037699 |
| Mean 21D selected regret | 0.104115 | **0.103917** |

Paired calendar-month 6-month circular bootstrap Top-3 difference (candidate minus original) **−1.083 percentage points**, 95% interval **[−2.400,+0.164] pp**. Regret difference −0.000198, interval [−0.002114,+0.001712], not meaningful. **Decision: keep frozen lambda=8 pairwise127**. This small, plausible strengthening of regularization provides no robust winner-capture improvement, so no promotion.

Historical years already examined extensively; bootstrap intervals are exploratory. Original live V2 remains untouched.
