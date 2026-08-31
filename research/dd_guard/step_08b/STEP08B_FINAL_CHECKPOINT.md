# STEP08B final checkpoint — 2026-08-31

## Verdict
`REJECT_BEFORE_2023_HOLDOUT`.

2023+ remains sealed. FUSION1 parity is exact both through the frozen engine and through the STEP08B zero-diversifier portfolio accounting (max absolute gap 0.0).

## Development 2021–2022 versus frozen FUSION1
- PERSIST_BIL10: ΔCAGR -1.76459 pp; Δmean MaxDD +2.41461 pp; Δp10 +3.23657 pp; Δworst-decile +3.47161 pp.
- PERSIST_TRIO10: ΔCAGR -2.30942 pp; Δmean MaxDD +2.10259 pp; Δp10 +2.86010 pp; Δworst-decile +3.14163 pp.
- PERSIST_TRIAD_TREND10: ΔCAGR -1.82907 pp; Δmean MaxDD +2.20109 pp; Δp10 +2.84516 pp; Δworst-decile +3.22058 pp.
- PERSIST_TRIO10_SYS20: ΔCAGR -2.77162 pp; Δmean MaxDD +2.48793 pp; Δp10 +3.28992 pp; Δworst-decile +3.57111 pp.

No eligible variant passes because every nonzero persistent allocation breaches the frozen CAGR guard (-0.50 pp), despite strong and annually replicated MaxDD improvement.

## Static fixed-trio diagnostic
0/5/10/15/20/25/30% BIL-IEF-GLD weights show a monotone protection/return tradeoff. At 5%: ΔCAGR -1.14951 pp, Δmean MaxDD +1.04951 pp, Δp10 +1.44105 pp. At 30%: ΔCAGR -7.04285 pp, Δmean MaxDD +6.33714 pp, Δp10 +8.71966 pp.

## Stop-rule interpretation
Close the persistent defensive-sleeve lane. Do not retune smaller weights or constituent/threshold choices. If DD research continues, move to risk budgeting inside the alpha portfolio rather than defensive capital extraction.
