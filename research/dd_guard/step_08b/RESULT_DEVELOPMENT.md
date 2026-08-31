# STEP08B — development result

**Verdict: REJECT_BEFORE_2023_HOLDOUT.**

2023+ holdout opened: **NO**. FUSION1 parity gaps: engine `0.000e+00`, w=0 portfolio accounting `0.000e+00`.

## Eligible persistent variants

| Variant | ΔCAGR | Δmean MaxDD | Δp10 | Δworst-decile | mean diversifier | gate |
|---|---:|---:|---:|---:|---:|:---:|
| PERSIST_TRIO10_SYS20 | -2.772 pp | +2.488 pp | +3.290 pp | +3.571 pp | 11.61% | FAIL |
| PERSIST_BIL10 | -1.765 pp | +2.415 pp | +3.237 pp | +3.472 pp | 10.00% | FAIL |
| PERSIST_TRIAD_TREND10 | -1.829 pp | +2.201 pp | +2.845 pp | +3.221 pp | 10.00% | FAIL |
| PERSIST_TRIO10 | -2.309 pp | +2.103 pp | +2.860 pp | +3.142 pp | 10.00% | FAIL |

## Static BIL/IEF/GLD frontier (diagnostic only)

| Weight | ΔCAGR | Δmean MaxDD | Δp10 | CAGR guard | joint pointwise gate |
|---:|---:|---:|---:|:---:|:---:|
| 0% | +0.000 pp | +0.000 pp | +0.000 pp | YES | NO |
| 5% | -1.150 pp | +1.050 pp | +1.441 pp | NO | NO |
| 10% | -2.309 pp | +2.103 pp | +2.860 pp | NO | NO |
| 15% | -3.479 pp | +3.160 pp | +4.170 pp | NO | NO |
| 20% | -4.658 pp | +4.218 pp | +5.585 pp | NO | NO |
| 25% | -5.846 pp | +5.277 pp | +7.069 pp | NO | NO |
| 30% | -7.043 pp | +6.337 pp | +8.720 pp | NO | NO |

No persistent weight, systemic threshold, trio constituent, or trend lookback is retuned after these results.
