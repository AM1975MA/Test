# ETF Trader V2 — Superpowers expert triage: tree leaves, Dense MLP, multi-stage screen
**8 Oct 2026 | READ-ONLY architectural review brief; NOT a new experiment, NOT an approved design.**

**Repository scope:** `AM1975MA/Test`, branch `research/v2-xgb-immutable-checkpoints-20261008`. Never modify `Etf_trader`/`Trader_selector`/`vendor/etf_trader_v2`. Do not rerun prior experiments. The related approved direction and revised design are in `docs/superpowers/specs/2026-10-08-v2-model-lifecycle-and-training-stability-v2-design.md`.

**Agent availability:** Superpowers skills for brainstorming, parallel delegation and rigorous review were read. The actual tools in this session do NOT expose a subagent-dispatch action, so no separate specialists have been invoked and this brief is a *handoff*, not independent agent reports.

## Context (established source evidence)

- Canonical **Compact21 XGBoost rank:pairwise**, `max_depth=4` (theoretical maximum 16 terminal leaves/tree), `min_child_weight=8` (Hessian, not a direct minimum number of ETF rows), `learning_rate=.035`, `n_estimators=360`, `reg_lambda=8`, `reg_alpha=.1`, 3 seeds and 125 features: `vendor/etf_trader_v2/src/etf_trader/source_only/kernel.py`, line ~54. Effective number of leaves is unknown until a fitted-tree dump exists.
- Historical forensic `forensics_v1/results/COMPACT21_XGB_FORENSIC_V1.json` isolated sensitivity to **training X and labels**, not fixed-model inference. It did NOT inspect first-divergent tree nodes or split gain margins. Instability of fitted splits is a hypothesis, not a proved root at the node level.
- Already tried and rejected: HGB learner swap, Ridge/Fourier, quantization Q4, label L50, seed committees and block bootstrap, plus risk overlays L2-N/P. The L2-G HGB `max_leaf_nodes=7` experiment is NOT an XGB Compact21 max-leaves sweep and cannot stand in for one. No such sweep may now be launched on reused Original149.
- **Crucial cascade history**: `evidence_v1/results/cascade_v1_ltr_top5_hybrid24/SUMMARY.json`: frozen LTR Top5 followed by Hybrid24, 114 matched monthly 21d Top1 proxy periods; cascade CAGR **15.5992%**, LTR Top1 **22.0631%**, Hybrid24-only Top1 **15.6599%**, **Top5 retrieved eventual global best ETF in 32/114 = 28.0702%**. FAIL. Not full 2,366-day V2 engine.
- **Additional previous rerankers**: `evidence_v1/results/pairwise_reranker_v1/SUMMARY.json` (Top10 logistic pair, FAIL), `reranker_v2_nonlinear/SUMMARY.json` (Top10 XGBRanker, FAIL despite diagnostic CAGR 25.51% vs 22.06% due worse winner containment), `reranker_v3_target21/SUMMARY.json` (21d shortlist relevance, FAIL), `reranker_v4_best_classifier/SUMMARY.json` (binary shortlist-best XGBClassifier, FAIL). **DO NOT RETEST** Top5/Top10 Hybrid24 or four shortlist rerankers, nearest K tweaks on same 2017–26.
- Literature is **motivation, not ETF V2 evidence**: [XGBoost tree parameter documentation](https://xgboost.readthedocs.io/en/stable/parameter.html) (`max_depth`, `max_leaves`, `min_child_weight`, `gamma`, `grow_policy`); [Gu, Kelly, Xiu 2020](https://doi.org/10.1093/rfs/hhaa009) (nonlinear trees and neural networks matter in stock cross-section, data regime not transferable to 149 ETFs); [Keras Dropout](https://keras.io/api/layers/regularization_layers/dropout/) and [weight regularization](https://keras.io/api/layers/regularizers/); [RankFlow SIGIR 2022](https://doi.org/10.1145/3477495.3532050), [LCRON ICML 2025](https://proceedings.mlr.press/v267/wang25fc.html) (cascades face downstream sample-selection and recall errors).

## Direction 1 — XGBoost leaf count/structure (**priority HIGH — closest to proven anomaly**)

**What might help**: control how splits compete so tiny X/y changes do not rewire many trees. Candidate axes in official XGBoost API: `max_depth`, `max_leaves`, `grow_policy` depthwise/lossguide, `min_child_weight`, split-gain threshold `gamma`, binning. None is a proven robustness fix; reducing tree capacity can erase rare nonlinear tail signals, and altering many axes together precludes attribution.

**First ask for proof, NOT a grid:** from newly saved genuine as-of boosters or *tiny synthetic grouped ranking fixtures*, compare actual leaf occupancy, node structure, first divergent tree, split gains/candidate near-ties, gain-weighted location and whether a changed node affects high-exposure top-ranked ETF. Do not infer gain runner-up from a final dump if absent. `max_depth=4` currently caps leaves at 16 and `min_child_weight=8` means Hessian threshold, not 'minimum eight samples'.

**Decision rule before real data**: use **one** structural axis only if a node-level mechanism is documented; prefer preserving nonlinear top-tail capture and minimize unnecessary reruns. Any numeric leaf settings must be fixed without peeking at old Original149 performance.

## Direction 2 — compact regularized Dense neural ranking model (**priority MEDIUM — genuine alternative, unproven**)

User proposes stacked `Dense` layers. **Dense stacking increases function capacity; it does not itself reduce overfitting.** To control variance, specialists may consider small widths / shallow residual or MLP, `weight_decay`/L2, dropout, early stopping using *purged chronological* folds and a ranking loss aligned with monthly query groups (`pairwise` or smooth listwise). A model trained against regression error alone is not necessarily optimized for top ETF selection.

**Major risk**: 149 tickers × ~113 evaluation months is not ~16,837 statistically independent market experiments; cross-sectional rows within a month share regime. Temporal purging must cover label horizon and ETF cluster/category leakage. Neural optimization can itself vary with seed and revised data; 'smooth network' does NOT imply stable trained ranks. Prior Fourier/Ridge instability/quality compromises are warning signals, not a direct neural-net veto.

**Study-only next step**: request parameter-count and capacity analysis, proof that monthly query ranking loss and missing-data handling are well-defined and chronological, seed perturbation/fitting stability on synthetic fixtures; **no architecture sweep** over old 149 ETF labels. A future single candidate gets a prospective full-V2 economic test after preregistration.

## Direction 3 — broad high-recall funnel (~149→37/38→few) (**priority CONDITIONAL — substantial prior negative evidence**)

Unlike previous Top5/Top10 freezes, the first stage would retain ~25% of the universe (roughly 37–38 ETFs) and a second *new* selector would focus on survivors. It **could** simplify final ranking and allow specialist training on difficult candidates, but it introduces a hard nonrecoverable failure: any true extreme winner screened out is gone permanently. The goal for stage1 is **near-perfect recall of high-value winners**, not low MSE or average NDCG.

- Before any learning: use **existing** cached OOS first-stage rankings and **existing** matured labels to audit recall/retention of realized global Top1/Top5 and of economically relevant V2 exposures among Top~25%, with no new fit and no new choice of K on CAGR. This is **new descriptive diagnostic**, not an independent holdout; if high-value retention is poor, STOP funnel.
- Evaluate stage1 stability across raw vintages on *same month and identical membership*, e.g. Jaccard retention, false negatives of major positive-tail events; only then formulate a gate.
- If stage1 is a deterministic *filter*, require an ex-ante eligibility/fundamental rationale and that rare explosive assets aren't trivially thrown away. If stage1 is a model, note sample-selection bias of stage2 (trained on survivors only) and shifting training populations; literature suggests coordinating upstream/downstream selection, not naive independent training.
- Removing 75% has no automatic benefit to statistical reliability. Fewer eligible labels and dynamic memberships can in fact worsen fit stability. Three cascading filters may compound these effects.

## Independent specialist assignments (PREPARED BUT NOT DISPATCHED)

1. **Boosted-tree internals / numerical ML**: adjudicate node topology/leaf-vs-depth vs pairwise gradient discontinuities; one structural falsification probe, failure risks to top-tail. Deliver: proof inventory, one justified axis or NO-AXIS, synthetic-only first.
2. **Deep ranking / statistical generalization**: compare small Dense MLP and suitable pairwise/listwise loss, parameter-to-effective-sample relationship, regularization and temporal purging; distinguish training noise from inference smoothness. Deliver: go/no-go to prepare one candidate, no financial sweeping.
3. **Information retrieval / multi-stage LTR**: read all five previously rejected cascade/reranker experiment reports. Assess ~25% Top-K **recall ceiling** using frozen predictions only, survivor sample-selection bias and near-perfect extreme-positive capture. Deliver: diagnostic gate and explicit ban on Top5/Top10 reruns.
4. **Quant portfolio / adversarial methodological reviewer**: define meaningful full-V2 economic opportunity-regret metrics, pro forma turnover/fees, cross-vintage poor-case and daily maxDD; ensure same-universe/same-raw-snapshot comparison; reject proxy NDCG/CAGR as proof, control multiple testing. Require new prospectively timestamped non-burnt evidence for economic promotion.

Every reviewer must return: `source-derived proven facts`, `hypotheses only`, `already-tested overlap`, `first falsifier`, `potential CAGR harm`, `recommendation`. The current chat lacks a callable subagent runner, so these are review briefs and not completed independent agent reports.

## Gating recommendation — no code/test authorization

**Stage R0: evidence-only review** (no training): inspect available tree dumps; compute existing frozen-retriever Top25% oracle recall only if needed to answer user approval; no reruns of old rankers; compare three technical directions against source-supported failure modes.

**Stage R1: single synthetic mechanism checks** after approved design: targeted tree-node axis diagnostics, *or* compact MLP API plausibility, no Original149 retuning. Stage R1 is not an excuse to optimize 3 methods retrospectively.

**Stage R2: at most one prospective challenger** with preregistered feature/universe/version cutoff and economic non-inferiority full-V2 gates per vintage, downside, fees, concentration and extreme upside capture. If no mechanism and no high-recall funnel, recommend NO ACTION and preserve V2.

This file is a review memo, NOT a revised approved spec or implementation plan. New branch plan's Track B may be amended after the user approves which direction(s) merit formal design work.
