# R0-E Results — pre-registered synthetic XGBoost leaf-cap test (no financial data)

**Date:** 2026-10-08. **Status:** SYNTHETIC MECHANISM EVIDENCE ONLY, NOT PERFORMANCE APPROVAL.
**Repository:** `AM1975MA/Test`, research branch `research/v2-xgb-immutable-checkpoints-20261008`.
**Frozen preregistration:** [R0-E protocol](2026-10-08-r0e-synthetic-leaf-cap-prereg.md), commit `17ac960659f8eda26efea1138618fd8b39832bb2`, published before running model fits.

## Setup

- XGBoost **3.1.3**, objective `rank:pairwise`, hist, `max_depth=4`, eta .035, subsample .85, colsample_bytree .8, `min_child_weight=8`, L2=8 and L1=.1, seed 101, nthread 1, 125 features.
- Toy grouped dataset: **36 query groups × 40 samples = 1,440 training examples**, **12 groups × 40 = 480 untouched inference examples**, nonlinear synthetic relevance and within-query integer 0–100 labels.
- Exactly **120 rounds** (not the canonical annual 360). A single synthetic perturbation changes each standardized-scale feature by jitter with std 2.5e−6; independently **one relevance label is changed by ±1** (1/1440 ≈ 0.069%). The observed maximum absolute feature perturbation is 1.15633e−5; this is a standardized-scale additive jitter and should not be misdescribed as an exact Yahoo price perturbation.
- Only **one structural parameter differs**: existing `max_leaves=0` (effective ≤16 via depth4) versus **`max_leaves=8`**, `grow_policy=depthwise` unchanged. Exactly **four model fits** (two variants × unperturbed/perturbed); no parameter sweep or optimization based on Original149.
- Predictions compared on *exactly the same* 480 synthetic held-input rows and ground-truth latent top-five labels, no trading simulation.

## Initial validation improvement: distinguish thresholds from real structural differences

A naive first split counter called *any* different floating split threshold a structural change. This would be materially misleading: even a 1e−6 threshold shift might produce no change in routing. Four explicit tree-dump unit tests (two RED before implementation; four GREEN after) distinguish:
1. split **feature, children/branch or tree topology** changes;
2. numerical **threshold-only** moves;
3. leaf-value changes;
4. identical trees except leaf values.

**Only item (1)** is the actual node-structure comparison below.

## Observed results

| Measurement | Canonical-like max_leaves=0 | Single-axis max_leaves=8 |
|---|---:|---:|
| Fitted trees in each of the 2 models | 120 | 120 |
| Mean **effective** leaves per tree (unperturbed) | 10.9083 | 7.9583 |
| Maximum leaves seen | 15 | 8 |
| **Changes in split feature/branches/topology** | **1,179** | **0** |
| Changes confined to split threshold | 486 | 831 |
| Largest absolute threshold change | 3.31976342 | 8.7×10−6 |
| Changed numerical leaf values, aligned by node ID | 651 | 0 |
| **Same predicted Top1 across 12 synthetic eval groups** | 11/12 (91.67%) | **12/12 (100%)** |
| Max absolute diff in synthetic predicted score | 0.12451 | **0** |
| Mean absolute synthetic predicted-score difference | 0.031257 | **0** |
| Synthetic oracle **Top5 capture** of the unperturbed model | 11/12 (91.67%) | 11/12 (91.67%) |
| Synthetic oracle Top5 capture of perturbed model | 11/12 | 11/12 |

**First true structural change** for `max_leaves=0` occurred at learned tree **33**, node id **3**, although numerical threshold differences began at tree 0. For `max_leaves=8`, no changes in split feature or branch routing were observed in the **learned tree dump**; 831 small threshold-only shifts never changed the synthetic test-row predictions.

**Important distinctions:**
- Even `max_leaves=8` generated slightly different floating thresholds, so *not* strictly byte-identical boosters. The observed prediction identity is restricted to the common 480 synthetic inference rows.
- This is one synthetic dataset, one fixed jitter realization, one changed label, one seed, 120 rounds and **12 groups**. It does **NOT** validate better fit stability in the actual 149 ETF system, actual adjusted OHLC histories, new ETF universes or future years.
- Stable synthetic Top5 capture is **not** proof of unchanged ETF Trader V2 Top1/Top2 accuracy, rare high-CAGR outcomes, or economic noninferiority. There is no historical or future CAGR measured here.
- The authentic trained Compact21 annual boosters were not archived in tracked GitHub Test; this result is **not a recovered original decision-tree forensic**. It is a synthetic structural falsification/proof-of-possibility.
- The code uses 2.5e−6 additive jitter on standard-normal standardized features, which follows a fixed *feature-unit scale* approximation. This is **not** a true multiplicative 2.5e−6 relative-price Yahoo perturbation; this protocol interpretation must not be overstated.

## Decision and next evidence gate

**S1 has mechanistic plausibility**: limiting tree leaves can strongly alter structural sensitivity on a constructed rank-learning problem while retaining high synthetic Top5 selection, and may deserve a single future *prospectively registered* financial candidate if actual V2 training can be compared without retrofitting past results.

**NOT GO for live V2, NOT a claim that 8 leaves optimizes CAGR.** Because `max_leaves=8` now looks promising on one toy sample, we must NOT sweep nearby values (6,10,12,...) or consult original-burnt 149 CAGR to choose settings. A true future result requires **a new point-in-time as-of ETF dataset**, *one fixed candidate*, full-V2 matched original baseline in the same new market/universe with predeclared **per-vintage noninferiority in CAGR and drawdown**, turnover, fees and extreme winner capture. An observed failure must reject the structural cap.

**Related R0-D no-go:** historical trailing 21/63d cross-sectional dispersion modestly predicts forward dispersion but fails to identify Top38 false-negative months (AUROC 0.515/0.531); do not start an adaptive Top38 screen on that signal. Focus new effort on ranker stability **at the source**.

## Reproducibility support (conversation package, not code silently claimed to be committed)

- `leaf_probe.py` SHA256 `3abf096b6cde43277a9218119a0f1c9b4510d1a80785da43d621a7303d467d85`;
- `test_structure.py` SHA256 `5808e61eaf4d33ef48f1398a5deb5e469153b1e16af8ed2d351b1e85924d33e6`;
- `synthetic_results.json` SHA256 `0d108971c924a4f620a2092c9cb2fe9eb9d2a29bf343d6b99ea1c4f759811cac`.
- TDD: initial two baseline tests GREEN, two new precise-threshold tests failed with missing keys before implementation, then **four GREEN** in final run. Synthetic training command output archived alongside source code in the user-support ZIP.
