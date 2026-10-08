# Immutable Compact21 XGBoost Checkpoints — Implementation Plan

> **SUPERSEDED — DO NOT EXECUTE.** This freeze-centric draft was replaced after review of support for new ETF universes, new dates and genuinely new training. Follow [Model Lifecycle Plan](2026-10-08-v2-model-lifecycle.md) and [Training Stability Research Plan](2026-10-08-v2-xgb-training-stability-research.md), grounded in [revised design](../specs/2026-10-08-v2-model-lifecycle-and-training-stability-v2-design.md). Retained for historical audit; no code from this draft has been authorized.


> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make ETF Trader V2's canonical Compact21 XGBoost annual training and prediction artifacts immutable, verifiable and reloadable, without changing training semantics or strategy decisions.

**Architecture:** Develop a research-only `checkpoint_contract_v2` package on a separate branch in `AM1975MA/Test`. Split **FitIdentity** (causal data/learner contract) from **PredictionIdentity** (model+inference input), retain UBJ boosters from otherwise canonical `QuantileDMatrix` training, verify exact reload/prediction agreement, and reject invalid/stale caches. Use an isolated research adapter and synthetic grouped datasets first; do not patch the vendored original producer or run historical portfolio tests in this plan.

**Tech Stack:** Python 3.13.5, numpy 2.3.5, pandas 2.2.3, XGBoost 3.1.3, stdlib `hashlib`/`json`/`os`/`pathlib` and pytest. Strict runtime/version pinning as recorded in the approved spec.

**Spec:** [`docs/superpowers/specs/2026-10-08-etf-v2-checkpoint-integration-design.md`](../specs/2026-10-08-etf-v2-checkpoint-integration-design.md)

## Global Constraints

- GitHub repo **`AM1975MA/Test`**, development branch **`research/v2-xgb-immutable-checkpoints-20261008`** (created from `research/target-redesign-level2-v1`).
- Do **not** change `Etf_trader`, `Trader_selector`, `vendor/etf_trader_v2`, canonical score formulas, original ranking, trading logic or risk configuration. No merge or PR promotion without instruction.
- No training or backtesting on Original149, no repeating L2-D/E/F/G/H/I/J, Q4/L50, L2-N/P or historic 2017–26 full replay.
- Keep canonical XGBoost `rank:pairwise`, 125 feature schema, 360 rounds, 3 seeds `[101,202,303]`, horizons `[21,63]` for eventual production-compatible configuration; reduce rounds only for explicitly labeled **synthetic unit/integration tests**, never reporting them as investment evidence.
- `QuantileDMatrix` with identical query grouping in **canonical fit**; `DMatrix` leaf-update belongs to a **different future plan** and must not be implemented here.
- Missing or mismatched checkpoint, input hashes, parameters, model version, feature order or cutoff => fail closed. Never silently overwrite checkpoints or substitute a model fitted on a different data vintage.
- Label maturity checked against each training row's `signal_date < cutoff` and `exit_date_h < cutoff`; avoid mere attestations.
- Hashes detect inadvertent changes, not cryptographic authenticity. Treat archived data and models as potentially untrusted until verified; never unpickle artifacts from unknown sources.
- No financial/CAGR claims are produced by these tasks. Existing L2-Q 10/10 passing prototype tests are **not** proof of this new implementation.
- This plan covers **Compact21 checkpoint foundation only**. MA3 ExtraTrees, XGB regressor, imputer and PCA/KMeans-state freezing is a **separate subsequent design/implementation plan** after this module is validated.

## Review Focus

1. **Signed zero, NaN/Inf and dtype drift:** canonical float-array representation must make equivalent NaN payloads deterministic but detect true feature changes; test `+0/-0`, NaN patterns, dtype and shape.
2. **Temporal leakage:** malformed `signal_date`/`exit_date`, equality to cutoff and row-order/group inconsistencies must be rejected before generating a fit identity; tests in Task 1.
3. **Interrupted/multi-process publication:** a reader must never accept a half-written archive, and two writers cannot overwrite each other; tests in Task 2.
4. **Inference drift without retraining:** changing just `Xte` changes prediction identity/cache but not fit identity; tests in Tasks 1 and 4.
5. **Actual Booster parity:** save/reload must preserve scores and ordering with `QuantileDMatrix` and query-group semantics; tests in Task 3. Reject stale scores even if `fit_audit_YEAR.json` exists, Task 5.

---

### Task 1: Deterministic fit/prediction identities and causal data validation

**Files:**
- Create: `target_redesign_level2_v1/checkpoint_contract_v2/__init__.py`
- Create: `target_redesign_level2_v1/checkpoint_contract_v2/identity.py`
- Test: `target_redesign_level2_v1/checkpoint_contract_v2/tests/test_identity.py`

**Interfaces:**
- Produces `validate_fit_rows(row_keys: Sequence[tuple[str,str]], signal_dates: Sequence[str], exit_dates: Sequence[str], groups: Sequence[int], cutoff: str) -> None`, raises `CheckpointContractError`.
- Produces `fit_identity(*, Xtr: np.ndarray, y: np.ndarray, groups: np.ndarray, row_keys: Sequence[tuple[str,str]], signal_dates: Sequence[str], exit_dates: Sequence[str], cutoff: str, horizon: int, seed: int, rounds: int, feature_names: Sequence[str], params: Mapping, source_identity: Mapping, runtime_identity: Mapping) -> str`.
- Produces `prediction_identity(*, fit_id: str, model_sha256: str, Xte: np.ndarray, inference_keys: Sequence[tuple[str,str]], prediction_config: Mapping) -> str`.
- Exports `CheckpointContractError(ValueError)`.
- Ensure numeric arrays hashed with recorded ordered dtype/shape and deterministic contiguous little-endian bytes; canonicalize NaN only for identity, never alter `Xtr` or original fit inputs. Feature names and ordered keys are exact, no alphabetically sorted feature columns.

- [ ] **Step 1: Write failing tests** covering maturity equality/future rejection; incorrect group sum; unsorted/duplicated row keys; change only `Xte` alters prediction ID not fit ID; differing training labels, seed, feature order, rounds, runtime or one feature cell change fit ID; repeat equivalent NaN payloads give same ID.
- [ ] **Step 2: Run `pytest -q target_redesign_level2_v1/checkpoint_contract_v2/tests/test_identity.py`** and verify RED from missing module/contract.
- [ ] **Step 3: Implement the four signatures above**, deterministic SHA-256 over a versioned canonical serialization with code/runtime identities and hard fail on invalid cutoff.
- [ ] **Step 4: Rerun Task 1 tests**, assert GREEN and `python -m compileall -q target_redesign_level2_v1/checkpoint_contract_v2`.
- [ ] **Step 5: Commit** `git add target_redesign_level2_v1/checkpoint_contract_v2; git commit -m "feat(test): causal fit and prediction identities for Compact21"`.

### Task 2: Immutable multi-file artifact archive and strict verification

**Files:**
- Create: `target_redesign_level2_v1/checkpoint_contract_v2/archive.py`
- Test: `target_redesign_level2_v1/checkpoint_contract_v2/tests/test_archive.py`

**Interfaces:**
- Consumes `CheckpointContractError` and `fit_id` from Task 1.
- Produces `publish_checkpoint(root: Path, fit_id: str, booster_ubj: Path, train_arrays_npz: Path, provenance: Mapping) -> Path`; archive path `root/fit_id`; refuses existing destinations; stores model+train arrays+manifest digest and seals the publication.
- Produces `load_verified_checkpoint(root: Path, fit_id: str, *, expected_provenance: Mapping) -> tuple[Path,dict]`; outputs verified `model.ubj` path and canonical manifest.

- [ ] **Step 1: Write failing tests** on known bytes: fresh archive success; changed bytes of UBJ, NPZ or manifest => error; feature/parameter mismatch => error; preexisting archive remains unchanged; symlink/relative-path injection rejection; interrupted staging ignored; two simultaneous publishers yield exactly one valid archive, no clobber.
- [ ] **Step 2: Run `pytest -q target_redesign_level2_v1/checkpoint_contract_v2/tests/test_archive.py`** and verify RED.
- [ ] **Step 3: Implement both signatures** with same-filesystem staging, exclusive per-`fit_id` lock `mkdir`, fsync of staged files/manifest and parent directory, atomic directory rename while holding the lock, read-before-use digest verification. Acquire lock before checking destination, and never delete a destination on failure. Caller owns lock recovery after a crashed writer; do not silently break stale locks.
- [ ] **Step 4: Run Task 2 tests and Task 1 tests**; assert GREEN.
- [ ] **Step 5: Commit** `git add target_redesign_level2_v1/checkpoint_contract_v2; git commit -m "feat: immutable content-addressed XGB checkpoint archive"`.

### Task 3: Canonical `rank:pairwise` fit-worker checkpoint adapter

**Files:**
- Create: `target_redesign_level2_v1/checkpoint_contract_v2/worker_adapter.py`
- Test: `target_redesign_level2_v1/checkpoint_contract_v2/tests/test_worker_adapter.py`

**Interfaces:**
- Consumes Tasks 1–2.
- Produces `fit_checkpointed_ranker(*, Xtr: np.ndarray, y: np.ndarray, groups: np.ndarray, Xte: np.ndarray, fit_id: str, root: Path, provenance: Mapping, params: Mapping, rounds: int, seed: int) -> np.ndarray` returning the **original native predictions**.
- Produces `predict_saved_ranker(*, root: Path, fit_id: str, provenance: Mapping, Xte: np.ndarray, Xtr_reference: np.ndarray, groups: np.ndarray) -> np.ndarray` using the exact canonical test-`QuantileDMatrix` construction and saved UBJ.

- [ ] **Step 1: Write failing tests** using only synthetic 8×10 grouped rows, no ETFs: predictions of the unchanged vendored `_xgb_worker.py` using equivalent synthetic NPZ/flags agree at native precision; fit and reload predict identical; six logical (2 horizons × 3 seeds) checkpoints are distinct; changed `Xtr/y/groups` identity cannot reuse old model; no new tree training when loading.
- [ ] **Step 2: Run `pytest -q target_redesign_level2_v1/checkpoint_contract_v2/tests/test_worker_adapter.py`**, verify RED.
- [ ] **Step 3: Implement the two interfaces**, using `xgb.train` with identical `QuantileDMatrix(Xtr,label=y).set_group(groups)`, `xgb.QuantileDMatrix(Xte,ref=dtrain)`, params/seed/thread settings from source, save UBJ, verify read-back score equality. Do **not** use leaf refresh.
- [ ] **Step 4: Run new tests + all `checkpoint_contract_v2/tests`**, assert GREEN; report any xgboost warning and exact max prediction delta.
- [ ] **Step 5: Commit** `git add target_redesign_level2_v1/checkpoint_contract_v2; git commit -m "feat: faithful XGB ranker UBJ save and reload adapter"`.

### Task 4: Independent inference cache, no silent retraining

**Files:**
- Create: `target_redesign_level2_v1/checkpoint_contract_v2/prediction_cache.py`
- Test: `target_redesign_level2_v1/checkpoint_contract_v2/tests/test_prediction_cache.py`

**Interfaces:**
- Consumes Tasks 1–3.
- Produces `save_prediction_cache(root: Path, prediction_id: str, predictions: np.ndarray, metadata: Mapping) -> Path`, content-addressed immutable archive.
- Produces `load_prediction_cache(root: Path, prediction_id: str, *, expected_metadata: Mapping) -> np.ndarray`; fail-closed on mismatch/hash corruption and wrong inference key ordering.

- [ ] **Step 1: Write failing tests** for exact hit, changed inference input (new prediction ID), changed model hash (new prediction ID), changed ticker order, stale result even with legacy audit file present, corrupted score file, refused overwrite.
- [ ] **Step 2: Run `pytest -q target_redesign_level2_v1/checkpoint_contract_v2/tests/test_prediction_cache.py`**, verify RED.
- [ ] **Step 3: Implement both interfaces** with atomic-write pattern from Task 2; numpy predictions are read-only artifacts, not proof of a different model. Reject a cache with legacy `scores_YEAR.csv` + `fit_audit_YEAR.json` when v2 strict mode is requested.
- [ ] **Step 4: Run all package tests**, assert GREEN.
- [ ] **Step 5: Commit** `git add target_redesign_level2_v1/checkpoint_contract_v2; git commit -m "feat: strict model-bound Compact21 inference cache"`.

### Task 5: Shadow-mode orchestration on synthetic data; no vendor changes

**Files:**
- Create: `target_redesign_level2_v1/checkpoint_contract_v2/shadow_runner.py`
- Test: `target_redesign_level2_v1/checkpoint_contract_v2/tests/test_shadow_runner.py`
- Create: `target_redesign_level2_v1/checkpoint_contract_v2/README.md`

**Interfaces:**
- Consumes Tasks 1–4.
- Produces `run_shadow_ensemble(*, synthetic_panel: object, horizons: Sequence[int], seeds: Sequence[int], params: Mapping, root: Path, cutoff: str) -> dict[int,np.ndarray]` with both baseline and checkpointed predictions and diagnostic hashes; exact synthetic panel schema is fixed in Task 5 test fixture to match `_fit_compact_rankers_isolated` data/eligibility/order/group contract.
- Produces CLI `python -m target_redesign_level2_v1.checkpoint_contract_v2.shadow_runner --synthetic --output <dir>` (if import namespace packaging is viable, else invocation by absolute script) writing a JSON result with run IDs and per-horizon parity deltas.

- [ ] **Step 1: Write failing tests** for 2 horizons × 3 seeds: baseline and shadow aggregation identical; restart from verified saved model performs **zero calls to XGBoost.fit/train**; inference changes recompute scores without model fitting; altered training input or cutoff aborts; state/header cannot impersonate Golden historical model.
- [ ] **Step 2: Run `pytest -q target_redesign_level2_v1/checkpoint_contract_v2/tests/test_shadow_runner.py`**, verify RED.
- [ ] **Step 3: Implement the two-run diagnostic orchestration** without any Original149 dataset reads; log both FitIdentity and PredictionIdentity and exact max abs score delta. Keep source-only `vendor` untouched.
- [ ] **Step 4: Run `pytest -q target_redesign_level2_v1/checkpoint_contract_v2/tests` and `python -m compileall -q ...`**, record versions, counts and failures (if any). Execute one synthetic CLI verification and archive outputs/QA in `README.md`.
- [ ] **Step 5: Commit** `git add target_redesign_level2_v1/checkpoint_contract_v2; git commit -m "test: verify synthetic six-booster Compact21 checkpoint parity"`.

### Task 6: Review and next gate for MA3, without implementation spillover

**Files:**
- Create: `target_redesign_level2_v1/checkpoint_contract_v2/REVIEW_AND_HANDOFF.md`
- Create: `docs/superpowers/specs/2026-10-08-etf-v2-ma3-state-freeze-design-notes.md` (**notes only**, a separate design approval is required before implementing the MA3 state freeze).

**Interfaces:**
- Consumes all previous QA outputs; no new runtime interfaces.

- [ ] **Step 1: Independently inspect** invariants of the new package and compare line-by-line with approved design; review model/parquet input safety, race-handling, group/cutoff and exact scores on synthetic corpus; log unresolved issues.
- [ ] **Step 2: Check Git diff** to ensure no original source, `Etf_trader`, `Trader_selector`, `vendor`, or production risk-control changes.
- [ ] **Step 3: Write report** with actual test outputs, number of saved/reloaded boosters, observed max parity error, untested limitations, and MA3/cluster-state freezing interface/costs.
- [ ] **Step 4: Re-run all tests and check Git branch/working tree**, never claim external CI success without a run.
- [ ] **Step 5: Commit** `git add target_redesign_level2_v1/checkpoint_contract_v2/REVIEW_AND_HANDOFF.md docs/superpowers/specs/2026-10-08-etf-v2-ma3-state-freeze-design-notes.md; git commit -m "docs: review immutable Compact21 checkpoints and scope MA3 state freeze"`.

## Dependency and integration pre-flight

| Task interfaces | Relationship | Decision |
|---|---|---|
| T1 → T2 | Stable `fit_id`, `CheckpointContractError` | T2 consumes digest and error; no duplicate canonical serializers |
| T1,T2 → T3 | Causal identity + storage | Worker does not compute its own incompatible fit identity |
| T1,T2,T3 → T4 | Saved model + prediction identity | Inference data not included in fit ID; separate cache |
| T1–T4 → T5 | Ensemble orchestration | Synthetic only and source exact kernel |
| T1–T5 → T6 | Immutable QA outputs | Documentation/report, no implicit MA3 integration |

## Acceptance and execution handoff

The implementation is done **only** when all Task 1–5 RED→GREEN evidence, full synthetic package tests, model reload parity, stale cache rejection, no-retraining on saved fit and working-tree scope checks are recorded. No CAGR or financial return is a relevant output of this *engineering* phase. Do not promote to live V2 or declare full MA3 reproducibility.

**Execution method:** to be chosen after the user reviews this plan. Superpowers has no subagent dispatch action surfaced in the current tools; **native inline** is the available safe method; if a true subagent tool becomes available, the plan may use independent task review. No implementation was authorized by merely creating this plan.
