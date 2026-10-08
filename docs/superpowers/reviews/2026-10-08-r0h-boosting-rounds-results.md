# R0-H — Boosting rounds 60–360, preregistered synthetic prefix audit
**ETF Trader V2 / Superpowers · 2026-10-08 · RESEARCH ONLY**  
**Repository:** `AM1975MA/Test`, branch `research/v2-xgb-immutable-checkpoints-20261008`.

**Protocol locked BEFORE model training:** [R0-H preregistration](2026-10-08-r0h-boosting-rounds-prereg.md), commit `13c91f6f5e1256910f801952f293677d2f3c245c`. This is a **new boosting-round axis** not tested in R0-E/F. Absolutely **NO financial ETF training**, no Original149 replay, no CAGR backtest, no ETF Trader production changes, no round-count model promotion.

## Decision / conclusion

**Reducing the number of trees does not systematically stabilize the model even on these two new synthetic worlds.** In world A the original-label-vs-flipped-label ensemble Top1 agreement actually **increases** as the number of trees grows from 60 to 360; in world B it oscillates. Cross-world total Y-only agreement is 21/24 at 60, 19/24 at 120, 20/24 at 180, 21/24 at 240, 21/24 at 300, and 22/24 at 360. Thus the intuitive statement "the last trees are always responsible for amplification" is **not supported** by this diagnostic. Early trees can also establish the first unstable order, while additional trees may either correct or reinforce it. Neither shorter nor longer is inherently a solution.

**NO GO** for selecting or changing the canonical 360-round count based on the available evidence. We can affirm the question was genuinely tested at the level of a synthetic grouped `rank:pairwise` model; we CANNOT affirm any real ETF CAGR/stability improvement from a different round count. Do not tune rounds on historical Original149, Golden or the Yahoo Repeat1/2/3 snapshots.

## Technical provenance

The original `vendor/etf_trader_v2/src/etf_trader/source_only/models.py::_fit_compact_rankers_isolated` and `_xgb_worker.py` fit an **individual 360-round booster for each seed and horizon** (21/63, seeds 101/202/303), then take the arithmetic mean of the 3 raw predictions. Therefore "360 rounds" means **per seed per horizon**, not 360 trees total across the ensemble.

**Fixed synthetic experiment:**
- **2 new synthetic worlds** seeded `20261011` and `20261012` (not the older R0-F worlds 20261009/20261010), 36×40 train rows and independent 12×40 test candidates per world, **125 features**; latent ground truth is mathematical/artificial.
- **Three scenarios** `original`, `X_only` (small 2.5e-6 additive standardized feature jitter), `Y_only` (one integer relevance label *strictly inverts* at least one within-query rank pair). Input test features and grouping fixed for all evaluations; no X/Y joint branch, since already used in R0-F.
- **Three original seeds 101/202/303**, 360 rounds each, parameters other than `num_boost_round` exactly fixed across runs: `rank:pairwise`, depth 4, learning rate 0.035, subsample .85, cols .8, min child Hessian 8, lambda 8, alpha .1, hist, `nthread=1`.
- **18 independent 360-round model fits total** (2 worlds ×3 scenarios ×3 seeds), **not 18 separate 6-value parameter sweeps**. Calculate predictions for frozen prefixes `60,120,180,240,300,360` via `booster.predict(dtest, iteration_range=(0,n))`; average across all 3 seeds as the source-only worker does.
- **Sanity refit:** one additional **60-round** fit of World A/original/seed 101 produces predictions **bit-identical** to the first-60-tree prefix of the 360-round fit: `max_abs_prediction_diff=0.0`. This confirms the prefix experiment really represents early stopping of the same trajectory in the verified setting. Source: [XGBoost 3.1.3 Python API](https://xgboost.readthedocs.io/en/release_3.1.0/python/python_api.html) on `iteration_range`.
- Environment: xgboost 3.1.3, numpy 2.3.5, pandas 2.2.3, pytest 9.0.2. **Five focused unit tests PASS**, Python `compileall` PASS, fit-run return code 0, 18/18 fits logged, two worlds reported.

## Results — 12 independent query groups per synthetic world, 24 total

`Top1 agreement` = how often modified-training ensemble picks the *same* synthetic candidate as baseline model with the **same number of rounds**, among 12 query groups. **Not** a measure of selecting the true best ETF. `Top5 capture` = baseline's predicted Top1 belongs to synthetic latent true five best, a toy skill metric **not** ETF-trading CAGR.

| Round count used | World A Y-only agreement | World B Y-only agreement | Total Y agreement | World A X-only | World B X-only | Baseline synthetic Top5 A+B | NDCG@5 baseline A | NDCG@5 baseline B |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 60 | 10/12 | 11/12 | **21/24** | 12/12 | 12/12 | 20/24 | .933130 | .872210 |
| 120 | 10/12 | 9/12 | **19/24** | 12/12 | 12/12 | 21/24 | .935673 | .859842 |
| 180 | 10/12 | 10/12 | **20/24** | 12/12 | 12/12 | 20/24 | .934960 | .867166 |
| 240 | 11/12 | 10/12 | **21/24** | 12/12 | 12/12 | 20/24 | .934297 | .873457 |
| 300 | 11/12 | 10/12 | **21/24** | 12/12 | 12/12 | 20/24 | .941306 | .879470 |
| **360 (canonical round count)** | **12/12** | **10/12** | **22/24** | **12/12** | **12/12** | 20/24 | .942587 | .865138 |

**Sensitivity beyond Top1:** rank-MAD under Y-only in world A stays ~0.0163–0.0195, world B ~0.0353–0.0382 (not a monotone improvement with fewer rounds). X-only Top1 stays 12/12 in **both** new toy worlds even at 360, but rank-MAD under X increases at later rounds in B; do not interpret stable Top1 as zero structural or score sensitivity. Earlier R0-F synthetic X-only counterexamples existed under a *different* world, so the new X-only stability does not contradict those results.

## Key limitations, avoid accidental overclaiming

- Artificial data, only **two independent synthetic worlds** and **12 evaluation groups per world**, no financial market regimens or actual rare explosive ETF winners; several outcomes 1/12 apart. The 24 evaluation groups also are **not 24 independent financial months**.
- R0-F in previous experiment fixed round count at 360; this experiment did not repeat R0-F or test cap8 again. Its higher/lower stabilization pattern depends on mathematical toy data, not original Yahoo 149 prices.
- No source-only actual annual fitted Booster checkpoint is archived, so we **cannot** read an already-fitted real original 360-tree model at 60/120 etc. Testing real early stopping would require new, causally qualified fit artifacts, separate pre-registration and matched full-V2 economic evaluation.
- This protocol uses **the same training data and latent synthetic test function** at multiple prefixes; the 6 checkpoints are **not six independent validation datasets**. They are a predeclared sensitivity profile; selecting the best score from them and declaring it generalizable is overfitting to one experiment.
- A pure target-label reversal on one row in 1440 synthetic samples is NOT matched numerically to the historical 8 real ETF pair flips; label generation, reference population, eligibility and true pair weight distribution differ.
- Only ensemble-mean forecasts were archived; per-seed predictions aren't retained individually. Do not assert independent per-seed stability.
- Same learning rate .035 was retained. Shrinking trees without changing eta reduces functional complexity and could remove high-opportunity skill. No early-stopping based on future labels was used.

## Revised action

1. **Keep 360 rounds as incumbent**; do not promote 60/120/180/etc, and do not search finer grids on 2017–26. The evidence rejects a simple monotone late-tree fragility explanation.
2. Prioritize **within-query label rank reversals and tie-entry/exit sensitivity**, demonstrated in [R0-G](2026-10-08-r0g-label-pair-transition-results.md), and separately **feature-X hist/split instability** established by past factorial forensics. Pairwise loss gradient dynamics remain mechanistic hypothesis, not a solved root cause.
3. If genuine point-in-time *new* financial training data can be collected, preregister **one** round-count challenger or one loss objective intervention, **not both**; compare on same universe/vintage full V2 CAGR per vintage, daily DD, transaction fees, turnover and extreme-upside capture. Do not substitute synthetic NDCG for economics.
4. Keep compact Dense ranking as conceptually independent fallback; hard Top38 filter triggered by past dispersion stays NO GO (R0-D AUC about 0.5).
5. Original code and strategy untouched. No agents independently dispatched.

## Reproducibility assets

The self-contained exact analysis code, tests, full per-prefix results, summary CSV, execution log and SHA256 inventory are provided in `ETF_Trader_V2_R0H_Boosting_Rounds.zip` alongside the conversation and were validated locally. They should not be described as GitHub-committed until separately uploaded. The preregistration and this results document are committed to GitHub Test.
