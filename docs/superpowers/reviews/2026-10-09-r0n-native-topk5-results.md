# R0-N — Native XGBoost rank:pairwise: exhaustive vs topk=5 (Data + Superpowers final audit)
**2026-10-09 | FINISHED | `AM1975MA/Test` research branch only | SYNTHETIC-ONLY: POSITIVE TOP1 ROBUSTNESS SIGNAL, FULL-RANKING QUALITY WARNING, NO PRODUCTION GO**

**Pre-registration committed BEFORE model fitting:** [R0-N protocol](2026-10-09-r0n-native-topk5-prereg.md), commit `4277cd0db93113cb55d7649b1878120f35db0108`.
**Follow-up to failed R0-M hard 20bp mask:** [independent Data R0-M report](2026-10-09-r0m-pair-band-results.md). NO actual ETF training/backtest, no altered V2, no financial CAGR measured.

## Most important finding

The original annual Compact21 uses the native `rank:pairwise` objective with effectively exhaustive training pairs in XGBoost 3.1.3 (learner objective config `lambdarank_pair_method=topk, lambdarank_num_pair_per_sample=4294967295`); the separate **evaluation metric** `ndcg@3` reports `num_pair_per_sample=3` **only for the metric** and should not be confused with the objective.

A **one-parameter native change**, `lambdarank_num_pair_per_sample=5`, changes how pairs are selected *during each XGB boosting round* but **does not remove any of the 149 ETF candidates from the universe or impose a two-layer screener**. It retains the native loss function, normalization, tree hyperparameters, 360 rounds and the canonical three seeds. On **two fresh independent synthetic worlds**, this single change:

- improved or preserved baseline synthetic Top1→realized Top5 capture in **both** worlds;
- improved or preserved *both* feature-only and label-only Top1 agreement in **both** worlds; and
- improved point-estimate mean selected synthetic return in **both** worlds;
- **BUT** worsened the full Top5 **NDCG** in world B by **−0.02490 absolute** (from .90339 to .87849), with a descriptive paired 20-query bootstrap 95% interval of [−0.05159, −0.00079]. This is a **material ranking-quality warning**, not a clean all-metrics win.

Thus the predeclared Top1/tail/robustness headline gates pass, **but the full-ranking guard remains a problem**. The appropriate decision is **MECHANISTICALLY PROMISING / NO ETF PRODUCTION PROMOTION**. Zero evidence of higher actual V2 CAGR or compatibility with new ETF universes exists.

## Exact experiment

- Two fresh nonlinear grouped toy-worlds (A seed `20261109`; B `20261110`), each **32 train queries ×32 synthetic candidates** (1,024 rows), **20 untouched synthetic eval queries ×32** (640 eval rows), **125 feature columns**, and synthetic realized-return latent targets. No Original149, EU120, Yahoo Repeat, Golden or real finance data used for model fitting.
- **Two policies only:** original native `rank:pairwise` unmodified (exhaustive default) vs same native objective with **`lambdarank_num_pair_per_sample=5`**, while `lambdarank_pair_method=topk` remains its default. Five comes from the predeclared interest in realized top5 capture, **not** a retrospectively optimized best K.
- Three training scenarios per world: original, tiny X-only Gaussian jitter (SD=2.5×10⁻⁶ standardized feature units), one genuine within-query two-label Y-only rank inversion with gross return separation 0.1bp; same fixed eval X. **Three seeds 101,202,303**, **360 rounds**, depth4 eta=.035, min-child8, lambda8 alpha.1, subsample.85, colsample.8, hist, native group `QuantileDMatrix`. 
- Exactly **36 native XGB fitted boosters** (2 worlds ×2 policies ×3 training variants ×3 seeds). The run was interrupted at 28/36 by a tool time limit, then **resumed the remaining 8 without retraining the completed 28**. Each result saved as a keyed SHA/parameter-verified `.npz` containing the **prediction array**, **not** the fitted Booster `.ubj` file.
- R0-N control: X-only has unchanged train labels, Y-only unchanged train features; original/modified predictions compared on identical evaluation input.

## Results (ensemble average of three native seed scores per scenario)

| Synthetic world and metric | Native default exhaustive | Native topk=5 | Interpretation |
|---|---:|---:|---|
| A Top1 hits realized true Top5 | 18/20 | **18/20** | equal |
| A exact top1 winner | 7/20 | **7/20** | equal |
| A X-only same Top1 as respective baseline | 20/20 | **20/20** | equal |
| A Y-only same Top1 | 20/20 | **20/20** | equal |
| A NDCG@5 (baseline) | .936017 | **.940739** | +.004723 |
| A mean selected *synthetic* return | .040789 | **.042097** | +.001308 |
| B Top1 hits realized true Top5 | 15/20 | **17/20** | +2 |
| B exact top1 winner | 4/20 | **4/20** | equal |
| B X-only same Top1 | 17/20 | **20/20** | +3 |
| B Y-only same Top1 | 16/20 | **19/20** | +3 |
| B NDCG@5 (baseline) | **.903391** | .878490 | **−.024901** |
| B mean selected *synthetic* return | .035385 | **.037073** | +.001687 |

The plotted stability numbers are **not absolute model accuracy**. Same-Top1 under perturbed training does not mean the chosen ETF is a good investment. The Top5-capture and artificial selected-return columns measure only constructed latent targets. **No real CAGR, daily MaxDD or Sharpe was computed.**

### Independent Data review (saved forecasts only, zero refits)

A separate code path reopened the **36 `.npz`** files, verified **all 36 SHA256 hashes**, XGB objective configs (native default `topk/4294967295` vs `topk/5`), exact 20×32 test shapes, and recomputed realized synthetic winner/top5 selection, NDCG and mean selected return independently. All comparisons matched the frozen summary within 1e−12.

Descriptive **paired-query bootstrap**, 5,000 samples, seed 20261009 (20 generated independent query groups/world; no market block/time-series inference):

| Metric: topk5 minus default | World A point delta | 95% descriptive interval | World B point delta | 95% descriptive interval |
|---|---:|---:|---:|---:|
| Selected mean artificial return (return units) | +.001308 | [−.002748,.006356] | +.001687 | [−.003310,.006526] |
| Top5-hit fraction | 0.000 | [−.20,.20] | +.100 | [−.15,.35] |
| Mean NDCG@5 | +.004723 | [−.008859,.020905] | **−.024901** | **[−.051590,−.000789]** |

Point returns and Top5 hit improvements are **NOT statistically reliable** even on these two toy worlds; no prospective market inference. B NDCG loss has a paired *descriptive* interval not crossing zero; no correction for multiple tests and no generality beyond this fixture.

### QA issue detected and repaired without repeating any fit

Initial synthetic run/pause produced all 36 saved per-fit predictions, but manifest `model_sha.json` erroneously included only the **18 last-world entries** because the in-memory list was reset inside the world loop. Data audit correctly **FAILED** this traceability mismatch. Added a regression test **RED** for the missing `rebuild_model_manifest` function, then implemented filesystem-based independent manifest reconstruction and reran **only checkpoint loading**, not model training. All **five focused R0-N tests GREEN**. Data audit now reports `AUDIT_PASS 36 artifacts hash_verified=36`. This corrects reproducibility bookkeeping, not selection metrics.

### Native pair-generation API control (before R0-N)

Original source `vendor/etf_trader_v2/src/etf_trader/source_only/kernel.py` sets `objective=rank:pairwise` and `eval_metric=ndcg@3` without explicit LambdaRank overrides. In one separate 4-query ×18-candidate/12-round synthetic config probe, saved objective config **default topk UINT32_MAX** gives **exact same predictions** as explicit `topk=18` (max abs 0). Setting `topk=3` gave different scores (max abs .6710433). This is implementation/API evidence; not V2 economics. Official 3.1.3 documentation: https://xgboost.readthedocs.io/en/release_3.1.0/parameter.html.

## Data/Superpowers decision and constraints

**Recommended follow-up:** treat the native pair-generation axis as **the first practical learner candidate**, subject to a stricter gate for **full-ranking quality**, not merely Top1 stability or NDCG@3. Do not vary K around 5 using already studied 2017–2026 data or existing toy-world results. Next:
1. Confirm exact canonical V2 environment source identity, all historical as-of train X/y and yearly MA3 states are stored; current historical original boosters not archived, so reconstructed annual XGB fit cannot be called an original golden replay.
2. Test **exactly this single prespecified** native `topk=5` candidate against the original on *new genuine time-frozen*, causally eligible ETF data, same as-of eligible universe, 125 features, 360 rounds, three seeds, 21/63 horizon, matching MA3 and daily risk/stop/cost engine. If clean new evaluation period too short, report paired daily/monthly P&L instead of falsely precise annual CAGR.
3. Prespecify before results the allowed loss of **NDCG@5 / Top5 opportunity capture**, net return/MaxDD, turnover and vintage-to-vintage exposure deviation, accounting for the NDCG regression observed here. **If full-ranking loss is economically material, NO GO even if Top1 stability improves.**
4. Preserve original learner intact, commit artifacts only in `Test`; no auto-deployment or resampling/re-tuning on Golden/Repeat1/2/3.
5. Separate UNG position risk/reentry concern (L2-O/P) from model-gradient instability, no extra stop-overlay tuning.

**Files:** downloadable support `ETF_Trader_V2_R0N_NativePair_Superpowers_Data.zip`, SHA256 `f2864210192dd4c4cd4c450549d3e45b1f9debb3aa1ed594a9292e9a3d2ea6f8`, **54 entries, 36 saved prediction .npz, source/test/QA and checksum manifest**, ZIP and all checksums verified. Sources in the ZIP are **not** claimed as separately committed GitHub text files in this report.
