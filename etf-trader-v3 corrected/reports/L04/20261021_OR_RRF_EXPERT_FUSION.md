# V3 L04.3 — disjoint-winner expert aggregation

**21 October 2026, completed; neither candidate promoted.** Frozen scores from ranker and Tail [original paired run 39659903643](https://github.com/AM1975MA/Test/actions/runs/39659903643), same 101 mature signal months, 500 canonical baskets; no new training, CAGR, regime or risk.

[Successful L04 test 39674361027](https://github.com/AM1975MA/Test/actions/runs/39674361027), artifact **12381350315**.

Two a priori aggregations:
- `OR_MAX`: max of the two same-month frozen cross-universe expert percentile scores (an attempt to retain independent expert winners).
- `RRF_K10`: reciprocal rank fusion `1/(10+rank_Pair)+1/(10+rank_Tail)` (k=10 predeclared, no OOS tuning).

| Metric | Tail only | Prior arithmetic 50/50 | OR max | RRF k=10 |
|---|---:|---:|---:|---:|
| Basket Top-3 | **42.7465%** | 41.8950% | 41.8950% | 42.5604% |
| Basket nDCG@3 | 0.530565 | **0.541014** | 0.534695 | 0.539113 |
| Mean selected regret (next21D) | 0.107387 | 0.105028 | 0.105707 | 0.105175 |
| Basket Top-1 | **17.5109%** | 16.6950% | 16.7366% | 17.1960% |

RRF minus frozen Tail Top-3 **−0.186 pp**, paired 6-month calendar-block 95% CI **[−2.295,+2.263]** pp. RRF nDCG +0.00855, CI [−0.00127,+0.01875]. OR minus Tail Top-3 −0.851 pp, CI [−3.022,+1.543] pp. Neither demonstrates positive upper-winner capture with adequate consistency. **Reject promotion**, keep original Tail for the primary Top-3 task and pairwise ranker independently for regret/general ranking.

All samples are previously explored OOS history, not independent virgin holdout.
