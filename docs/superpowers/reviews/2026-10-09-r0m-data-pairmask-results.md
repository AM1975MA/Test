# R0-M — Data review: cost-band masked pairwise objective, synthetic results and decision
**2026-10-09 · `AM1975MA/Test` · `research/v2-xgb-immutable-checkpoints-20261008` · NO GO for current candidate.**

**Source/frozen protocol:** [R0-M preregistration](2026-10-09-r0m-pair-band-prereg.md) commit `ab5f7ee8d5397f2f8173003e0d3e1e98cf38fbfd`, published before new training. Independent analytical Data check of run results, not a new economic simulation. **No market data used to fit any R0-M model**.

## The question answered
A previous read-only price audit (R0-J) found that the eight strict 21-day relevance pair inversions between Yahoo Repeat1/Repeat3 occurred at tiny return gaps, max ~0.0116 basis points, and **0 inversions among pairs admitted under a fixed 20bp return-gap band**. A proposed custom logistic pairwise objective (R0-L) was mathematically tested and ran in XGBoost. Does this `fee_band=.002` MASK itself improve held-out predictions without sacrificing the extreme winners?

**Critical control:** three arms, native XGBoost `rank:pairwise` as original reference; custom full-pairs logistic **0bp** as *causal control*; identical custom full-pairs logistic **20bp** masking. The native-vs-custom difference conflates changed targets, pair sampling, score scale and diagonal Hessian, so **only 20bp-vs-0bp within the custom objective isolates masking**. Hard threshold 20bp was frozen, not chosen by maximizing the old 149-ETF CAGR.

**Method:** two independent synthetic worlds A/B, 32 groups × 32 training rows = 1024, 20 groups × 32 evaluation rows = 640 each, 125 features. One XGB seed `101`, exact **360** rounds, otherwise original depth4, eta .035, subsample .85, colsample .8, min-child Hessian 8, lambda8, alpha.1, hist. Three scenarios: same original data, train-X-only tiny feature jitter, train-Y-only exactly **one** swap of a nearly tied pair with *true* relevance-grade sign reversal and fixed X. The pair separated by 0.1bp, always inside 20bp band. **18 independent fitted synthetic models**, no historical ETFs, no full V2, no financial CAGR. The two world files were stored as completed; no incomplete fit report.

## Primary evidence, evaluated on 20 synthetic test query groups per world

| World | Model | Original Top1 in actual Top5 | Exact best | NDCG@5 | Train-X change: Top1 agreement | Train-Y pair inversion: Top1 agreement |
|---|---|---:|---:|---:|---:|---:|
| A | Native pairwise | 16/20 | 9/20 | .948409 | 18/20 | 19/20 |
| A | Custom logistic, 0bp | 17/20 | 9/20 | .941331 | 20/20 | 19/20 |
| A | **Custom logistic, 20bp** | **18/20** | 9/20 | .938299 | 20/20 | **20/20** |
| B | Native pairwise | 16/20 | 4/20 | .897484 | 17/20 | 17/20 |
| B | Custom logistic, 0bp | **16/20** | **4/20** | .894058 | **20/20** | 19/20 |
| B | **Custom logistic, 20bp** | **15/20** | **3/20** | .893544 | 19/20 | **20/20** |

**Aggregate 40 synthetic groups** (not 40 independent market months): Native Top5 **32/40**, exact winner **13/40**, training-Y Top1 agreement **36/40**, X-only agreement **35/40**, mean NDCG **.922946**; custom 0bp **33/40,13/40,38/40,40/40,.917695**; custom 20bp **33/40,12/40,40/40,39/40,.915921**.

**Mask-only effect:** Baseline Top5 hit A **+1**, B **−1** versus custom 0bp; exact winner A 0, B **−1**; baseline NDCG A **−.003033**, B **−.000515**; mean *artificial* selected return A **−.000576**, B **−.001567**. Thus robustness gains are **not paired with an economic/selection gain** even in a very limited artificial toy. User goal is full V2 tail-upside CAGR, so candidate **FAILS preregistered joint stability × opportunity skill gate**.

## Mechanism and why not a solution yet

The artificially swapped middle-ranked pair stays at a 0.1bp return gap; the 20bp objective excludes it in **both** training vintages, so its gradient/Hessian **does not change**. The masked learner's Top1 also stays fixed 20/20 in both worlds, with zero observed Y-only ranking movement. This verifies a **constructive causal mechanism in an isolated synthetic case** but it is partly guaranteed by how this perturbation was constructed. It says nothing about concurrent X-only Yahoo changes, real corporate-action data revisions, or 20bp **eligibility threshold crossings** (R0-J reported **14 such crossings**). In this new synthetic A/B 4.66%/4.37% of pairs were masked. Previous REAL historical R0-J 20bp mask excludes ~3.789% of 2,333,613 theoretical comparables; real native XGB pair sampler was not reconstructed.

The custom 0bp baseline and native XGBoost are **different learning objectives**, even at zero band. The loss uses all pairs per group and **diagonal approximate Hessian** rather than the native sampler/curvature. No inference about a native pairwise-with-mask implementation is justified.

**Statistical limitations:** only 2 worlds, 20 query groups each and one trained seed; no different future market vintages. Selected-return deltas are from constructed synthetic future returns; NOT financial CAGR, investor capital, Sharpe or daily MaxDD. No per-query prediction dumps retained, so no valid matched group-level uncertainty calculation without new training. The original 20bp threshold is motivated by assumed 0.1% purchase and sale fees but is NOT independently established as the data-revision uncertainty or right indifference margin between alternative ETF positions.

## Verification
- Exact run log documents 18 synthetic fits, two completed worlds, all 360 rounds/booster and no errors.
- 4 new TDD tests observed RED (missing module) → GREEN; together with 8 prior custom-loss mathematical / group / gradient / XGB smoke tests **12/12 tests PASS**; Python syntax compilation PASS.
- Data validation script independently reads finished `results.json`, validates exact fixture/flip/masking counts, computes both worlds and three-arm aggregates, checks precertified outcome `FAIL_JOINT_GATE`.
- Source, `test_r0m.py`, `data_audit.py`, `results.json`, `data_analysis.json`, `run.log`, and original unchanged R0-L code/tests are delivered in the conversation's `ETF_Trader_V2_R0M_Data_20261009.zip`; they were not falsely described as fully committed source to GitHub.

## Decision / next research gate
**NO GO for deploying or financially backtesting this current 20bp hard-mask custom objective.** This rejects the *specific implementation and evidence*, not the research direction of making pair selection robust to genuinely ambiguous outcomes. Next technical design, if separately authorized: preserve the original `rank:pairwise` sampler and training behavior as far as practical while making *just pair eligibility/weighting* robust to known provider-data uncertainty, and evaluate **X-only perturbations** alongside y-only, else it remains an incomplete fix. A smooth weight rather than hard on/off could avoid R0-J's real 20bp eligibility discontinuity; that is **untested**. One frozen learner candidate, independently collected point-in-time data, untouched V2 engine and prospective per-vintage net CAGR/daily MaxDD/turnover/high-upside capture remain mandatory gates. No Original149 performance grid or reruns.
