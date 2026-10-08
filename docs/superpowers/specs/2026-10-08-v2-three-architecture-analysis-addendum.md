# ETF Trader V2 — Technical Analysis Addendum: XGBoost Leaves, Dense Ranking, 25% Recall Funnel
**2026-10-08 | Superpowers architectural review | analysis-only scope CONFIRMED by user.**

**Repository:** `AM1975MA/Test`, branch `research/v2-xgb-immutable-checkpoints-20261008`.
**Companion evidence:** [expert triage](../reviews/2026-10-08-v2-xgb-leaf-mlp-cascade-expert-triage.md), [revised lifecycle/stability design](2026-10-08-v2-model-lifecycle-and-training-stability-v2-design.md), [Track B research plan](../plans/2026-10-08-v2-xgb-training-stability-research.md).

## Decision and scope

The user approved including **three new research directions in the technical-analysis phase only**:
1. XGBoost number/structure of leaves;
2. compact stacked Dense neural ranking model with *explicit* controls against overfitting;
3. multi-stage ranker with a high-recall first stage keeping ~25% of the original population (149→37/38), then selecting winners among survivors.

This approval **does not authorize** any XGBoost/MLP fitting, hyperparameter sweep, financial backtest, new data acquisition, source-code implementation, system deployment, agent assertions or production changes. Existing ROI estimates are evidence from prior distinct experiments, not predictions for any new model. The user expressly wishes to avoid rerunning failed tests. The full V2 is the reference, not a substitute model being freely optimized.

## Previously established facts vs untested hypotheses

**Facts:** canonical XGB Compact21 uses `rank:pairwise`, `max_depth=4`, `min_child_weight=8`, `n_estimators=360`, 3 seeds, 125 features; 4-year diagnostic shows stability of fixed-model inference but high sensitivity to perturbing training X or labels. It has **not** isolated split-node root cause. HGB, Ridge/Fourier, Q4, L50, cross-vintage committees and temporal bootstrap have already failed joint requirements. The separate prior LTR Top5→Hybrid24 cascade and four Top10 rerankers were rejected on Original149 (source: `evidence_v1/results/cascade_v1_ltr_top5_hybrid24/SUMMARY.json`, `pairwise_reranker_v1/SUMMARY.json`, `reranker_v2_nonlinear/SUMMARY.json`, `reranker_v3_target21/SUMMARY.json`, `reranker_v4_best_classifier/SUMMARY.json`). Those are **monthly single-ETF Top1 proxies, not full-V2 CAGRs**.

**Hypotheses only:** leaf constraints may reduce split-topology bifurcation; Dense ranking networks may provide alternative nonlinear smoothness with regularized training; retaining 37/38 ETFs may keep enough extraordinary winners while simplifying final ranking. **No such improvement is demonstrated**, and independent subagents have not supplied opinions.

## Three distinct analytical workstreams (READ-ONLY FOR NOW)

### Workstream S1 — tree internals, effective leaves and splits (first priority)

**Expert:** gradient-boosted ranking / XGBoost internals.

- Inventory **already saved** authentic UBJ/JSON tree dumps from the exact as-of fits; if unavailable, record `HISTORICAL_BOOSTER_NOT_ARCHIVED`; prediction arrays cannot recover split structure.
- Contrast *effective* leaf count, occupancy/Hessian, gain, tree depth, branch feature/thresholds and whether major position scores depend on unstable nodes. `max_depth=4` only imposes theoretical ≤16 leaves; `min_child_weight=8` is a Hessian condition, **not ≥8 tickers per leaf**.
- Differentiate a structural near-tie in first divergent split from a changed distribution of pairwise rank labels or XGB histogram cuts. Do not infer the margin between top and runner-up candidate splits from a final tree dump.
- Deliver one of: `MECHANISM_EVIDENCED`, `INSTRUMENTATION_REQUIRED`, `NO_SUPPORT`; list **at most one** change axis `max_leaves / grow_policy / minimum Hessian / gamma` justified by evidence, not an ex-post grid.
- Stop if there are no authentic boosters or no established link between structural flips and economically influential Top1/top2 decisions; separate, later authorization needed even for synthetic model fits.

### Workstream S2 — Dense deep ranking model and real generalization (second priority)

**Expert:** deep learning-to-rank, financial ML and statistical validation.

- First estimate *effective* sample size (month/query groups and market regimes), parameter count and the disparity vs 16,837 correlated ETF-month rows. Check time-purged CV with 21d/63d label maturity, point-in-time universe membership and correlated ETF sectors.
- Distinguish `Dense` stacking (**capacity increases**) from *actual* variance-control mechanisms: constrained width/low parameter count, weight decay/L2, dropout, early stopping, robust pairwise/listwise ranking losses, feature normalization fitted only on past data. These are technical design candidates, **not already-authorized parameter combinations**.
- Require multi-seed and small-data-perturbation **training** stability, not merely deterministic/smooth inference; prioritize extreme-winner capture over MSE. Explicitly explain why previous Ridge/Fourier/HGB negatives do not falsify a well-regularized MLP but do warn of an accuracy–robustness trade-off.
- Deliver: `FEASIBLE_ON_AVAILABLE_AS_OF_SAMPLE` / `UNDERPOWERED` / `UNKNOWN` with capacity budget and one prospective **predeclared** neural candidate design, if warranted. No training yet.

### Workstream S3 — recall-preserving cascade, first stage retains 25% (conditional priority)

**Expert:** multistage ranking / information retrieval and quant selection.

- Distinguish this 149→37/38 high-recall proposal from **already rejected** Top5 LTR→Hybrid24 and Top10 rerankers. Do not rerun or merely vary Top5/10 to Top37 on the same used data seeking higher CAGR.
- From already archived, genuinely **out-of-sample** rank forecasts and mature realized winners, derive an *analysis-only* **fixed 25%** first-stage oracle retention: (i) actual best 21d/63d ETF globally; (ii) members of the top-positive tail, e.g. top5 realized winners; (iii) eventual high-contribution V2 selected ETF, when the correct frozen ledger exists. Record exact dates, universe, cutoff and assets covered. Keep `37/38` fixed; never choose K after looking at returned performance.
- Compare *same-date / same-universe* shortlist membership stability across Yahoo vintages using e.g. Jaccard and **missed-extreme-event rate**. If ranking scores exist only on a different representation, state `UNIDENTIFIABLE`; never extrapolate Top5 28.07% retention to Top25% as a measurement.
- Address biased Stage2 training only on Stage1 survivors, survivor-distribution shift, tie-handling, stage coupling and failed-filter irreversibility.
- Gate: `HARD_SCREEN_CAN_PRESERVE_EXTREMES` only if preregistered high recall and vintage robustness are demonstrated, otherwise `REJECT_HARD_SCREEN`. No stage2 training or full-V2 backtest yet.

### Independent adversarial methods and economic reviewer

**Expert:** quantitative portfolio construction, research-statistics and execution.

- Audit all three proposals **against the complete V2**, not against an irrelevant Top1 proxy. Challenge causal maturity, same-universe equivalence, current full-V2 concentration, fees, drawdown, and tail-opportunity erosion.
- No more hyperparameter sweeps on burned Original149 or unblinded Holdout70/120; these are not fresh validation. New investment-grade decision only on new *prospective point-in-time* data, with one frozen candidate and predeclared per-vintage no-material-CAGR-harm gate.
- A method that reduces rank-MAD or increases agreement but lowers capture of extreme positive opportunities is a **NO GO**, regardless of reported robustness.

## Deliverables and gate

**R0 (now authorized):** source/evidence inventory, independent review briefs, technical feasibility assessment, report of unmeasured quantities, *no model fitting*. If existing frozen artifact allows a simple **read-only statistic** (such as one fixed Top25% recall), report it as a retrospective diagnostic, NEVER as prospective test or new CAGR.

**R1 (NOT AUTHORIZED NOW):** code/synthetic XGBoost/MLP fits, tuning, or other training — requires separately reviewed design.

**R2 (NOT AUTHORIZED NOW):** any financial test/candidate promotion — requires one preregistered intervention and genuinely new as-of observations, with the full-V2 daily cash/fee/stop engine.

**Agents:** task specifications for four truly independent specialists are written in the companion review. This session exposes Superpowers **skills** but no callable subagent dispatch; do not claim they were run. Review can be conducted directly against accessible frozen GitHub evidence only, with transparent attribution.

**Required R0 outcome:** 1-page evidence matrix per direction (past overlap, unique mechanism, observability, principal financial hazard, first falsifier and no-test stop). Then recommend **zero or one** workstream to advance to a distinct implementation proposal; do not automatically advance all three. 
