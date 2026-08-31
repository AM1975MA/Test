# DD-controller checkpoint after STEP07D — 2026-08-31

## Decision
**Close the current DD-controller research lane. Do not open 2023+ and do not tune nearby normalized-depth ladders.**

STEP07D was the final preregistered deterministic test: exact FUSION1 protection was retained as a floor and a basket/path-specific fixed-volatility normalized cap could only reduce exposure further.

Development 2021–2022 versus FUSION1:
- ΔCAGR **-7.0824 pp**
- Δmean MaxDD **+1.2539 pp**
- Δp10 **+2.1596 pp**
- Δworst-decile **+1.8527 pp**
- Δworst basket **-4.9586 pp**
- mean gross **84.15%** vs **98.02%** for FUSION1
- extra protection active on **46.33%** of basket-days.

The mechanism therefore proves that normalized early de-risking can buy drawdown protection, but the price is far outside the allowed economic frontier. The CAGR gate (-0.50 pp maximum concession) fails by more than an order of magnitude. In 2021 the tail metrics are also unstable: mean MaxDD improves +0.5108 pp, while p5/worst-decile/worst-basket worsen.

Combined with STEP07A–07C, this establishes that the remaining limitation is not a missing classifier, regressor, quantile model, or nearby exposure ladder. Further tuning on the same information set is not admissible. A future reopening requires genuinely new information or a materially different portfolio architecture, not another controller parameterization.

2023+ remains sealed for STEP07D.
