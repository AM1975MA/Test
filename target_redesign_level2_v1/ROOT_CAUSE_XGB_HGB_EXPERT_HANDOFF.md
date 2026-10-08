# ETF Trader V2 — Evidence handoff for independent reviewers (NO repeat experiments)

**Date 2026-10-08. Repo:** `AM1975MA/Test`, branch `research/target-redesign-level2-v1`. **Do not change `Etf_trader` or `Trader_selector`.** This is a *literature/code/evidence review* assembled for independent expert agents if/when that capability is connected. No subagents/independent external consultants were run in this session. Absolutely NO old tests should be rerun, no new model fitting, and no backtest parameter search on burned Original149.

## Executive correction: HGB is not the production root

The canonical Annual V2 Compact21 uses `XGBoost` with objective `rank:pairwise`, 360 iterations, 3 seeds (101/202/303), 125 features. Confirm in `vendor/etf_trader_v2/src/etf_trader/source_only/kernel.py` and `models.py`. MA3 hybrid in `vendor/etf_trader_v2/src/etf_trader/ma3/hybrid_producer.py` uses ExtraTrees + XGBoost. **HistGradientBoostingRegressor (HGB)** was tried in **L2-G** as `HGB_DIRECT` and `HGB_TEACHER50` *alternatives*, NOT the original Compact21 learner. The separate old `transport/hgb25_full_chain_20260919` is marked `RECONSTRUCTED_NOT_ORIGINAL` for some helpers and must not be taken as proof of original V2 source identity.

**Narrowly established amplification point:** **annual Compact21 XGBoost model fitting**, with both feature perturbations and label perturbations capable of triggering large fitted-score differences. It is **not proven that this single amplifier accounts for all 11.542 percentage points** between Golden historical and October 2 Yahoo; MA3/KMeans membership and realized execution-price differences are also possible channels and have previous evidence of sensitivity.

## Main evidence — no re-execution needed

1. **Yahoo input perturbation**: `gap_analysis/results/yfinance_repeatability_v1/RESULT.json`: same date rows and volume; 137/149 ticker CSVs differ; max relative OHLC difference `2.511e-6`; max adjusted daily close-return difference `3.796e-6` across pairs. **No missing dates**. This is a small-data perturbation test, not proof all historical provider revisions are comparably small.
2. **Original full V2**: `compact21_stability_v1/results/FULL_REPLAY.json`, `BASE`: Repeat1 `29.7534%`, Repeat2 `30.8437%`, Repeat3 `34.6771%` CAGR; vintage span **4.9236 pp**; full-pipeline daily Top1 disagreement **~30.1–33.3%**. All are development-period data reused many times; not 3 independent market trials.
3. **Golden baseline** `43.145952%` audited against its own frozen OHLCV Parquet; fresh 2026-10-02 matched canonical source `31.603995%`, delta **−11.541958 pp**: `gap_analysis/results/BASELINE_LINEAGE_DECISION.md`, `CROSSED_REPLAY_MATRIX.json`, `SOURCE_IDENTITY_43_VS_31_V1.json`. Canonical source hash gated; historical build environment not independently proven bit-for-bit. Known top-level changed factor is historical **raw-data vintage**; no controlled allocation yet between score changes, cluster membership and execution prices.
4. **CAUSAL MECHANISM IS ALREADY EXPERIMENTALLY ISOLATED IN FOUR YEARS**: `forensics_v1/results/COMPACT21_XGB_FORENSIC_V1.json`, pair Repeat1/Repeat3, years 2017/2020/2023/2026, **same held-inference input**:
   - change inference features only with fixed fitted model: **0% Top1 disagreement**, mean percentile rank-MAD `0.0001051`;
   - re-fit full on different raw vintages: **43.75% Top1 disagreement**, mean rank-MAD `0.05964`;
   - training X-features changed, Y-labels fixed: **62.5% Top1 disagreement**, rank-MAD `0.05329`;
   - training Y-labels changed, X-features fixed: **58.33% Top1 disagreement**, rank-MAD `0.04497`;
   - integer relevance label disagreement only `~0.00047–0.00070` training rows (0.05–0.07%): `forensics_v1/results/COMPACT21_LABEL_STABILITY_V1.json`. Attribution components do **not** sum as percentages: interactions and discrete winner changes mean the top1 disagreements need not be additive.
5. **Matched full L2-D XGB vs Ridge**: `target_redesign_level2_v1/L2D_RESULTS.md`: Repeat2-common-input Top1 agreement XGB `45.13/56.64/46.90%` vs Ridge **100%**, but original XGB Top1 realized Top5 selection **19.17%** vs Ridge **7.96%**, selected next21 mean net return **2.4605% vs 1.7618%**; top1-only diagnostic, not V2 CAGR. The Ridge target was continuous percentile whereas XGB target was rounded integer relevance; a pure same-target learner-only causal attribution is not proven.
6. **HGB alternatives NEGATIVE (L2-G)**: `L2G_RESULTS.md`, 90 mature months: native `HGB_DIRECT` Top5 selected **6.67%** and next21 mean **+1.1074%**; `HGB_TEACHER50` **11.85%**, **+1.9505%** vs frozen XGB **21.48%**, **+2.7002%**; HGB Top1 agreement **~64–69%**, below required 90%. Full portfolio V2 not performed for these variants; do not invent its CAGR.
7. **Tried, failed or qualified:**
   - `COMPACT21_LABEL_STABILITY_V1`: coarsening relevance to 50 levels (`L50`) improves label agreement but Top1 disagreement **54.17% vs 43.75%** on the four-year diagnostic, i.e. worse.
   - `compact21_stability_v1/results/FULL_REPLAY.json`: `Q4` feature rounding reduced full V2 vintage CAGR span **4.924→2.245 pp** but reduced average CAGR **31.758→29.013%** and made mean Top1 disagreement **31.38%→34.09%**. NOT a root fix.
   - `L2E` Ridge/XGB score blend and Ridge final selection fail joint gate despite some proxy upside.
   - `L2F` 75% Ridge/25% XGB *capital sleeve* reduces exposure to XGB instability by reducing its notional; does not stabilize the fitted ranker; proxy, not full V2.
   - `L2G` HGB direct/distilled fail ability and Top1 gate.
   - `L2H` Fourier consistency/smooth nonlinear ranker greatly stabilizes scores but erases top-opportunity capture; common-perturbation-seed posthoc correction improves stability, still low skill.
   - `L2I` 3-vintage XGB committee mean/vote2 quality gain is exploratory but leave-one-vintage-out common-input Top1 agree only **65.5–69.9%** and full decision skill NOT validated; not feasible as historical causal multi-vintage policy.
   - `L2J` month-block bootstrap XGB, 54 fits, common-input Top1 agree **31.8–40.9%** vs XGB **42.4–57.6%**, NDCG **0.517 vs 0.569**, selected return **1.95% vs 3.39%** matched; FAIL.
   - `gap_analysis/results/canonical_v2_determinism_control_v1/RESULT.json`: **six independent same-byte full V2 replays 30.8437049% identical**; nondeterministic code/process on unchanged data is not the observed cause.

## Shortlist of interventions NOT YET TESTED (expert review before fit)

### Priority 0 — production data reproducibility, NO trading change
- Implement an **append-and-version point-in-time data store** of original vendor responses, corporate-action adjustments, frozen features and hashes per training cutoff. Never silently rebuild all historical training on a provider’s revised adjusted bars; distinguish permitted corporate-action restatements and audit price consistency. Freeze fitted model per annual cutoff and persist its exact trained trees, feature schema, groups and training-row IDs. Re-pulling same time interval must reuse the same trained model, not silently change the decision model. This prevents snapshot refresh from triggering a brand-new tree topology on unchanged economic information.
- This preserves the **exact original policy on whichever snapshot/checkpoint is frozen**, hence does not introduce an algorithmic CAGR loss on that snapshot. It **does not** guarantee the Golden 43% on a different vintage, repair bad data, or stabilize *future mandated legitimate retrains*. These limitations must be prominent.
- Diagnostic new vs previous: do NOT rerun the existing six identical-source determinism tests; instead review whether current live pipeline ever retrains on revised ancient Yahoo history and whether the checkpoint lifecycle provides immutable model semantics.

### Priority 1 — retain XGB split topology during *legitimate* refreshed fits
- Explore **structural warm-start / leaf-refresh only** from an independently frozen as-of annual XGBRanker model: official XGBoost `process_type=update, updater=refresh, refresh_leaf=1` recalculates leaf stats/values on new data **without rebuilding split topology**. Source: https://xgboost.readthedocs.io/en/release_3.2.0/treemethod.html . Alternative `refresh_leaf=0` updates stats only and is a nearly no-op on predictions, not a proof of robustness. The supported XGBoost API + exact `rank:pairwise`/QuantileDMatrix behavior must be validated in the frozen environment; no financial results yet.
- Training/target semantics must respect annual cutoff; an original base checkpoint must be **causal as of that cutoff**, not fitted using full 2026 for a 2017 backtest. Requires time-as-of checkpoint archives or a valid retrospective simulation carefully labeled.
- This is unlike replacing XGB with a smooth Ridge/Fourier, unlike switching to HGB, and unlike averaging 3 new separate XGB tree structures. Main risk: stale splits may cease capturing changing opportunities and CAGR may decline; *not pre-approved*.

### Priority 2 — controlled tree-split sensitivity for legit occasional full rebuild
- Diagnose tree structural divergence after **first** different learned split in same-seed same-year fit on equally supported rows and mature labels, including gain margin between best and runner-up split, histogram bin edge changes, per-group ranking gradients and interaction. This is **not** the already-completed 2x2 feature/target attribution. From that evidence decide if fixed as-of histogram cut points or split-tie deterministic preferences are justified. Must not simply repeat 4-decimal Q4 rounding, 50-bin target coarsening, block bagging or Ridge blends.
- Scikit-learn HGB is also histogram based (max_bins), so replacing XGB with HGB alone does not remove split discontinuities: https://scikit-learn.org/1.7/modules/generated/sklearn.ensemble.HistGradientBoostingRegressor.html .

### Priority 3 — secondary MA3 clustering channel
- MA3 cluster/sector derived features and KMeans assignments are already known potential extra amplifier `gap_analysis/results/BASELINE_LINEAGE_DECISION.md`; quantify their **incremental** effect only *after* training-tree pathology is pinned down, not assume they explain entire Golden gap. Consider label-alignment, as-of cluster checkpoint and hysteresis when updating cluster membership, but avoid stale economic regimes and no threshold searches on consumed Original149.

## Objective and economic guardrails

- Primary outcome: **full V2 Annual**, identical three frozen vintages, code, 2017–2026 2,366 daily sessions, 0.1% modeled execution cost, real daily MaxDD, CAGR *per* vintage and worst vintage, turnover, daily Top1/Top2 and P&L dispersion, rather than Top1-only CAGRs, NDCG or Rank-MAD as a surrogate.
- Keep **all 149 ETF universe candidates, canonical 125 Compact21 + MA3, pairwise ranking objective, concentration, Tail, V6, HighCAGR24, selection and stop policy** fixed for first structural hypothesis. No 2017–2026 post hoc tuning. Check decision-margin sensitivity and coherence at period transitions. No optimizer could legitimately promise unchanged CAGR in previously unseen future data.
- Predefine *before* new results economic **non-inferiority per vintage** (not mean alone), plus measurable reduction in common-input training-induced Top1 instability and full-pipeline CAGR span, matching daily DD and fee accounting. If economic gate fails, reject even if score agreement improves.
- A robust live release also needs truly prospective time-stamped as-of raw snapshots and unseen months; repeats of revised 2017–2026 history are one development market.

## Independent specialist reviewer assignments — prepared, NOT dispatched

1. **Gradient-boosted ranking / XGBoost internals reviewer:** verify 2x2 X/Y finding and whether the root is split-topology instability, rank:pairwise gradients/threshold ties or XGB histogram sketch; evaluate fixed-tree refresh compatibility and propose strict structural metrics. **Adversarial challenge:** could tree splits differ extensively yet allocations remain economically stable? What proves the earliest important split?
2. **Numerical reproducibility / market-data lineage reviewer:** audit loss of point-in-time training identity, adjusted OHLC price-vintage drift, corporate actions, feature-group masks, quantile cuts and KMeans state. Deliver minimal immutable datastore/checkpoint design with no data leakage. **Adversarial challenge:** what changes in legitimate future information vs merely vendor-revised past?
3. **Statistical learning / robust optimization reviewer:** audit prior trials, multiple testing and limits of N=113 monthly market states; assess economically meaningful continuity constraints that preserve upside without fake no-change gates. **Adversarial challenge:** why would local consistency regularization not erase the original opportunity skill as in L2-H?
4. **Quant portfolio and execution reviewer:** reconstruct what "no significant CAGR loss" actually means on **matched full V2**, and insist on daily DD, costs, concentrated winner attribution, drawdown regime and 43% historical-vs-raw difference. **Adversarial challenge:** is Top1 exact-match instability the correct economic objective, or should we focus on money-weighted decision regret / return dispersion while not destroying signal?

**Output sought from each reviewer:** (a) identify already-proven statements, (b) top two hypotheses not already tested, (c) falsification checks, (d) whether no-action/checkpoint is preferable to refit, (e) failure risk to CAGR, (f) explicit NEVER RETEST ledger. Reviewers must independently inspect the linked evidence, not invent experimental outcomes. Any later combined technical recommendation must highlight dissent and unresolved questions.

## Index
- `forensics_v1/results/COMPACT21_XGB_FORENSIC_V1.json`, `forensics_v1/results/COMPACT21_LABEL_STABILITY_V1.json`
- `target_redesign_level2_v1/L2D_RESULTS.md`, `L2E_RESULTS.md`, `L2F_RESULTS.md`, `L2G_RESULTS.md`, `L2H_RESULTS.md`, `L2I_RESULTS.md`, `L2J_RESULTS.md`
- `compact21_stability_v1/results/FULL_REPLAY.json`, `gap_analysis/results/yfinance_repeatability_v1/RESULT.json`
- `gap_analysis/results/BASELINE_LINEAGE_DECISION.md`, `SOURCE_IDENTITY_43_VS_31_V1.json`
- `vendor/etf_trader_v2/src/etf_trader/source_only/kernel.py`, `models.py`; `vendor/etf_trader_v2/src/etf_trader/ma3/hybrid_producer.py`.
