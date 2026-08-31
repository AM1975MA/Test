# STEP08E final checkpoint

- Verdict: **REJECT_BEFORE_2023_HOLDOUT**
- 2023+ opened: **NO**
- Protocol persisted before execution: **YES**
- Post-hoc tuning: **NONE**
- Frozen q95 decisions: **1,124**
- Causal basket-local V2: delta CAGR **+0.476254 pp**, delta mean MaxDD **+0.415965 pp**, delta p10 **+0.179810 pp**, delta worst-decile **-0.525883 pp**.
- 2021 causal delta mean MaxDD: **-0.334021 pp**.
- 2022 causal delta mean MaxDD: **+0.795400 pp**.
- Basket-local oracle stay-allowed: delta CAGR **+9.156281 pp**, delta mean MaxDD **+3.046643 pp**, delta p10 **+4.940783 pp**.

Interpretation: restricting destination selection to the native 24-ETF basket materially improves the causal frontier versus full-universe STEP08D, but does not solve the 2021 failure. The local oracle remains very strong in both years, so destination opportunity exists; stale monthly ranking is the leading remaining limitation.
