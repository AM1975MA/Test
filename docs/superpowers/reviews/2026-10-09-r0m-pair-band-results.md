# R0-M — Data review: 20bp ambiguous-pair masking vs matched full-pair ranking
**9 October 2026 · FINAL · decision: FAIL_JOINT_GATE · Test-only research**
**Pre-registered before model fits:** [R0-M protocol](2026-10-09-r0m-pair-band-prereg.md). **No ETF financial training, full-V2 backtest, CAGR, or production changes.**

## Primary decision

A hard **20 basis-point pairwise eligibility mask** *does* remove model sensitivity to the single deliberately constructed low-margin label-order inversion on two artificial grouped datasets (**Y-only Top1 stability 40/40 vs 38/40 unmasked custom**). However it does **NOT** pass the jointly specified stability / opportunity-capture gate. On the harder artificial world B, it reduces selected-realized Top5 capture **16→15 out of 20** and exact winner **4→3 out of 20**; it also loses one of 20 unchanged Top1 selections under tiny **X-only** perturbation (20→19 agreement), decreases NDCG in both worlds, and reduces the mean synthetic realized selected return in both worlds relative to matched no-mask custom loss. **No production adoption, no 20bp optimization on the explored Original149.**

This is an experimentally evidenced **conditional mechanism**, NOT a demonstrated stable profitable learner. User's prior goal to preserve extreme winning ETF opportunities overrides numerical stability alone.

## Source integrity / method

- **Frozen before fits:** XGBoost3.1.3, synthetic only, two new worlds A/B generated with seeds 20261031/20261101, each 32 train groups ×32 candidates (1,024 rows, 125 features) plus independent 20 eval groups ×32 (640 rows), one tree seed **101**, **360 boosting rounds**. Three arms: `rank:pairwise` native reference; **custom all-pairs logistic** with 0bp band; **same custom all-pairs logistic** with fixed 20bp hard exclusion. Each has original, training-X-only jitter (feature-unit Gaussian SD 2.5e−6), and training-Y-only exactly **one** within-query two-label rank inversion at 0.1bp gross return difference, unchanged train X. **2 worlds ×3 arms ×3 variants =18 fitted boosters**. No 149 ETF model fit or portfolio trading.
- The *causal test of the mask* compares **custom 0bp vs custom 20bp**. Native `rank:pairwise` is contextual only: different pair sampling, Hessian curvature approximation and label input; comparisons against native do **not** isolate the 20bp intervention.
- The custom objective computes per-group all eligible pairs and an **approximate diagonal Hessian**, unlike original XGBoost native `rank:pairwise`. It cannot be described as a drop-in same-objective patch. The label inversion stays inside the excluded band with all other eligible pairs unchanged by construction; therefore perfect Y-only stability partly follows from the constructed intervention and **does not** prove robustness to authentic Yahoo adjusted-price revisions (which previously had 14 eligibility flips at 20bp).

## Source result table (synthetic evaluation)

| Arm | Top1 in realized Top5 (of 40 groups) | Exact top1 (of 40) | Mean NDCG@5 | X-only same Top1 (of 40) | Y-only same Top1 (of 40) | Mean synthetic selected next-period return |
|---|---:|---:|---:|---:|---:|---:|
| Native `rank:pairwise` (contextual reference) | 32 | 13 | 0.922946 | 35 | 36 | 0.0408521 |
| Custom all-pairs logistic, 0bp | **33** | **13** | **0.917695** | **40** | 38 | **0.0404922** |
| **Matched custom all-pairs logistic, 20bp mask** | **33** | **12** | 0.915921 | 39 | **40** | 0.0394208 |

**Per-world matched 20bp minus 0bp:**
- World A: Top5 18/20 vs 17/20 (+1), exact best 9 vs 9, NDCG 0.938299 vs 0.941331 (−0.003033), selected gross artificial return 0.046649 vs 0.047225 (**−0.000576**, −0.0576 percentage points per artificial period). X-only agreement 20/20 vs 20/20, Y-only 20/20 vs 19/20.
- World B: Top5 15/20 vs 16/20 (**−1**), exact best 3/20 vs 4/20 (**−1**), NDCG 0.893544 vs 0.894058 (−0.000515), synthetic return 0.032193 vs 0.033760 (**−0.001567**, −0.1567 percentage points per artificial period). X-only 19/20 vs 20/20, Y-only 20/20 vs 19/20.
- In the two synthetic worlds, 20bp excludes **4.662%** and **4.366%** of theoretical within-group training pairs; the label reversal has identical mask eligibility before and after perturbation.

**Historical observational prior (no new fit):** frozen Yahoo Repeat1/3 Compact21: **8 strict pair inversions** and **14 tie transitions** among 2,333,613 available comparable cross-sectional ETF pairs; 20bp excludes ~3.79% of theoretical pairs, with **zero sign inversions among eligible pairs** yet **14 pairs changing eligible/ineligible status**. The real pairs' maximum gap was **0.0116bp**. Those are *all-theoretical-pair* counts, not the native XGB actual sampled pair set. The 20bp band is based on assumed 0.1% fee per side but has **NOT** been calibrated as a statistically justified noise magnitude; the fee difference between two equally costly ETFs is not automatically 20bp.

## Data QA (freshly verified without refitting)

- Existing final `results.json`: SHA256 `bb5354132bdec1c5b0d5cddcd043b2ad317dd13164ac22feb03270ebd0a5004d`, 18 logged fits, two 1,024-row training groups and two 640-row evaluations, original source data never used for training.
- Locally **reran read-only Data independent audit**, result `DATA_AUDIT_PASS worlds=2 models=18 ... OUTCOME: FAIL_JOINT_GATE`; **reran all 12 R0-M/R0-L unit tests, 12 PASS**. Did **not** rerun any completed R0-M learner fit, optimize parameters or repeat historical V2 backtests.
- Verified support bundle `ETF_Trader_V2_R0M_Data_20261009.zip` (SHA256 `a13cc79ceec0a35ac8d59ace884612f7cda9340011dd7886eb2cfd27e100a68d`) holds `r0m.py`, targeted tests, `data_audit.py`, JSON results, Data report and raw logs. The ZIP and source remain in conversation downloads, **not claimed committed as executable source on GitHub** in this documents-only publication.

## Follow-up decision (not a new blind parameter sweep)

1. **DO NOT** promote hard 20bp clipping, `rank:ndcg` replacement (R0-K quality failed), cap8 leaves, fewer trees, HGB/Ridge/Fourier, or historical Top38 funnel.
2. **DO** separate **native XGB pair sampling** and objective-gradient invariance vs altered training-X histogram cuts. R0-M's full-pair custom comparator *without masking* was already slightly steadier, but native-vs-custom conflates model objective and Hessian so that is only an **attribution hypothesis**. Review XGBoost's exact native pair generator/parameters and whether a faithful API-level pair reweighting is feasible before any candidate. No automatic learner fit.
3. If exact native pair-weighting is impractical, stop objective engineering and focus on the proven engineering fix: **immutable as-of data + fit checkpoints + explicit causal refits**, including MA3/cluster states. This resolves silent backtest drift, **not** generalization instability.
4. For a truly new causal data vintage, preregister **one** objective candidate and then compare *unchanged full V2* across same snapshot with daily CAGR/DD, fees, turnover and extreme-winner capture. Do not use burned Original149 to choose the band or evaluate a model replacement.
5. Distinguish risk policy for 2025 UNG concentration from model fitting stability; do not conceal a learner's quality regression under a new risk overlay.

**Verdict: VALID MECHANISM, FAIL JOINT MODEL GATE, KEEP CANONICAL V2.**
