# STEP08F final checkpoint

- Verdict: **REJECT_BEFORE_2023_HOLDOUT**
- Producer: **HGB event-time distillation of authentic TIT_R**
- F0 parity gate: **PASS** (mean Spearman 0.864606; median 0.903810; basket Top-3 overlap 0.536917)
- 2021-2022 vs FUSION1: ΔCAGR **+0.632483 pp**, Δmean MaxDD **+0.050503 pp**, Δp10 **-0.865013 pp**, Δworst-decile **-1.354248 pp**.
- 2021: ΔCAGR **+0.314126 pp**, Δmean MaxDD **-0.219715 pp**.
- 2022: ΔCAGR **+0.987675 pp**, Δmean MaxDD **+0.408654 pp**.
- BIL fallback: **0.00%**.
- Event-level chosen destination beats exact FUSION1 utility: **53.74%**.
- 2023+ opened: **NO**.
- No post-result retuning.

## Key interpretation
Refreshing TIT_R at event time fixes a meaningful part of monthly-score staleness and raises aggregate/2021 CAGR, but it shifts the policy toward return-seeking destinations and loses the drawdown-tail benefit required by the preregistered gate. The destination problem is therefore not solved by freshness alone.
