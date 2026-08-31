# STEP09A2 — Robust Escape Availability Target Audit Result

**Verdict: REJECT_STEP09A2_ROBUST_GEOMETRY_INSUFFICIENT.** 2023+ remains sealed.

STEP09A2 reuses the exact STEP09A geometry and full episodes but defines ROTATE only when at least 25% of the basket's non-BIL ETFs have full-episode utility above STAY. This removes the best-of-24 maximum bias.

Date-weighted class distribution:
- 2018-2020: STAY 51.92%, ROTATE 42.38%, BIL 5.71%; mean escape fraction 28.73%.
- 2021-2022: STAY 32.74%, ROTATE 47.49%, BIL 19.77%; mean escape fraction 25.33%.

Primary frozen geometry LOGIT forward 2021-2022:
- balanced accuracy: 0.439109 (gate 0.45; fail)
- macro OVR AUC: 0.614523
- STAY AUC: 0.461937
- ROTATE AUC: 0.703040
- BIL AUC: 0.678592
- predicted rates: STAY 45.51%, ROTATE 42.22%, BIL 12.27%.

2021 alone:
- balanced accuracy 0.487414
- macro AUC 0.682250
- ROTATE AUC 0.757161
- BIL AUC 0.787517.

2022 contains only 9 basket events on 2 market dates and is diagnostic only.

Pre-2021 LOO macro AUCs:
- 2018: 0.6900
- 2019: 0.9756
- 2020: 0.4737
- median valid: 0.6900.

All frozen information gates pass except combined balanced accuracy (0.4391 < 0.45). The gate is not bent and no 20/30% escape-fraction thresholds, class weights or C values are searched.

Scientific conclusion: robust escape topology contains genuine forward information, particularly for ROTATE-vs-BIL in 2021, but price geometry alone is not yet sufficient for promotion. The next admissible test adds genuinely orthogonal funding/liquidity information without changing the target or geometry.