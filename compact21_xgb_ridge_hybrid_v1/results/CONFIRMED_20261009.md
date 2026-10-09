# Compact21 fixed XGB75/Ridge25 — confirmed diagnostic 2026-10-09

GitHub run [37933994472](https://github.com/AM1975MA/Test/actions/runs/37933994472): **success**, registered original frozen XGB and Ridge source artifacts from run 37229180477, all original annual/refit/cohort/source integrity gates verified. Detailed machine-readable outcome: Actions artifact `xgb75-ridge25-summary` ID **11616929851**. All registered pre-outcome weights fixed; there was no weight search.

| Endpoint | BASE | Fixed hybrid | Change |
|---|---:|---:|---|
| Mean common-input rank-MAD | 0.0536093548 | 0.0477963034 | -10.84% (does NOT satisfy >=25% reduction) |
| Mean native Top1 disagreement across pairs | 50.0000% | 40.6433% | -9.3567 percentage points / -18.71% relative (does NOT satisfy >=25% reduction) |
| Mature selected Top1 mean realized target percentile | 0.5834372711 | 0.5986220823 | +0.0151848112 |
| Mature realized Top5 overlap (Precision@5) | 0.1262536873 | 0.1115044248 | -11.68% relative (FAIL >=95%-of-BASE floor) |
| NDCG@5 | 0.5519943578 | 0.5897070459 | +6.83% relative |
| Native pair Top1 disagreement 1-2 | 54.39% | 44.74% | improved |
| Native pair Top1 disagreement 1-3 | 42.98% | 40.35% | improved |
| Native pair Top1 disagreement 2-3 | 52.63% | 36.84% | improved |

Mature quality period 113 monthly dates; 114 months for decision-stability. The paired, noncircular 3-calendar-month bootstrap (20,000 draws, prespecified seed) on Top1 realized percentile change has estimated overall delta **+0.015185**, central 95% interval **[-0.04322,+0.06674]**, one-sided 95% lower bound **-0.035200**. The frozen allowed lower bound is **-0.05 × 0.583437 = -0.029172**. Thus the quality-conservation uncertainty gate fails despite a positive historical point estimate.

**Registered verdict:** `STABILITY_PILOT_PASS=false`, `NEAR_REPEATABILITY_PASS=false`, `QUALITY_CONSERVATION_PASS=false`, `STABLE_WITH_CONSERVED_QUALITY=false`, `production_adoption=false`.

The numerical results are exploratory diagnostics on repeatedly inspected Original149 history, not proof of significant forecasting improvements; the bootstrap uses dependent vintages clustered by signal date. **No economic full replay has been performed for this hybrid, so no hybrid CAGR exists.** In particular, its positive selected-Top1 mean percentile and NDCG cannot be converted to CAGR.

The result supports a useful engineering direction (regularized learner can reduce head instability while preserving/improving single-winner point estimates), but its measured Top5/uncertainty compromise is not sufficient under the registered gates. Do not tune neighboring weights on this development history. Prioritize fully recovering the separate original 9 completed BASE/RIDGE/LGBM full replays (run 37195399755) and an untouched holdout before another model candidate.
