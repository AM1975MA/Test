# STEP09A — Escape Topology Audit Result

**Verdict: REJECT_STEP09A_GEOMETRY_INSUFFICIENT.** 2023+ remains sealed.

The first full-episode target defined ROTATE as the single best ex-post ETF among the basket's 24 members. This creates a strong multiple-candidate maximum bias: date-weighted ROTATE prevalence is 88.17% in 2018-2020 and 68.95% in 2021-2022.

Primary frozen geometry LOGIT forward 2021-2022:
- balanced accuracy: 0.333333
- macro OVR AUC: 0.4773
- STAY AUC: 0.4192
- ROTATE AUC: 0.6334
- BIL AUC: 0.3791
- predicted ROTATE rate: 100%

Pre-2021 leave-one-year-out macro AUCs: 2018 0.5440; 2019 0.6499; 2020 0.3364; median 0.5440.

The frozen gate fails. No threshold/model tuning and no 2023+ outcomes were opened.

Scientific conclusion: the single-best-ETF oracle is not a valid target for whether a robust escape route exists. A separate preregistered STEP09A2 changes the target, not the model, to robust escape availability.