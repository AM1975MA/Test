# STEP07A — adaptive local-scale + competing-hazard development result

**Verdict: REJECT_BEFORE_2023_HOLDOUT.**

The 2023+ holdout was **not opened**.

## Primary LOCAL_PLUS_REGIME vs frozen FUSION1 — 2021–2022
- ΔCAGR: **-0.4314 pp**
- Δmean MaxDD: **-0.4109 pp**
- Δp10 MaxDD: **-0.4825 pp**
- Δp5 MaxDD: **-0.3932 pp**
- ΔSharpe: **-0.01611**
- mean gross exposure: **99.44%**

## Primary vs STEP06K
- ΔCAGR: **-0.4564 pp**
- Δmean MaxDD: **-0.4196 pp**

## LOCAL_ONLY ablation vs FUSION1
- ΔCAGR: **-0.4036 pp**
- Δmean MaxDD: **-0.4053 pp**

## Year consistency — primary vs FUSION1
- 2021: ΔCAGR **-0.3534 pp**, Δmean MaxDD **-0.3200 pp**
- 2022: ΔCAGR **-0.5074 pp**, Δmean MaxDD **-0.2210 pp**

## Hazard diagnostics
The next-session endpoint hazards themselves are highly rankable:
- primary crash-next AUC: **0.9726**
- primary recovery-next AUC: **0.8629**

This does **not** translate into economic protection. The controller worsens MaxDD relative to both HGB and FUSION1 despite average gross exposure of 99.44%. This is strong evidence that predicting proximity to the normalized endpoints is not the same as predicting the economic value of de-risking.

## Pre-registered net-jump gate
- mean_maxdd_vs_fusion1_ge_0_50: **FAIL**
- p10_vs_fusion1_ge_0_50: **FAIL**
- cagr_concession_vs_fusion1_ge_minus_0_50: **PASS**
- mean_gross_ge_0_85: **PASS**
- annual_maxdd_nonnegative_both: **FAIL**
- local_only_maxdd_nonnegative: **FAIL**

## Mechanism
For the primary controller, the gross (before overlay transaction costs) CAGR delta versus HGB is **-0.4073 pp** and net is **-0.4610 pp**. Approximate mean cumulative exposure-change cost over the two-year validation is only **0.0939%**. Therefore transaction cost is not the main failure mechanism; the de-risking decisions themselves lose economic value.

The clean low-dimensional adaptive-hazard route is rejected before holdout. No sizing, endpoint, percentile or feature retuning is authorized from this result.
