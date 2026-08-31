# STEP07D — deterministic normalized-depth floor: development result

**Verdict: REJECT_BEFORE_2023_HOLDOUT_CLOSE_CONTROLLER_LANE**

2023+ holdout opened: **NO**.

## Primary result versus frozen FUSION1
- ΔCAGR: **-7.0824 pp**
- Δmean MaxDD: **+1.2539 pp**
- Δp10 MaxDD: **+2.1596 pp**
- Δp5 MaxDD: **+2.1154 pp**
- Δworst-decile MaxDD: **+1.8527 pp**
- Δworst basket MaxDD: **-4.9586 pp**
- ΔSharpe: **-0.176867**
- mean gross: **84.15%** vs FUSION1 **98.02%**
- extra-cut basket-days: **116529** (**46.33%** of development basket-days)

## Annual replication
- 2021: ΔCAGR **-7.8528 pp**; Δmean MaxDD **+0.5108 pp**.
- 2022: ΔCAGR **-6.3218 pp**; Δmean MaxDD **+2.0822 pp**.

## Quality-jump gate
- mean MaxDD >= +0.50 pp: PASS
- p10 MaxDD >= +0.50 pp: PASS
- CAGR >= -0.50 pp: **FAIL**
- annual mean-MaxDD nonnegative in both years: PASS
- worst-decile MaxDD >= +0.25 pp: PASS
- leave-one-episode-start-date-out: not run because the mandatory CAGR gate already failed; therefore not eligible to pass.

The rule does materially reduce average/tail drawdown, but only by remaining underinvested for almost half of development basket-days and sacrificing ~7.1 CAGR points. It also worsens the single worst basket by ~4.96 pp. No nearby ladder or threshold search is permitted by the preregistered protocol.
