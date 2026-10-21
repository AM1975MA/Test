# V3 L04/01 — Frozen corrected Ranker + frozen Tail: information complementarity

**Date 21 October 2026. Completed, predeclared simple rank blends are NOT superior to the Tail specialist on the primary winner Top-3 criterion.**

[GitHub Actions successful 39659903643](https://github.com/AM1975MA/Test/actions/runs/39659903643), complete artifact **12372633250**. Earlier run 39659730735 failed due Pandas attribute shadowing (`DataFrame.tail` method vs "tail" prediction column); this was fixed without changing numerical conditions.

## Protocol and causal controls

- Frozen corrected-125 pairwise-127 expert OOS from 39652989033.
- Frozen Tail elite event classifier OOS from 39655513813.
- All 149 ETF/months, 500 original heavily overlapping 24-ETF baskets, same matured 21-trading-day future outcome, 101 months 2018–May2026.
- Entirely fixed score-level rank blends `50% ranker +50% tail` and `25% ranker +75% tail`, defined before seeing their performance. No supervised training or any changes to L01/L02/L03.
- Top-3 primary, Top-1, nDCG@3, opportunity regret, IC and expert overlap secondary. No CAGR.

## Outcome

| Metric | Ranker127 | Tail45 | Blend50 | Blend25/75 |
|---|---:|---:|---:|---:|
| Basket Top-1 capture | 14.552% | **17.511%** | 16.701% | 17.406% |
| Basket Top-3 capture | 35.471% | **42.747%** | 41.895% | 42.618% |
| Basket nDCG@3 | **0.542279** | 0.530565 | 0.541110 | 0.533860 |
| Basket 21D selected regret | **0.104115** | 0.107387 | 0.104984 | 0.106676 |
| Universe monthly rank IC | **0.038536** | 0.026447 | 0.036051 | 0.030935 |

Bootstrap paired calendar-month 6-month circular blocks, 6000 replications:
- Blend50 minus Tail Top-3 **−0.851 pp**, exploratory CI [−3.218,+1.824] pp; its nDCG@3 **+0.010545**, CI [+0.000620,+0.021395].
- Blend25/75 minus Tail Top-3 **−0.129 pp**, CI [−1.281,+1.099] pp; nDCG@3 **+0.003295**, CI [−0.001569,+0.008186].
- No fixed blend clears a positive winner-capture improvement. Do not promote.

## Quantified complementarity (per-basket winner Top-3 hit)

- Both experts capture the same winner: **23.024%**.
- Pairwise captures it exclusively: **12.448%**.
- Tail exclusively: **19.723%**.
- Neither: **44.806%**.
- Conditional upper bound of an oracle choosing either expert with perfect next-month foresight: **55.194%**; **unattainable ex ante without predictive signal** and should not be advertised as performance.
- Same-month rank-score Spearman correlation averaged **0.789533**.

## Next isolated L04 test

The missing benefit of a simple linear average argues for a *prequential supervised meta-ranker*, trained from historical first-stage OOS predictions with fully mature 21D labels; model inputs restricted to the two frozen expert percentile scores and a predeclared interaction. Evaluation must start only when enough past OOS expert/label pairs exist and compare paired Top-3 against static Tail and both fixed blends on the exact same later months. A separate "L04 meta" model is permitted; do not change L01, L02, regime L03 or risk/portfolio policy.

Historical data were repeatedly examined during research: all confidence intervals are exploratory, not a virgin out-of-time certification.
