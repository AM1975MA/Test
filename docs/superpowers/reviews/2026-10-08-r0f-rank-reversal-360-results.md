# R0-F — Corrected 360-tree XGBoost synthetic label-inversion result: max_leaves=8 NOT ROBUST

**2026-10-08 · TEST-only branch `research/v2-xgb-immutable-checkpoints-20261008` · NO ACTUAL ETF FIT / NO CAGR.**
**Preregistered before training:** [`2026-10-08-r0f-rank-reversal-360-prereg.md`](2026-10-08-r0f-rank-reversal-360-prereg.md), commit `df9f3a8e155bf8c42c3ff566bb868c7f2d9702ca`.

## Bottom line
**NO GO** for treating `max_leaves=8` as the established stability fix. Contrary to the favorable initial R0-E toy fixture, the cap can be **less stable** than the depth-only canonical-like tree constraint. A genuinely **rank-reversing single-label perturbation** causes extensive split-topology changes **under BOTH leaf settings**. Therefore **do not promote capped trees to ETF Trader**, do not rerun old Original149 data, and do not sweep max_leaves around 8 hoping to regain performance.

This negative result is **synthetic only**: it neither establishes a causal solution for original V2 annual fits nor establishes the cost to financial CAGR.

## Why the prior result needed a corrected test
The R0-E training relevance targets were ranks quantized as `round(rank / 39 * 100)`. Changing one grade by `+1` did **not necessarily invert an ordinal pair**, unlike actual training perturbations that can reverse realized rank ordering. Its label contribution was under-tested, and its only 120 trees/12 test dates made `0` changes for one setting fragile. We preserved R0-E as historical evidence; **this new independent fixture does not rerun R0-E**.

## Frozen R0-F design
- XGBoost **3.1.3** `rank:pairwise` with same canonical-like XGB settings: `max_depth=4`, eta `.035`, `subsample=.85`, `colsample_bytree=.8`, `min_child_weight=8`, `lambda=8`, `alpha=.1`, hist, one seed `101`, **360 rounds**.
- Sole changed architecture: `max_leaves=0` (depth-limited) versus `max_leaves=8`; no other parameter optimization.
- **Two independently generated artificial worlds**, fixed generator seeds **20261009** (world A) and **20261010** (world B); each with 36 × 40 training rows and independent 12 × 40 inference rows, 125 dimensions. World B has distinct signal function and more noise.
- Per setting/world four separate **independent trainings**: original, perturbed **X only**, perturbed **y only**, perturbed both. Exactly **16 synthetic fits**.
- Training X additive float32 jitter σ=2.5e-6 on standardized features (NOT Yahoo-price % disturbance). Label: **one and only one** synthetic training grade changed, from **51 to 55**, strictly inverting **one** within-group relevance pair. Same perturbations were paired across caps. All 12 evaluation-query input matrices unchanged.
- Tree dump comparator distinguishes split feature/child/missing/structural differences from mere split-threshold float movement; seven focused tests verified (RED: module not initially importable; GREEN: 7 tests, exit 0). Full code files `r0f_probe.py`, `test_r0f.py`, `results.json` in conversation support bundle. No ETF historical prices or 149×3 backtests.

## Results — common-input *synthetic* prediction stability

| World | Perturbation | Depth-4 max_leaves=0 same Top1/12 | capped-8 same Top1/12 | Depth-only structural changes | cap8 structural changes |
|---|---|---:|---:|---:|---:|
| A | X only | **12/12** | 10/12 | 1,317 | 1,303 |
| A | y only, 1 truly reversed pair | 7/12 | **8/12** | 4,920 | 2,385 |
| A | X + y | 7/12 | **8/12** | 4,920 | 2,385 |
| B | X only | **12/12** | 9/12 | **0** | 1,402 |
| B | y only, 1 truly reversed pair | 7/12 | 7/12 | 4,926 | 2,687 |
| B | X + y | **7/12** | 5/12 | 4,926 | 2,703 |

**Top-5 synthetic latent-winner quality:**
- World A, base XGB: original 11/12; X-only 11/12; Y-only 11/12; joint 11/12.
- World A, cap8: original 12/12; X-only 11/12; Y-only 12/12; joint 12/12.
- World B, base XGB: original 9/12; X-only 9/12; Y-only 10/12; joint 10/12.
- World B, cap8: original 10/12; X-only 9/12; Y-only 10/12; joint 10/12.
Small 12-group samples; cannot infer economic dominance, power or predictive performance on ETFs.

**Structural nuance:** Comparing node IDs from independently grown trees counts all downstream structural changes after a first diverging split, so 4,920 **is not 4,920 independently caused split decisions**. It nevertheless indicates extensive downstream tree differences in this synthetic fixture and is corroborated by changes in 12 common-input rankings. In world A, first node feature/structure change after label inversion at tree 14 for base and tree 31 for cap8; in world B, tree 67 for base but tree 7 for cap8. These are **not** recovered historical Compact21 tree-node diagnostics.

**Quality/verification:** 7 tests passed, Python `compileall` passed, exactly 16 fits in a single execution, both worlds completed, label rank-inversion assertion passed for both worlds; model comparison output `results.json` retained. No original V2 models refitted or production files modified.

## What the result tells us
1. A hard leaf cap **may suppress some** structural differences yet introduce others. Original R0-E `0` changes was **not robust** to an independent fixture and a rank-changing label.
2. The `rank:pairwise` gradient/tree pipeline is evidently *capable* of being highly sensitive to one reversal of a training pair in artificial grouped data. Together with prior **real** four-year Compact21 `Y-only` diagnostic, this supports investigating **label-ordering stability at the causal maturity boundary**, not merely trimming tree complexity.
3. It **does not prove** the cause of Golden 43.146% versus 31.604%, a final causal remedy or the effect on financial profitability.

## Revised test-plan decision
- **STOP max_leaves=8 as a direct challenger.** Do not sweep nearby leaf counts or retest Original149/Repeat1/2/3 or EU120.
- Focus next **read-only** work on the **label construction/quantization and pair ordering** underlying `rank:pairwise`, and on how very small adjusted OHLC revisions propagate to realized forward-return order. Use existing forensics; if original fitted boosters unavailable, report it rather than reconstruct them with future-revised prices.
- Preserve Dense-MLP and 25%-recall funnel as **architectural alternatives** only: no training, no cascading K search, no performance claims. Cross-sectional trailing dispersion's diagnostic ROC ~0.515/0.531 rejects an adaptive Top38 gating rule on already researched history.
- New financial model testing only with **genuinely novel point-in-time observations**, pre-registered one challenger, **full unchanged V2 engine**, daily MaxDD, fees, turnover, per-vintage CAGR, tail-capture and no-change fallback. If fresh independent data/model checkpoints aren't available: **NO FINANCIAL TEST / retain existing V2**.

**Files (local support):** R0-F `r0f_probe.py`, `test_r0f.py`, `results.json`, `run_stdout.txt` + integrity manifest. No independent subagent dispatch tool was exposed in this session.
