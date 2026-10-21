# V3 L05 — allocation quality, budget, concentration and churn, without CAGR

**21 October 2026: completed source-only layer experiment. Candidate: fixed Top-3 50/30/20, not a statistically established predictor improvement.**

Successful [GitHub Actions run 39661273577](https://github.com/AM1975MA/Test/actions/runs/39661273577), complete artifact **12373642646**.

## Protocol

Frozen, already chronological OOS Tail45 elite scores from 39655513813 via L04 artifact 39659903643. All 149 original ETFs, 500 canonical baskets, **101 monthly 21D-mature labels**. No change to L00-L04, no macro gate, financial risk overlay, optimization to future returns or CAGR.

Four predeclared fixed policies: V2-like 75% first/25% second except score gap≥0.12 then 100% first; Top1 100%; Top3 equal; Top3 decay [50%,30%,20%].

The layer's functional metrics are weighted *within-basket future percentile rank* of chosen ETFs, weighted regret versus the best ETF, weight accidentally allocated to the future bottom 3, diversification/effective number of holdings, target-weight selection churn. **Target-weight churn is NOT actual trading turnover inclusive of price drift and market execution.**

| Metric | V2-like | Top1 | Top3 50/30/20 | Top3 equal |
|---|---:|---:|---:|---:|
| Weighted within-basket realized rank quality (0 worst, 1 best) | **0.513263** | 0.513328 | 0.512941 | 0.512789 |
| Weight invested in basket's 3 worst forward-21D ETFs | 28.005% | 28.618% | 26.695% | **25.879%** |
| Target weight churn per month | 0.473985 | 0.534960 | 0.383364 | **0.325860** |
| Effective number of positions | 1.5779 | 1.0000 | 2.6316 | **3.0000** |
| Mean maximum position weight | 75.921% | 100% | 50% | **33.33%** |
| Weight invested in future basket best ETF | **16.789%** | 17.511% | 15.218% | 14.249% |
| Weighted best-ETF regret (fractional return) | 0.107264 | 0.107387 | 0.107137 | 0.107043 |

Paired calendar-month six-month block bootstrap (6000 reps), Top3-decay minus original V2-like:
- Weighted realized rank quality **−0.000322**, 95% CI [−0.006109,+0.005436] (no established advantage or inferiority).
- Bottom-three weight **−1.310 pp**, CI [−1.846,−0.795] pp.
- Target weight churn **−0.090621**, CI [−0.098676,−0.082319].
- Weight on future winner **−1.571 pp**, CI [−2.149,−0.973] pp.
- Regret **−0.0001264**, CI [−0.001740,+0.001439] (undetermined).
The extra diversification naturally reduces concentration on *both* realized losers and winners; this is a trade-off, not free alpha.

## Layer decision

Keep **Top3 50/30/20 as candidate L05** because it reduces concentration and churn substantially with essentially unchanged *observed average selected rank quality*; retain V2-like as immutable comparator. The allocation is not production-approved. These historical months have been used in prior research and do not constitute an untouched evaluation.

For L06, apply a model of future large losers using scores available on the decision date and compare risk-event recall/false alarm and missed winners at a *fixed* Top3-decay policy (alongside original policy reference), without changing ranker, Tail or adaptive regime.
