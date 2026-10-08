# V2 Model Lifecycle: Replay, Predict, Causal Refit — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a research-local model lifecycle for ETF Trader V2 that supports exact historical replay, new-date inference and legitimate **new training versions** (including ETF-universe changes), without changing the ranker or hindering future model improvement.

**Architecture:** A versioned immutable registry contains FitIdentity, PredictionIdentity and UniverseIdentity, plus separate model and forecast artifacts. A research-only wrapper exposes `REPLAY`, `PREDICT`, `REFIT` and a non-production champion/challenger admission workflow. Existing models remain available, but new causal fits are always allowed under new identities. Complete source-only V2/MA3 integration is **out of scope**; no original source or trading engine files are touched.

**Tech Stack:** Python 3.13.5, numpy 2.3.5, pandas 2.2.3, XGBoost 3.1.3, stdlib and pytest. Research-only package; actual XGBoost training only on **synthetic grouped inputs** until separate user authorization.

**Spec:** [Revised V2 lifecycle & stability design](../specs/2026-10-08-v2-model-lifecycle-and-training-stability-v2-design.md).

## Global Constraints

- Only `AM1975MA/Test`, branch `research/v2-xgb-immutable-checkpoints-20261008`; never modify `Etf_trader`, `Trader_selector`, `vendor/etf_trader_v2`, MA3, risk/stop/cost rules, or production branch.
- No repeated financial test on Original149 (L2-D/E/F/G/H/I/J, Q4/L50, L2-N/P, Repeat1/2/3 V2); no trading CAGR statements derived from synthetic data.
- Canonical future setting: Compact21 125 ordered features, two horizons 21/63, seeds 101/202/303, objective `rank:pairwise`, 360 rounds, existing worker's `QuantileDMatrix` grouping. Tiny rounds allowed only in explicitly synthetic unit tests.
- New ETF or universe changes require time-stamped membership and a separate ranking/label contract; old-as-of labels/cluster mapping cannot be recomputed using future constituents.
- New dates may use saved model for inference when schema/coverage compatible; new year or changed training universe triggers explicit `REFIT`, not an automatic preference for saved historic booster.
- Fail closed on stale/missing evidence; allow **new** immutable content ID after legitimate training change; never silently overwrite or replace historical models.
- `fit` and `predict` identities must differ; changed Xte invalidates only forecast, not booster; changed Xtr/y/groups/params/source/universe invalidates fit identity.
- Maturity checked on every training row `signal_date < cutoff`, `exit_date_h < cutoff`; universe membership as-of, sort order and group sizes validated. No 2026 Yahoo snapshot masquerading as authentic 2017 point-in-time.
- Frozen model is an **audit asset, not a decision that it is optimal**. Model selection is a distinct, causal, preregistered protocol: neither promote nor reject by looking at the highest already explored CAGR.
- A1/A2 completion is **engineering-only**; research stability hypothesis and economic evaluation belong to separate Plan B and eventual prospective Plan B2.

## Review Focus

1. Actual universe update without time-travel: new ticker enters only when its as-of eligibility begins; old cutoff cohort cannot gain a future entrant. Task 1.
2. Missing corporate action revision provenance or unsorted/duplicate keys: fail before fit/prediction ID calculation, not after fitting. Task 1.
3. Tiny Xte update must not trigger booster fit, but Xtr/y changes must not reuse old booster; distinct fit/prediction identities and tests. Tasks 2/4.
4. Integrity under corrupted artifact, mis-ordered feature names, process crashes and racing writers: fail closed, leave original checkpoint intact. Task 3.
5. Promoting 'better' model on evaluation data unavailable at its date, incompatible universe or missing full-V2 metrics: reject; incumbent expiry not infinite. Task 5.

---

### Task 1: Universe identity and causal maturity contract

**Files:** Create `target_redesign_level2_v1/checkpoint_contract_v2/universe.py`; Test `target_redesign_level2_v1/checkpoint_contract_v2/tests/test_universe.py`.

**Interfaces:** `universe_identity(members: Sequence[Mapping], effective_at: str, feature_schema: Sequence[str], eligibility_policy: Mapping, label_policy: Mapping, cluster_state_id: str) -> str` and `validate_training_cohort(keys, signal_dates, exit_dates, groups, cutoff, universe_manifest) -> None`. Require each member ticker unique, as-of start <= cohort date and no future entry, label denominator and symbol mapping version recorded. Do not fit.

- [ ] Write failing unit tests: 149→150 changed `universe_id`, future-listed ticker rejected for earlier date, mismatched label-denominator/version identity, repeated ticker rejected, label `exit_date == cutoff` rejected, sum(groups) mismatch and duplicate/unsorted row keys rejected.
- [ ] Run `pytest -q target_redesign_level2_v1/checkpoint_contract_v2/tests/test_universe.py`; expected RED for missing interface/incorrect validation.
- [ ] Implement exactly those signatures with ISO dates and canonical JSON/SHA256 identity. All dates verified **against the declared cutoff** and stored historical membership, not system wall clock.
- [ ] Run tests, verify GREEN and no unrelated tests broken.
- [ ] Commit `feat: causal ETF-universe and cohort identity for checkpoint lifecycle`.

### Task 2: Separate fit identity and prediction identity

**Files:** Create `.../checkpoint_contract_v2/identity.py`; Test `.../checkpoint_contract_v2/tests/test_identity.py`.

**Interfaces:** `fit_identity(*, universe_id: str, Xtr: np.ndarray, y: np.ndarray, groups: np.ndarray, rowkeys, cutoff: str, horizon: int, seed: int, rounds: int, feature_names, params: Mapping, source_hashes: Mapping, runtime: Mapping) -> str`; `prediction_identity(*, fit_id: str, model_sha256: str, Xte: np.ndarray, inference_keys, feature_names, inference_source_hashes: Mapping) -> str`. Keep exact input dtype/shape/order and normalise NaN representation only in ID, never source arrays.

- [ ] RED tests: changed Xte changes `prediction_id` not `fit_id`; changed single Xtr, y, groups, feature-order, seed, horizon/rounds, runtime, universe or source_hash changes `fit_id`; equivalent NaN payload behavior deterministic; signed-zero semantics documented.
- [ ] Run `pytest -q .../tests/test_identity.py` to observe RED.
- [ ] Implement signatures, prohibit non-finite JSON metadata and unsafe dtype/object arrays.
- [ ] Run Task 1+2 tests GREEN.
- [ ] Commit `feat: separate reproducible training and inference IDs`.

### Task 3: Immutable *versioned* artifacts and integrity checker

**Files:** Create `.../checkpoint_contract_v2/archive.py`; Test `.../checkpoint_contract_v2/tests/test_archive.py`.

**Interfaces:** `publish_fit(root: Path, fit_id: str, model_ubj: Path, train_npz: Path, provenance: Mapping) -> Path`; `load_fit(root: Path, fit_id: str, expected_provenance: Mapping) -> Path`; `publish_prediction(root: Path, prediction_id: str, prediction_npy: Path, provenance: Mapping) -> Path` / `load_prediction(...)`. Use SHA256 with no-clobber publish, directories named by digest; **different fit IDs coexist**, repeated identical fit ID is idempotent only when hashes match, otherwise reject. Legacy scores with audit but no model flagged `LEGACY_SCORE_ONLY`.

- [ ] RED tests: new fit can coexist with old, read-reload exact, tamper any component rejected, stored manifest mismatch rejected, concurrent publisher cannot overwrite, symlink/path traversal rejected, stale cache file rejected, interrupted stage dir ignored.
- [ ] Run `pytest -q .../tests/test_archive.py`, verify expected RED.
- [ ] Implement these functions with validated manifests, directory staging and exclusive lock/atomic publish; no deletion or overwrite of existing fit. Define stale-lock error and external recovery, never auto-break.
- [ ] Run all package tests GREEN.
- [ ] Commit `feat: immutable multi-version XGB model and prediction artifacts`.

### Task 4: Explicit replay/predict/refit orchestration, synthetic XGBoost only

**Files:** Create `.../checkpoint_contract_v2/lifecycle.py`; Test `.../checkpoint_contract_v2/tests/test_lifecycle.py`.

**Interfaces:** `run_replay(checkpoint_id, Xte, ...) -> Predictions`; `run_predict(approved_model_id, Xte, as_of, ...) -> Predictions`; `run_refit(training_bundle, cutoff, universe_id, ...) -> ModelVersion`. Avoid hidden fallback; the caller picks mode. For `REFIT`, use identical `QuantileDMatrix`+QID grouping as original worker, `xgb.train` with source-identical params, save UBJ after worker fit, verify exact prediction reload. For `PREDICT` a new `Xte` gets new predictions but zero training calls. Logs include `FIT_CREATED`, `INFER_RECOMPUTED`, `REPLAY_VALIDATED`, `FAIL_STALE`.

- [ ] RED tests on tiny grouped synthetic data: same as-of REPLAY parity; new date inference no re-fit; next cutoff REFIT permitted under *new id*; ETF membership change forces explicit new-universe identity; source drift in old ID rejected; unavailable historical fitted booster not falsely recreated.
- [ ] Run `pytest -q .../tests/test_lifecycle.py`, verify RED.
- [ ] Implement minimal signatures with dependency-injected training function to count actual fits, full causal validation before fit; include tests for six synthetic (2 horizon × 3 seed) UBJ round trips.
- [ ] Run full package test suite, collect max prediction equality delta, prove no other source touched.
- [ ] Commit `feat: replay predict and causal refit modes with canonical XGB`.

### Task 5: Champion–challenger *registry*, not trading promotion

**Files:** Create `.../checkpoint_contract_v2/registry.py`; Test `.../checkpoint_contract_v2/tests/test_registry.py`.

**Interfaces:** `register_candidate(existing_id: str|None, candidate_id: str, universe_id: str, cutoff: str, supported_until: str|None, evidence_manifest: Mapping) -> RegistryEvent`; `review_candidate(candidate_id: str, decision: str, evaluation_manifest: Mapping, review_cutoff: str) -> RegistryEvent`; `resolve_approved_model(as_of: str, universe_id: str) -> str`. Valid states `CHALLENGER/APPROVED/REJECTED/RETIRED/NO_APPROVED_MODEL`. **No financial gate criteria are chosen automatically;** absent preregistered policy or future-valid evidence -> no promotion.

- [ ] RED tests: candidate registered never auto-selected; reject keeps compatible incumbent; expired/incumbent incompatible returns NO_APPROVED_MODEL; cannot approve with immature future labels, different universe, missing mandated economic fields or missing dated gate; prospective results cannot be accessed before observation timestamp.
- [ ] Run `pytest -q .../tests/test_registry.py` RED.
- [ ] Implement append-only event history; strict as-of release decision and signed/ACL note (SHA integrity not authentication).
- [ ] Run all package tests GREEN.
- [ ] Commit `feat: causal approval lifecycle with explicit no-approved-model status`.

### Task 6: QA, scope containment and MA3 handoff

**Files:** Create `.../checkpoint_contract_v2/REVIEW.md`; Create `docs/superpowers/specs/2026-10-08-v2-ma3-state-followup-notes.md` (notes only, not authority to build MA3).

- [ ] Inspect full spec against Tasks 1–5 and check no hidden freeze-forever behavior; check no cohort leakage, universe version ambiguity, model promotion by retrospective CAGR or legacy artifact masquerading as complete checkpoint.
- [ ] Run `pytest -q target_redesign_level2_v1/checkpoint_contract_v2/tests` and `python -m compileall -q target_redesign_level2_v1/checkpoint_contract_v2`; include exact outputs and versions in QA.
- [ ] Check actual git diff excludes `vendor/etf_trader_v2`, `Etf_trader`, `Trader_selector` and any production trading parameters.
- [ ] Document data/model lifecycle, synthetic round trips, boundaries, lack of real economics and **separate Track B instability plan**.
- [ ] Commit `docs: validate versioned replay and causal refit lifecycle`.

## Pre-flight relationships

| Tasks | Interface | Invariant |
|---|---|---|
| 1→2 | `universe_id`, maturity validator | Fit identity includes exact as-of universe + cohort |
| 2→3 | `fit_id`, `prediction_id` | New training version can coexist; stale same-ID reuse forbidden |
| 1–3→4 | checkpoint storage and identity | REPLAY never trains, PREDICT never trains, REFIT always creates new ID |
| 1–4→5 | model IDs and future evidence | Candidate does not automatically replace champion |
| 1–5→6 | actual QA evidence | Test coverage and documented MA3 follow-up, not CAGR claim |

## Acceptance and handoff

This project is an engineering capability only, NOT an answer to the inherent tree-instability. The proper exit is a verified **three-mode lifecycle with legitimate refits**, a no-override version archive and explicit prospectively constrained model governance; **not** a proof that historical CAGR improves or remains at 43.146%.

**Status:** REVISED PLAN — FOR REVIEW. No execution, no financial tests. The separate [Track B plan](2026-10-08-v2-xgb-training-stability-research.md) addresses instability itself. Superpowers execution method (native or subagent, if available) is chosen only after user approval.
