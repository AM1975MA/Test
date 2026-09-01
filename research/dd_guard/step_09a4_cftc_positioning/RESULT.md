# STEP09A4 — CFTC Positioning Topology Audit

**Verdict: REJECT_STEP09A4_CFTC_POSITIONING_INSUFFICIENT.** 2023+ opened: **NO**.

## Mandatory parity
- max absolute metric difference vs STEP09A2: **0.000e+00**

## Forward comparison

| feature_set | balanced_accuracy | macro_auc | auc_stay | auc_rotate | auc_bil |
|---|---:|---:|---:|---:|---:|
| GEOMETRY | 0.439109 | 0.614523 | 0.461937 | 0.703040 | 0.678592 |
| GEOMETRY_PLUS_CFTC | 0.406368 | 0.615852 | 0.448780 | 0.719582 | 0.679195 |

2021 GEOMETRY_PLUS_CFTC: balanced accuracy 0.445600, macro AUC 0.677319, ROTATE AUC 0.785717, BIL AUC 0.759836.

## Incremental vs geometry
- balanced accuracy: **-0.032742**
- macro AUC: **+0.001329**
- STAY AUC: **-0.013157**
- ROTATE AUC: **+0.016542**
- BIL AUC: **+0.000603**

## Gate
The unchanged STEP09A2 gate fails because forward balanced accuracy is below 0.45. All other principal AUC/robustness checks pass, including the incremental macro-AUC safeguard.

CFTC coverage: 42 reports, median report age at trigger 9 days. No contract, feature subset, lag, threshold or model was changed after observing the result.
