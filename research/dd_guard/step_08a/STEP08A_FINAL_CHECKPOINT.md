# STEP08A final checkpoint — 2026-08-31

## Verdict
`REJECT_BEFORE_2023_HOLDOUT`.

No structural defensive-reallocation variant passed the preregistered quality-jump gate on 2021–2022. The 2023+ holdout remains sealed.

## Development frontier vs frozen FUSION1
- BIL_FILL: ΔCAGR +0.00668 pp; Δmean MaxDD +0.00373 pp; Δp10 +0.00000 pp; Δworst-decile -0.00010 pp.
- TRIAD_TREND: ΔCAGR +0.00643 pp; Δmean MaxDD -0.04282 pp; Δp10 +0.00000 pp; Δworst-decile +0.02800 pp.
- LOWCORR_TOP3: ΔCAGR -0.17774 pp; Δmean MaxDD -0.04155 pp; Δp10 -0.06355 pp; Δworst-decile -0.07859 pp.
- LOWCORR_TOP3_SHIFT15: ΔCAGR -0.30525 pp; Δmean MaxDD -0.07492 pp; Δp10 -0.33675 pp; Δworst-decile -0.16916 pp.

## Interpretation
Replacing FUSION1 cash with a defensive sleeve does not materially improve the drawdown frontier. Basket-specific low-correlation selection is actually harmful on 2021–2022, especially in 2021. A fixed additional 15 pp shift from the risky sleeve also worsens both mean and left-tail drawdown despite keeping the CAGR concession within the preregistered -0.50 pp limit.

The only neutral result is BIL_FILL, whose changes are economically negligible. Therefore the evidence does not support further tuning of lookback, top-k, defensive universe, score coefficients, or shift size inside this lane.

## Computational implementation note
The final run replaced repeated `scipy.stats.rankdata` calls and row-wise low-eligibility fallback loops with vectorized NumPy operations. This was a computational optimization only. The frozen development panel has no exact within-row correlation ties, asserted at runtime, so the resulting correlation ranks are mathematically identical to `rankdata(method="average")`. Eligibility is common across baskets and is also asserted before the vectorized fallback. No scientific parameter or portfolio rule changed.

## Integrity
- FUSION1 parity max absolute gap: 0.0.
- Development window only: 2021-01-01 through 2022-12-31.
- 2023+ opened: NO.
