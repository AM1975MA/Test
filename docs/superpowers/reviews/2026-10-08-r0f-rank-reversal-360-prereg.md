# R0-F — Corrected split-stability diagnostic, frozen BEFORE execution
**ETF Trader V2 — 2026-10-08 — NEW TEST, synthetic only**

Repo `AM1975MA/Test`, branch `research/v2-xgb-immutable-checkpoints-20261008`. This single bounded follow-up addresses a specific flaw of [R0-E](2026-10-08-r0e-synthetic-leaf-cap-results.md): its `+1` label perturbation changed one numeric relevance grade but did **not** necessarily change any ordering of relevant document/ETF pairs. Thus R0-E's favorable capped-tree outcome may primarily reflect small X perturbation on an easy synthetic fixture and cannot be generalized to label-sensitive annual Compact21.

**Aim:** falsify (not confirm by parameter tuning) the claim that max_leaves=8 stabilizes *both* feature and genuinely rank-changing label perturbations, without compromising synthetic top-tail selection. This is **not an ETF training/backtest**, an economic proxy, or permission to alter `Etf_trader`.

## Frozen one-axis protocol
- XGBoost 3.1.3, `rank:pairwise`, `hist`, 125 ordered features, `max_depth=4`, 360 rounds (canonical round count), eta .035, subsample .85, colsample_bytree .8, min_child_weight 8, reg_lambda 8, reg_alpha .1, seed 101, nthread=1, query sizes 40.
- Only two tree capacities: `max_leaves=0` (depth-based upper bound 16) vs `max_leaves=8`. No other parameter changes and no sweep.
- **Two independent synthetic worlds**, RNG seeds **20261009** and **20261010**, each 36 monthly-like ranking groups ×40 rows (1,440 training rows) and 12 independent evaluation groups ×40 rows (480 evaluation rows). World A nonlinear sparse feature interactions; world B nonlinear weaker/noisier signal with different feature coefficients. Generated from independent RNGs; NOT Yahoo-like economics.
- Four scenarios per capacity/world, each baseline fitted from scratch under same XGB seed and cutoff policy: `original`, `X_only`, `Y_only`, `X_and_Y`. Thus **2 worlds × 2 capacities × 4 scenarios = 16 new synthetic fits**. This is different from prior 4-model R0-E joint perturbation at 120 rounds; R0-E itself is NOT rerun.
- Training feature perturbation: independent additive noise std **2.5×10^-6 on every standardized float32 feature**, same order of magnitude as R0-E, but **NOT the Yahoo OHLC relative-value change**. Use identical X noise in each capacity and corresponding scenario.
- Label perturbation: choose **exactly one row** with a non-max rank within query zero by deterministic RNG; adjust its integer relevance from rank grade r to **one point higher than the immediately superior relevance grade**, verifying that **at least one within-query pair strictly reverses relevance ordering**. Use identical changed label across both capacities and their Y/joint scenarios; log the one changed row, delta, and count of reversed pairs. If requirement fails, abort instead of relabeling after result inspection.
- Source-group order and entire 12-group evaluation X stay identical across all eight fits of a world. No feature/pricing data from Original149, EU120, Holdout70 or Golden.

## Preselected measurements (no outcomes seen)
1. Compare each altered fit to same-capacity original on **identical** evaluation X. Report 12/12 Top1 agreement, prediction mean abs difference, native top1 holdout Top5-hit vs synthetic latent actual top5 (not portfolio P&L).
2. Compare node structure (feature + child IDs) vs **threshold-only** movement; count first structural change tree/node; show average/max realized leaf count. Different thresholds with same learned split structure are not identical boosters.
3. Report separately X-only, Y-only and joint, per world and cap; **never average away a failure**. If capped result only works in one world/channel, mark **not robust**.
4. Quantify top-opportunity capture **per world** under original and altered cap. Lower quality on synthetic world is grounds not to call the approach validated; equal synthetic quality is **not proof** of financial noninferiority.
5. Derive no financial return, CAGR, drawdown, annualized proxy, or ETF selection. No new threshold or hyperparameter tuning following results.

## Controls, stop gates and files
- TDD validate one-label rank inversion and comparator's structural-vs-threshold classification. Run tests RED→GREEN; then execute synthetic fitting once.
- If new rank-changing label perturbs the 8-leaf model significantly, explicitly **downgrade** R0-E's strong-stability interpretation; do not fit more settings until a new approval and genuinely new hypothesis.
- If 8-leaf remains more stable in both worlds/channels but synthetic Top5 quality declines, classify `STABLE_BUT_SKILL_RISK` rather than GO.
- If both worlds/channels look favorable: classify `SYNTHETIC_ONLY_PROMISING`, not a promotion to ETF Trader or a reason to reuse the burned Original149 for model selection.
- Save executable Python files/tests and JSON report on the **new GitHub Test research branch**. Under this authorization only synthetic models may train. No production modifications. Independent agent dispatch must not be fabricated.
