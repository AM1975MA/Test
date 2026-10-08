# V2 XGBoost Intrinsic Training Stability — Research/Validation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Determine which tree-building mechanism amplifies nearly identical annual Compact21 training data into materially different rankings and establish **one** genuinely new, falsifiable stabilization approach that does not sacrifice extreme-opportunity selection.

**Architecture:** Preserve the canonical XGBoost `rank:pairwise` baseline and reuse the research evidence; instrument raw tree topologies/candidate split margins on **existing saved booster artifacts where present**, otherwise on small **new synthetic data**. Freeze one causal hypothesis before any future real-data training. Keep historical cache/lineage and prospective economic validation separate; use the companion Model Lifecycle plan to ensure new models remain traceable.

**Tech Stack:** Python 3.13.5, XGBoost 3.1.3, numpy 2.3.5, pandas 2.2.3, pytest, JSON and XGBoost tree dumps. Synthetic only for new fitting at this stage.

**Spec:** [Revised V2 lifecycle & stability design](../specs/2026-10-08-v2-model-lifecycle-and-training-stability-v2-design.md).

## Global Constraints

- Only `AM1975MA/Test`, branch `research/v2-xgb-immutable-checkpoints-20261008`. Do not modify `Etf_trader`, `Trader_selector`, vendor source or production V2. No merge/promotion.
- **DO NOT REPEAT** L2-D/E/F/G/H/I/J, HGB/Ridge/Fourier, Q4/L50, 75/25, bootstrap, multi-vintage committees, L2-N/P, or 149 ETF 2017–26 full V2 replay. Use the archived evidence as input.
- 149-ticker Original149 Repeat1/2/3 and historical Golden are **already highly explored**; they are not independent holdouts, and 43.146% Golden cannot be attributed entirely to XGB.
- New training experiments in Tasks 2–3 exclusively synthetic; no financial fit using the 149/120 ETF snapshots. Task 4 freezes a future experiment, it does not execute it.
- Original architecture stays original: 125 features, annual rank `rank:pairwise`, three seeds, 360 rounds, MA3 and risk engine unchanged in any future matched economic test. Fewer rounds allowed only for labeled synthetic diagnostics.
- The prior XGB four-year factorial proves independent X/y training sensitivity but **not** the first divergent learned split, histogram bin edge or gradient. Never report mechanism confirmed if only model ranking diverges.
- Split-topology agreement, Top1 agreement, NDCG, CVaR, CAGR and drawdown are different things. A stable but unprofitable model is a failure of the stated aim.
- Before any new money-bearing intervention, preregister **one** policy, thresholds and prospectively timestamped sources. Do not tune fixed-tree duration, split regularization, gain margins, seed or vote weights on old Original149.
- Candidate-approval lifecycle (champion/challenger, valid until, model universe, feature schema) is defined in companion [Plan A](2026-10-08-v2-model-lifecycle.md).

## User-approved R0: read-only review of three additional architectures (no training)

**User decision (8 October 2026):** add to technical analysis **(S1) XGBoost leaf count/structure; (S2) small regularized stacked Dense learning-to-rank network; (S3) high-recall 149→37/38 ETF first stage plus optional later ranking of survivors**. This is **approval of analysis only**; it does not supersede the requirement for separate approval before any implementation or training. The precise questions, evidence sources, failure gates and independent-expert briefs are in the [three-architecture analysis addendum](../specs/2026-10-08-v2-three-architecture-analysis-addendum.md).

**R0 work packets to complete in order; all read-only, no new tests or retraining:**
- [ ] **R0a — Trees expert inventory:** check whether authentic existing trained boosters/tree dumps survive; summarize effective leaf/branch observability, `max_depth=4` and `min_child_weight=8` semantics; designate first possible split-bifurcation falsifier. Explicitly label unobserved split counts/runner-up gains `UNKNOWN`.
- [ ] **R0b — Neural ranking expert feasibility:** outline one compact Dense candidate architecture class without selecting a width/depth from historic returns; account for effective monthly sample size, query-level ranking loss, signal maturity and nested purged chronological early-stopping policy. No model fitting.
- [ ] **R0c — Cascade expert no-repeat audit:** cite `evidence_v1/results/cascade_v1_ltr_top5_hybrid24/SUMMARY.json` and all `reranker_v1–v4` failures. Assess **fixed 25%** OOS first-stage recall of exceptional winners from *already frozen* predictions if those files are accessible, otherwise `INSUFFICIENT_ARTIFACTS`; **never tune K**, refit, or claim Top5/Top10 experience directly measures Top25% performance.
- [ ] **R0d — Quant adversarial review:** challenge risk of losing rare upside, available effective independent months, transaction costs and required full-V2 economic guardrails, and separate score stability from fit robustness. A new model with lower CAGR is not a success.
- [ ] **R0e — Integrated decision:** publish source-grounded R0 matrix and **no more than one** proposed new mechanism for subsequent approval; if none is demonstrably promising, `NO_CANDIDATE` and STOP.

**Existing Tasks 1–5 below describe a separate, *future* research implementation**. In particular Tasks 2–3's synthetic fittings are NOT included in R0 approval. No financial or synthetic model trainings have been authorized by the user's most recent approval. **Actual independent agent dispatch is unavailable in this session**; do not conflate detailed reviewer briefs with executed reviews.

---

## Review Focus

1. **Already-used old evidence**: no re-training on preexamined original 149 to fill missing old booster files; label 'historical split attribution unknown'. Task 1.
2. **Tree comparison is invariant to JSON node order**: use node-id and learned split attributes, not text dump order. Task 2.
3. **Altering label alone changes gradients and potentially splits**, but topology difference cannot be called label *causation* without matched X, group, rounds and seed. Tasks 2–3.
4. **Small synthetic noise vs real provider revisions**: synthetic demonstration is API/mechanism evidence, not evidence of the size of 2017–26 CAGR loss. Tasks 3–4.
5. **Performance selection leak**: no choice of winner by full-history Golden/Repeat CAGR; compare matched same-universe portfolio on future observations only. Task 4.

---

### Task 1: Freeze research baseline, enumerate already tried approaches and available boosters

**Files:** Create `target_redesign_level2_v1/training_stability_v1/EXISTING_EVIDENCE.md`; Create `target_redesign_level2_v1/training_stability_v1/ARTIFACT_INVENTORY.json`.

**Interfaces:** consumes GitHub evidence paths in the revised spec; outputs fixed list of existing model/score/feature provenance, available original `.ubj` and tree dumps (if any), negative experiments and unresolved mechanism. Read-only research.

- [ ] Read the existing four-year Compact21 forensic and L2-D/L2-G/L2-H/L2-J/Q4/L50 reports, alongside L2-Q synthetic XGBoost3.1.3 probe; do **not** refit them. Record actual numeric endpoints with exact sources and flag any inconsistent narrative.
- [ ] Inventory accessible archived booster files vs `pred_*.npy` and older `scores_YEAR.csv`. Mark `SPLITS_NOT_RECOVERABLE` whenever only predictions survive; no post hoc alleged authentic tree topology.
- [ ] Write `EXISTING_EVIDENCE.md` and `ARTIFACT_INVENTORY.json` with method blacklist and source digests.
- [ ] Verify each cited path exists through GitHub read API and inventory JSON parses. No financial fitting.
- [ ] Commit `docs: freeze proven XGB training-instability evidence and nonrepeat ledger`.

### Task 2: Build faithful tree-topology comparison/structural instrumentation

**Files:** Create `target_redesign_level2_v1/training_stability_v1/tree_diff.py`; Test `target_redesign_level2_v1/training_stability_v1/tests/test_tree_diff.py`.

**Interfaces:** `canonical_tree_structure(booster_json_dumps: Sequence[str]) -> tuple` normalizes node ID, feature, threshold, missing/yes/no branches; `compare_tree_models(left_dumps, right_dumps) -> dict` returns first divergent tree/node, changed leaf weight count, changed split count and missing-split attribution as UNAVAILABLE when gain candidates were not recorded.

- [ ] RED tests using hand-authored tiny tree JSON: identical structures differing only leaf weights -> split diff 0; altered threshold/feature/missing branch -> first divergence correct; order of JSON child objects does not matter; missing dump/gain metadata explicitly unavailable.
- [ ] Run `pytest -q target_redesign_level2_v1/training_stability_v1/tests/test_tree_diff.py`, expect RED due absent interfaces.
- [ ] Implement exact two functions; no training, code cannot infer a split gain margin from a final tree if runner did not save competing candidate gains.
- [ ] Run tests GREEN; inspect output on tiny JSON fixtures.
- [ ] Commit `feat: auditable nodewise XGB split comparison without historical refits`.

### Task 3: Probe XGB split sensitivity on only NEW synthetic grouped training inputs

**Files:** Create `target_redesign_level2_v1/training_stability_v1/synthetic_probe.py`; Test `target_redesign_level2_v1/training_stability_v1/tests/test_synthetic_probe.py`.

**Interfaces:** `probe_training_perturbations(seed:int=101, rounds:int=12) -> dict` generates controlled group ranking data, runs original `rank:pairwise` with `QuantileDMatrix`, holds baseline trained model constant for inference-only perturbation, refits once each with X-only and y-only synthetic perturbation, audits same 8 query groups, changed label count, tree splits and inference scores. Reports whether first tree/node differs **for these fixtures only**. No financial labels.

- [ ] RED tests: deterministic exactly replicated same input/seed yields same scores/splits; group sizes and sample identities identical for perturbations; X-only holds y byte-identical, y-only holds X byte-identical; changed fit vs inference-only reported separately; output marks `synthetic_only=true`.
- [ ] Run `pytest -q target_redesign_level2_v1/training_stability_v1/tests/test_synthetic_probe.py` expecting RED.
- [ ] Implement the minimal `probe_training_perturbations` with one frozen perturbation size chosen to expose API behavior, not a parameter sweep; no claims synthetic structure mirrors 149 ETF training.
- [ ] Run Task 2+3 tests GREEN; save complete fixture seeds and dumps, no economic evaluation.
- [ ] Commit `test: capture ranked-tree structural response on synthetic perturbations`.

### Task 4: Design an **observable** single-candidate research gate, not an optimization campaign

**Files:** Create `target_redesign_level2_v1/training_stability_v1/SINGLE_HYPOTHESIS_GATE.md`; Create `target_redesign_level2_v1/training_stability_v1/PROSPECTIVE_EVALUATION_CONTRACT.md`.

**Interfaces:** Outputs (a) observed primary XGB split mechanism with verified trace OR explicit `ROOT_CAUSE_NOT_RESOLVED`; (b) single selected future hypothesis if justified, chosen without using held-out P&L; (c) fixed future economic test contract; no training/evaluation in this Task.

- [ ] Read Tasks 1–3 results and choose: `TOPOLOGY_PERSISTENCE/LEAF_REFRESH` **only if** divergent topology is substantiated and as-of checkpoint exists; `STABLE_SPLIT_TIE_POLICY` **only if** near-equal split competing gains are measured by instrumentation; otherwise `NO_CANDIDATE_YET`. These are mutually exclusive choices; never test both and select by which historical CAGR looks better.
- [ ] For chosen future hypothesis define whether it operates only on legitimate new yearly refits or also maintains tree refresh; maintain `rank:pairwise`, group QIDs, eligibility and 360 rounds original unless proposed intervention itself necessarily differs, and lock all exceptions before any outcome observed.
- [ ] Pre-register prospective as-of snapshot schedule, new period not reused in research, *same universe and same exact market vintage on both sides*, only matured data, fixed fees, daily V2 MA3/HighCAGR24/V6 and old risk governor.
- [ ] Define joint release gates for **economic non-inferiority for each new observed vintage**, worst/dispersion CAGR, daily MaxDD, fees/turnover, downside tails and genuine extreme-upside capture, and reduced training-model sensitivity. Explicitly require user agreement on numeric tolerances rather than inventing them ex post.
- [ ] Commit `docs: predefine one falsifiable XGB training stabilization candidate and future full-V2 gate`.

### Task 5: Independent review, scope verification and stop

**Files:** Create `target_redesign_level2_v1/training_stability_v1/REVIEW.md`.

- [ ] Verify "first split changed" statement is backed by actual saved tree trace, not inferred from old Top1 disagreement. If evidence insufficient mark unresolved and propose only diagnostics, not a live candidate.
- [ ] Verify all methods flagged "already tried" were *not rerun*. Verify no real ETF training, no full V2 backtest, no metric shopping and no changed `Etf_trader` files.
- [ ] Run `pytest -q target_redesign_level2_v1/training_stability_v1/tests`; record output and local versions; no CI claims without CI run.
- [ ] Review prospective evaluation contract for data leakage, same-universe comparability and trade accounting, and note what cannot yet be inferred from 113 monthly historical dates.
- [ ] Commit `docs: independently audit model-stability mechanism and prospectively gated next step`.

## Dependencies

| Connection | Why it matters |
|---|---|
| Task 1 → 2 | Do not pretend historical tree dumps survive when only score arrays exist |
| Task 2 → 3 | Synthetic fit responses use the same tree comparison, not score-only estimates |
| Task 1–3 → 4 | Model intervention justified by traced phenomenon, not ex-post CAGR |
| Task 4 → 5 | Reviewer catches hypothesis/metric snooping |
| Companion Plan A → real future economics | Verifiable model IDs, as-of training data and challenger lifecycle required |

## Exit and handoff

**Exit for this plan:** a falsifiable structural mechanism (or explicitly unresolved cause), tested only synthetically, **one** prospective candidate if justified and an economic validation protocol not yet run. **No newly measured CAGR and no claim of actual improved V2 stability.**

**State:** REVISED RESEARCH PLAN — FOR REVIEW. Requires user approval before any implementation. If subagent dispatch unavailable, report that and use native inline execution only if authorized. No tests from old research are to be repeated.
