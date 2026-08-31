# STEP08E2 — correlation-aware basket-local protective rotation

**Verdict: REJECT_BEFORE_2023_HOLDOUT_PROCEED_STEP08F.** 2023+ remains sealed.

## Development 2021–2022

| policy | ΔCAGR vs FUSION1 | Δmean MaxDD | Δp10 | Δworst-decile | gate |
|---|---:|---:|---:|---:|:---:|
| INV_CORR_MIN | -3.811 pp | -1.320 pp | -1.086 pp | -1.926 pp | FAIL |
| INV_DOWNSIDE_BETA_MIN | -1.626 pp | -0.872 pp | -1.291 pp | -1.475 pp | FAIL |
| NEG_DOWNSIDE_THEN_TITR | -0.785 pp | -0.438 pp | -0.704 pp | -0.964 pp | FAIL |

## Annual deltas

`NEG_DOWNSIDE_THEN_TITR`, the preregistered primary structural test, remains negative in 2021: ΔCAGR -1.220 pp, Δmean MaxDD -0.716 pp, Δp10 -2.102 pp. In 2022 it is nearly neutral on CAGR (-0.125 pp) and slightly positive on mean MaxDD (+0.018 pp), but this does not rescue temporal replication.

## Mechanism

- Pure minimum correlation selected a negative-correlation destination on 76.1% of non-BIL decisions, yet beat exact FUSION1 event utility only 35.3% of the time.
- Minimum downside beta produced mean selected downside beta -0.192 and beat BIL 53.0% of events, but still worsened portfolio MaxDD and CAGR.
- `NEG_DOWNSIDE_THEN_TITR` used BIL on 8.90% of decisions, enforced downside beta <= 0 on every non-BIL choice, and beat FUSION1 event utility 45.8% of the time. It still worsened the global DD frontier.
- All three policies are materially worse than STEP08E pure basket-local TIT_R on mean MaxDD and p10.

No post-hoc tuning was performed. Per the preregistered protocol, research proceeds to STEP08F event-time Titanium ranking.
