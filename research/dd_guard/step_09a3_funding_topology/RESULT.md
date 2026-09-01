# STEP09A3 — Reserve-Balance Funding Topology Audit

**Verdict: REJECT_STEP09A3_FUNDING_INSUFFICIENT.** 2023+ opened: **NO**.

Mandatory geometry parity passed with max absolute metric difference **5.55e-17**.

Forward 2021–2022, frozen LOGIT:
- GEOMETRY: balanced accuracy 0.439109; macro AUC 0.614523; ROTATE AUC 0.703040; BIL AUC 0.678592.
- GEOMETRY_PLUS_WRESBAL: balanced accuracy 0.431695; macro AUC 0.602757; ROTATE AUC 0.675060; BIL AUC 0.684594.

Incremental vs geometry:
- balanced accuracy **-0.007415**
- macro AUC **-0.011766**
- ROTATE AUC **-0.027980**
- BIL AUC **+0.006001**

2021 augmented macro AUC = 0.656740, balanced accuracy = 0.481499. The combined gate fails on forward balanced accuracy and the preregistered non-degradation condition for macro AUC. No alternative WRESBAL windows, lags, transformations, model parameters, or thresholds were tested.

Conclusion: reserve-balance plumbing does not add useful incremental information to the robust escape-topology geometry. Proceed to genuinely orthogonal positioning/flow information rather than funding-window tuning.