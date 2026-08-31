# STEP08I post-mortem

Official verdict: **REJECT_BEFORE_2023_HOLDOUT**. 2023+ remains sealed.

## What improved
Relative to the deployable STEP08H policy, the small-set selector improves the delta frontier by:
- CAGR: **+1.255 pp**
- mean MaxDD: **+0.598 pp**
- p10 MaxDD: **+1.884 pp**
- worst-decile MaxDD: **+2.025 pp**

Against FUSION1, STEP08I reaches p10 **+0.907 pp** while keeping CAGR at **-0.496 pp**, but mean MaxDD improves only **+0.118 pp**, worst-decile is **-0.093 pp**, and 2021 mean MaxDD is **-0.290 pp**. The strong gate therefore fails.

## Regime split
2021: the model chooses STAY 80.5%, ETF 19.5%, BIL 0%. The ETF interventions have mean realized advantage about **-3.08%** and beat FUSION1 only **27.5%** of the time.

2022: the model chooses STAY 48.2%, BIL 47.5%, ETF 4.2%. BIL decisions are much more useful; the year delivers mean MaxDD **+0.406 pp** and p10 **+1.148 pp**.

The dominant remaining failure is therefore not the causal shock filter. It is the instability of **ETF replacement action value**, especially in 2021.

## Post-hoc simplification diagnostic (NOT promotion eligible)
After the official result was known, the same fitted model was inspected under a diagnostic action restriction: **BIL if predicted BIL advantage > 0, otherwise STAY; no ETF rotations**. This gives approximately:
- CAGR **-0.074 pp**
- mean MaxDD **+0.367 pp**
- p10 **+0.999 pp**
- p5 **+0.254 pp**
- worst-decile **+0.547 pp**
- 2021 mean MaxDD **+0.012 pp**
- 2022 mean MaxDD **+0.424 pp**

This diagnostic is explicitly post-hoc and cannot be promoted or used to open 2023+. It does, however, identify a simpler hypothesis for a future preregistered experiment: **learn when BIL is preferable to STAY, and stop trying to select an ETF replacement for DD protection**. STEP08F's event-time ETF rotation remains separately preserved as an alpha challenger.
