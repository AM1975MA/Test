# OLC15 execution protocol — 2 November 2026

User approved the existing REGIME_ANALYSIS_IT.md direction. Parent branch tip2da5f4734aeac60af3cc5367e7904c493a27f288; OLC14 fixed parent6fcc215eeaa9834f5bcf8581e1fa6549a403f5b2. CUM_FIT remains an integration candidate, not a promotion. No main change, no trading. This protocol is committed before new fitted gates or economic results.

## Scope and recovered inputs
Restore and hash-check OLC14_Fitting_Risultati_20261101.zip and OLC12_Integrazione_Checkpoint_20261101.zip. OLC14 scores/fitting frames and frozen OLC12 prices/engine are sufficient for this integration test; no new base-learner fit is required. Reproduce ORIGINAL,CUM_FIXED,CUM_FIT (two markets,three timings,two legacy costs,plus IMMEDIATE systemic lag1) exactly against saved OLC14 curves before gate claims. The old binaries remain distinct from their GitHub manifests.

## Signal context frozen before fitting
First experiment is a deliberately small equity-context gate, NOT a complete macro/asset-class regime system. Benchmark SPY for USA and EXSA.DE for EU, both present in frozen execution inputs. No new price download and no claim that listing country identifies underlying exposure. Use only local close observations through the signal date; no contemporaneous US data for Europe. A fixed broad proxy avoids weighting its state by the number of ETF listings. All features use rolling past windows with no backward filling. At least126 observations before finite context.

Five context inputs:
1. benchmark log-return126 divided by daily log-volatility126*sqrt(126);
2. benchmark path efficiency63: abs(sum daily log returns)/sum(abs(daily log returns));
3. log(volatility21/volatility126);
4. benchmark drawdown from prior/current126-session maximum;
5. Spearman stability of CUM_FIXED forecast scores versus the previous signal, on ticker intersection, with exact duplicate pairs canonicalized before correlation. This is model-leadership stability, not certified economic breadth. Report its limitations and missingness. Exclude outcome variables from features.

Additional nonregime input RECENT: mean of the most recent12 fully matured, informative monthly differential outcomes per market, using only exit63-group date strictly before current signal. Fewer than3 matured observations gives zero plus documented count. Warm-up2019–2020 is not informative because FIT=FIXED. Diagnostics may display trend/stress groups but may not fit new thresholds from the test performance.

## Outcome and gate
For each full candidate month, delta = U(Top2(CUM_FIT_CURRENT))-U(Top2(CUM_FIXED_CURRENT)), using unchanged OLC14 U and tie-aware Top2 weights. U=(L0_21+q L21_42+q² L42_63)/(1+q+q²), q=sqrt(.5). Group label is available only after all finite endpoints and maximum exit63 date. Unknown outcomes never remove a live candidate.

Gate forecasts conditional delta, not overall market return. Annual fits2022–2026; retain historical 2021 gate fallback as1. At least12 matured dates per market and complete context for both; until available use g=1 (existing CUM_FIT). This is expected to defer first adaptation to2023, verified from actual rows. Count distinct market months, not ticker pairs. Shared coefficients, equal total training weight for EU and USA, same cutoff. Local contexts may yield different weights without different continent-specific rules.

Models: weighted ridge regression with intercept; predictor median imputation, mean/std and outcome RMS scale fitted on training only. Clip standardized predictors at +/-5. Lambda grid1,10,100 on mean-normalized ridge objective. Select lambda using chronological last two available annual validation blocks, only earlier mature training, at least12 train dates per market. Balanced validation squared error of delta; default10 if no valid fold. Exact ties prefer larger shrinkage. No CAGR or test outcomes in fitting. Map predicted differential to g=logistic(2*predicted_delta/training_RMS_delta), with 1e-8 scale floor. g is a mixing weight, not a calibrated probability. No extra gate-timing smoothing.

Frozen variants: ORIGINAL; CUM_FIXED(g0); CUM_FIT(g1); HALF(g.5); CONSTANT (intercept only); RECENT (one input); CONTEXT (five inputs); CONTEXT_RECENT (six inputs, primary candidate). Sensitivity CONTEXT_RECENT_LAG uses same current annual model and current recent-skill input, with the five context features delayed one monthly signal. Before valid fit all estimated-gate variants use the same g1 fallback. No HMM, hidden future state, dynamic exponent or fit of per-regime beta in this lot.

Mix contemporaneously scale-aligned CUM_FIXED_MAPPED and CUM_FIT_MAPPED scores, then apply unchanged .4/.3/.3 memory, power1.1, Return .475 + Hybrid .525. Do not average old NAV curves. Gate changes signals only, no cash veto/exposure/stop/V6 modification. Preserve ORIGINAL separately.

## Comparisons and windows
Primary native endpoint: same U excess of actual mixed Top2, CONTEXT_RECENT vs RECENT and CONSTANT, CURRENT and final FUSION separately. Also compare vs CUM_FIT and CUM_FIXED; probabilities of loss, regret, original-target ranking and21/42/63 plus incremental returns are diagnostics. Same complete groups across variants. Primary adaptive window2023–2024 with all exits matured before2025; report all2023–2024 signal outcomes through2025 as coverage sensitivity. Full adaptive2023 to last matured group by2026-07-01, plus2025,2026partial. Include2021–2024 and full2019 onward but never describe fallback years as gate successes.

Portfolio: nine variants x two markets x (IMMEDIATE,DELAY3,PHASE5) x two costs(.001,.003)=108 full paths; IMMEDIATE systemic-input lag1 for all variants/costs=36 additional paths. Total144 including48 exact parent controls. Frozen V6/exposure and same-open assumptions remain. Report adaptive2023–2024 and2023–2026,2021–2024,full,annual,turnover,drawdown and worst months. Independent NAV and metric recalculation.

## Validation, safeguards and preservation
Tests first for causal feature prefix, missing observations, duplicate leadership inputs, label maturity, local calendar alignment, ridge/balance/scaler training-only, bounded mixture weights, warm-up equality, endpoints g0/g1, mixed-score rather than NAV semantics, and future outcome perturbations preserving earlier fits. Native metrics independently reconstructed. Four primary contrast families; paired block bootstrap6months,4000draws,seed20261102, common calendar blocks EU/USA, missing months explicit. CIs are descriptive, no zero-veto/posterior interpretation and no untouched-holdout claim.

Register first verification checkpoint, then source/tests, final data/model/result artifacts and hashes on GitHub; full prepared checkpoint in Library. No claims that a manifest alone uploads binaries. Keep failures, scope reductions and post-observation extensions explicit; no automatic production promotion.
