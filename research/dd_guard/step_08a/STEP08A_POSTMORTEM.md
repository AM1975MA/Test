# STEP08A post-mortem — structural interpretation

## Key exposure fact
Across the 2021–2022 development panel, frozen FUSION1 is active on only **2.9046% of basket-days**. Mean residual/cash weight is **1.9755%** over all basket-days, but conditional on an active FUSION1 state the mean residual weight is **68.0151%**.

This explains the structural ceiling of a cash-fill-only overlay: the overlay has a large allocation only on a small fraction of observations, while FUSION1 already removes most risky exposure on those observations.

## LOWCORR defensive mix actually used
Residual-weighted 2021–2022 LOWCORR mix was led by BIL (20.31%), SCHP (19.61%), TIP (12.91%), SHV (10.61%), IAU (6.56%), VGSH (6.09%) and GLD (5.21%).

The regime split was unstable:
- 2021: SCHP 29.52%, TIP 19.87%, SHV 11.20%, VGSH 9.72% dominated.
- 2022: BIL 47.43%, IAU 14.54%, GLD 12.66%, SHV 9.64% dominated.

Despite causal low-correlation/momentum/volatility selection, the basket-specific sleeve worsened both mean and left-tail drawdown versus cash-backed FUSION1 on the full development period. The fixed SHIFT15 made the result worse, especially in 2021.

## Research implication
The evidence rejects **stress-only defensive substitution inside the existing FUSION1 windows** as a quality-jump mechanism. If structural portfolio research continues, it should alter the portfolio *before* the FUSION1 trigger: e.g. a persistent diversifying sleeve or different core portfolio construction, rather than optimizing which defensive asset receives already-cut cash during the rare stress windows.
