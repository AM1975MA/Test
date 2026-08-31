# STEP08I — Small-Set Protective Selector

**Verdict: REJECT_BEFORE_2023_HOLDOUT.** 2023+ remains sealed.

## Development 2021–2022

| policy | CAGR | mean MaxDD | Sharpe | p10 MaxDD | p5 MaxDD | worst-decile | ΔCAGR pp | Δmean MaxDD pp | Δp10 pp | Δp5 pp | Δworst-decile pp |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| SMALLSET_PROTECTIVE_HGB | 19.919647% | -26.034472% | 0.738834 | -34.906970% | -40.094692% | -40.770731% | -0.496338 | +0.117584 | +0.906850 | -0.826737 | -0.092810 |

## Annual deltas vs FUSION1

| year | ΔCAGR pp | Δmean MaxDD pp | Δp10 pp | Δp5 pp | Δworst-decile pp |
|---:|---:|---:|---:|---:|---:|
| 2021 | -0.784316 | -0.290410 | -1.115181 | -0.831959 | -0.773268 |
| 2022 | -0.174373 | +0.406387 | +1.147610 | +0.933065 | +0.901863 |

## Mechanism

- Decisions: 1,124.
- STAY rate: 64.2349%.
- BIL rate: 23.9324%.
- ETF replacement rate: 11.8327%.
- Realized selected action beats exact FUSION1 event utility: 51.7794%.
- Exact small-set oracle hit rate: 32.4733%.
- Small-set oracle STAY rate: 39.6797%.

## Gate

The preregistered gate fails because mean MaxDD improves only +0.117584 pp (< +0.50 pp), worst-decile is slightly negative, and 2021 mean MaxDD is -0.290410 pp vs FUSION1. CAGR (-0.496338 pp) is just inside the permitted -0.50 pp concession and p10 passes strongly (+0.906850 pp).

No 2023+ outcomes were opened. No post-result tuning was used for the official result.
