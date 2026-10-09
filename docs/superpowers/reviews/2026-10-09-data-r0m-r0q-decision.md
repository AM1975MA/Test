# Data decision — 20 bp masked pairwise objective versus real-feature numerical root cause

**Date:** 9 October 2026. **Repository:** `AM1975MA/Test`. **Branch:** `research/v2-xgb-immutable-checkpoints-20261008`.
**Outcome:** **NO GO** for direct adoption of the `20 bp` hard-masked custom pairwise loss; **GO TO NEXT DIAGNOSTIC GATE ONLY** for continuous downside-feature candidate. Not a trading return improvement, no new ETF training/backtesting, and nothing touched in production.

## 1. Actual user-requested pairwise trial: already completed, not rerun

Existing *pre-registered* [R0-M primary report](2026-10-09-r0m-pair-band-results.md) and local 18-fit synthetic artifact `ETF_Trader_V2_R0M_Data_20261009.zip` were recovered and inspected; no need to repeat 18 already completed model fits. These consisted of 2 worlds × 3 models × baseline/X-only/Y-only = 18 fits, seed 101, 125 features, 360 rounds.

| 40 artificial held-out grouped queries | Canonical native pairwise (context) | Same custom all-pairs logistic, 0 bp | **Same custom, 20 bp hard mask** |
|---|---:|---:|---:|
| Top1 within true Top5 | 32 | 33 | 33 |
| Top1 exactly true best | 13 | 13 | **12** |
| NDCG@5 | **0.922946** | 0.917695 | **0.915921** |
| Top1 agreement, train **X-only** perturbed | 35 | **40** | 39 |
| Top1 agreement, train **y-only** rank-swapped | 36 | 38 | **40** |
| Artificial selected mean return (NOT ETF performance) | 0.040852 | 0.040492 | **0.039421** |

**Causal contrast:** the 20bp threshold effect is 0bp-custom vs 20bp-custom, because native uses different gradient/hessian, aggregation and label conventions. The hard mask raises synthetic y-only Top1 agreement **38→40/40**, but lowers x-only **40→39/40**, exact winner **13→12/40**, NDCG and selected artificial returns, with negative world B tail hit **16→15/20**. **Joint gate: FAIL**. Masked label reversal is inside an excluded interval by construction, which partly guarantees the observed y-only invariance and is not proof of robust Yahoo-vintage training.

**Limitations:** synthetic worlds and one model seed, not 149 ETF real as-of; old reports include a correction that current native XGB may use effective full-pair default; historical original 20bp category changes eligibility for 14 comparisons; trade fees of 20bp are not measurement-error bounds. No actual financial CAGR was measured. The read-only existing R0M report had 12/12 unit tests pass; re-executing just original 8 masked-objective focused tests here gives 8/8 PASS. Repeating the 18 model fits would create no independent validation and was deliberately avoided.

## 2. More consequential *real observed* feature-instability mechanism

Existing preregistered [R0-Q real-data report](2026-10-09-r0q-continuous-downside-feature-results.md) and frozen local `ETF_Trader_V2_R0Q_Continuous_Downside_Data.zip` show that source-only `rolling_downvol` computes conditional standard deviation of negative returns after `where(r<0)`. A near-zero return sign crossing can change *the number of available rolling observations*, interact with `min_periods`, and then propagate through the cross-sectional median/MAD scaling. This is a traceable nonlinear numerical amplification point, not a claim that XGBoost itself miscalculates.

An alternative **zero-target second lower partial moment** `sqrt(mean(min(r,0)**2))*sqrt(252)` is continuous under sign crossing. It is deliberately a **different risk feature**, not a drop-in semantics-preserving bug fix. The research-only candidate was compared on the **four-way matched finite cell intersection** of both Yahoo Repeat1 and Repeat3 with the original/native and continuous formulas:

| Lookback | Matched cells | Mean absolute vintage difference reduction | Original deviations >0.1 | Continuous deviations >0.1 |
|---|---:|---:|---:|---:|
| 21 | 18,412 | **23.20x** | 44 | **0** |
| 63 | 12,724 | **43.96x** | 16 | **0** |
| 126 | 8,676 | **24.25x** | 4 | **0** |

This was established from **actual frozen 149 ETF historical Yahoo adjusted Close**, no model training. The overall share of available feature cells changes materially because new formula uses all valid recent return days instead of counting only negative days; thus neither the training-row population nor Alpha nor CAGR is proven preserved. The requirement `>=30/125` nonmissing features for the original model means **more available cells for one feature do not imply more eligible training rows**.

**Independent validation in this follow-up:** local `pytest -q test_r0q.py`: **6 passed**, result status `R0Q_READ_ONLY_COMPLETE`, independent audit status `AUDIT_PASS`, four-way common support `MATCHED_SUPPORT_QA_PASS`. On those same cells, all 64 source revisions >0.1 across windows disappear in the challenger; this is descriptive *feature-level* sensitivity improvement, not `Top1` or portfolio economic stability. No original real ETF fits repeated.

## 3. Decision and next *strictly warranted* experiment

**Discard for now:** integrate 20bp hard pair eligibility filter, tune band threshold on Original149, change XGB num trees/depth based on synthetics, adapt Top38 screen, claim model stability from return-label cleanliness.

**Prioritize P0 source-level independent verification followed by one P1 data-contract experiment**, not a hyperparameter sweep:
1. Reproduce exact source-only 125-feature construction with time-aligned point-in-time ETF membership and annual maturity constraints on **a genuinely fresh, separately versioned as-of dataset**, or a frozen development panel used only for non-performance diagnostics.
2. For the proposed continuous downside risk family, build the 125-feature cohort in parallel and explicitly compare *identical group/key support*, `>=30` nonmissing cutoff, rank-percentile transforms and 21/63/126 lookbacks. No silent overwriting the original feature schema. **Stop if cohort/feature semantics mismatch is noncausal or unacceptably large.**
3. After prerequisites and a predeclared full source-contract gate, run **one** matched X-only training intervention for canonical XGB (3 seeds, horizons 21/63, 360 rounds) while holding y maturity and decision engine fixed; compare trained-model common-input vs native Top1 disagreement, tail capture and decision exposure. Do not combine loss and feature changes.
4. **Only if** trained ranker passes stability and upside gates on new prospective sample, compare to unchanged full V2 for daily compounded net performance, per-vintage CAGR if sufficient years, daily MaxDD, fees, turnover and high-upside selected positions; wrong/unknown data snapshot or short horizon => do not fabricate meaningful CAGR.
5. Retain canonical V2 unchanged on any failed guardrail, with two model identities and no automatic champion promotion.

**Scope:** analysis-only consolidation and unit validation; no financial testing or production integration in this task. Superpowers workflow stays inside GitHub Test research branch; Data analyses independently distinguish row-population, input semantics, proxy metrics and full V2 economics.

## Source paths

- `docs/superpowers/reviews/2026-10-09-r0m-pair-band-results.md`
- `docs/superpowers/reviews/2026-10-09-r0q-continuous-downside-feature-results.md`
- `docs/superpowers/plans/2026-10-08-data-led-v2-stability-roadmap.md`
