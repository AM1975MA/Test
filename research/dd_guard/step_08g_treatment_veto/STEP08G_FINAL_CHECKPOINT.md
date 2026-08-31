# STEP08G final checkpoint

- Verdict: **REJECT_BEFORE_2023_HOLDOUT**
- Validation replay parity with STEP08F: **CORRECTED / EXACT**
- Frozen treatment model/actions changed after result: **NO**
- 2023+ opened: **NO**
- Frozen STEP08F alpha challenger preserved separately.
- No post-result tuning.

## Key result vs FUSION1, 2021–2022
- ΔCAGR: **-0.790293 pp**
- Δmean MaxDD: **-0.354431 pp**
- Δp10 MaxDD: **-0.482474 pp**
- Δworst-decile MaxDD: **-0.628451 pp**

## Action distribution
- STAY: **83.452%**
- BIL: **16.281%**
- ETF: **0.267%**

The zero-threshold HGB treatment gate rejects almost every event-time Titanium proposal and sends a material subset to BIL. Those non-STAY interventions beat exact FUSION1 utility only 28.495% of the time. The gate therefore destroys the STEP08F alpha improvement without repairing the DD frontier.
