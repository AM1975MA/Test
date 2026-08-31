# STEP08C C1 implementation freeze — after oracle, before causal selector

The preregistered C0 oracle gate passed, so C1 is authorized. No causal-selector result has been inspected.

## Fixed estimator
`SimpleImputer(median) -> StandardScaler -> Ridge(alpha=10.0)`.
No alpha grid or model-family comparison is permitted.

## Training balancing
The full pre-2021 adaptive-stress panel contains many baskets on the same market date. To prevent calendar-time pseudo-replication and keep the cross-sectional training matrix tractable, at most 10 basket states are retained per training date, deterministically by sorted basket id and evenly spaced positions when more than 10 are present. This selection is independent of future outcomes.
Each retained market date receives equal total training weight; within a date weight is divided equally across retained basket states and candidate ETFs.

## Candidate target and eligibility
Target = candidate 10-session robust utility minus BIL 10-session robust utility, both net of 10 bp entry + 10 bp exit. Only labels fully matured by 2020-12-31 are admitted.
At validation, the current monthly leader and satellite are excluded when identifiable. BIL is not ranked as a risky candidate: if the maximum predicted advantage among non-BIL ETFs is <= 0, destination is BIL.

## Features
Exactly the protocol feature families are used. No feature selection is performed after validation results.
