# OLC114 Complete Plan Implementation Plan

> **For agentic workers:** follow isolated task ownership, tests before implementation, then independent review. Root owns integration, freezes and historical runs.

**Goal:** Test complete per-position protection/redeployment values with the same finite plan in labels and deployment.

**Architecture:** A minimally extended native engine executes a reusable finite `PlanExecutor`. Baseline-state comparisons build two target banks. Portable mean, Ridge and small-tree heads are fit chronologically; the live policy selects at most one active plan until monthly handoff.

**Tech Stack:** Python3.12, NumPy, pandas, scipy, scikit-learn1.8.0, unittest, original native accounting core.

**Spec:** `docs/DESIGN_AND_PROTOCOL.md`. API contracts below bind all modules.

## Global constraints

- Never edit earlier study files. No market-data labels before BANK_FREEZE; no real fits/account runs before EXPERIMENT_FREEZE.
- Exact current selector order and correlation0.85; strict later weekly entry; one candidate attempt; monthly handoff priority.
- PARK8 / REDEPLOY12 features;42-session outcomes; strict mature-only fitting;504dates/24months/12nonoverlap;32paired63-session bootstraps.
- TREE primary; MEAN/RIDGE comparators; five accounts and three scenarios;15paths.
- Root may resolve interface details but must record rulings before results.

## Review focus

- Targeted seeded instruction preserves other units through a price gap; default native engine output is unchanged.
- No initial feature reads future replacement identity or realized waiting duration.
- Pending/partial sale, strict weekly timing, no-candidate and monthly handoff remain identical in bank and live policy.
- Repeated legs on one date do not multiply that date's statistical weight;42-session nonoverlap is genuine.
- Portable tree predictions and loaded model hashes match the fitted estimator; future rows cannot change earlier fits.

### Task1 — Native engine, plans, features and bank

**Own:** `src/cycle_engine.py`, `src/cycle_core.py`, `tests/test_cycle_core.py`; report `research/implementation/TASK1_REPORT.md`.

- [ ] Write failures for seeded-target masks, preserved unaffected units/gaps, scheduled mask restriction, deferred sales, weekly strictness, one entry attempt, scheduled handoff priority and future-candidate feature leakage.
- [ ] Add opt-in `allow_initial_targeted=False` to the copied native simulator, requiring seeded state; test default parity with the old simulator.
- [ ] Implement the API below and the exact protocol mechanics, with synthetic small-panel tests.
- [ ] Verify BASE counterfactual parity on synthetic monthly histories. Real baseline-replay checks run later with the bank after freeze.

**API:**

`build_bundle(root: Path) -> dict`: reuse the OLC111 bundle and existing baseline snapshots; add `selected_order` (list of global-index lists), `weekly` mask and `states` dict with k/units/cash/nav/busy. Reconstruct selector order causally and assert its0.5weights equal cachedtargets. Save only OLC114 order/provenance cache.

`candidate_for(bundle, k: int, retained: iterable[int]) -> int | None`: current ordered frozen selector candidates, exclude retained, correlation<=.85 to each retained.

`plan_features(bundle, k: int, current: ndarray, nav: float, asset: int, head: str) -> ndarray | None`: exact8/12vector; primary ticket1; current candidate only; no labels.

`PlanExecutor(bundle, head: str, asset: int, signal_idx: int, local_ids=None)`: callable `(k,current,context)->dict|None`, with `.active`, `.trace`, `.summary`. With `local_ids`, context/weights refer to that subset while selectors/features use global identities. The first call at signal_idx emits the targeted sale, including seeded initial calls. Monthly handoff emits a full baseline target and sets activeFalse. After handoff, the executor continues only baseline monthly instructions for label continuation. Trace records sell confirmation, entry attempt/candidate/instruction, handoff, pending status. `.summary` exposes plan/head/asset/signal, sale_complete_idx, entry_attempt_idx, entry_candidate_idx, handoff_idx and phase. Bank and live use this exact class.

`counterfactual_group(bundle, k: int, state: dict, horizon=42) -> dict`: BASE and all per-held-leg plans from same state, nextClose/normalcost, union asset subset, complete outcomes plus explicit censor status and native accounting checks. Returns records with head/asset/X/y/signal_idx/terminal_idx for both banks, group events and BASE replay endpoint. Never fits models.

`build_bank(root: Path, bundle: dict, resume=False) -> dict[str,dict]`: verifies BANK_FREEZE, persists BANK_PARK.npz and BANK_REDEPLOY.npz (`X,y,signal_idx,terminal_idx,asset_idx`), BANK_EVENTS.jsonl and provenance/summary; resumes only exact identities. All eligible starting dates used once; no subjective trigger conditioning. Writes no old source/results.

### Task2 — Portable fixed models

**Own:** `src/cycle_model.py`, `tests/test_cycle_model.py`; report `research/implementation/TASK2_REPORT.md`.

- [ ] Write tests for strict terminal maturity, future mutation, per-date weighting,42-session nonoverlap/readiness, deterministic paired block draws and portable tree/Ridge prediction parity.
- [ ] Implement `fit_head(X,y,signal_idx,terminal_idx,cutoff,dates,*,min_dates=504,min_months=24,min_blocks=12,n_boot=32,seed=114,penalty=1.) -> dict|None` with fixed model designs. Expected return: `models` mapping MEAN/RIDGE/TREE to `ValueModel`, `hashes` mapping the same names, `meta` with maturity/readiness/training support/draw hash.
- [ ] Implement `ValueModel.predict(x)->{'mean':float,'lower':float}`, `to_dict()` and `from_dict()` with full portable numerical model objects. Export tree children/features/thresholds/leafvalues and implement exact numerical inference, avoiding pickle artifacts. Models and bootstrap models all saved.
- [ ] Return model-independent metadata including feature scaler for training-support diagnostics; arrays must round-trip finite JSON.
- [ ] Validate deterministic tests with synthetic data only. No market-data fit.

### Task3 — Root integration, freeze and experiment

**Root owns:** `src/run_cycles.py`, `tests/test_run_cycles.py`, freeze/progress documents.

- [ ] Integrate monthly cache and the at-most-one-active-plan policy using Task1 executor and Task2 models. Save actual eligible decision-state features and model hashes.
- [ ] Review dependencies and tests, create BANK_FREEZE, then build and reconcile the complete counterfactual bank.
- [ ] Freeze completed bank and runner before fits/15paths. No old model/fund selection changes.
- [ ] Save full account artifacts, forecast ledger and model/cache identities; exact BASE/STATIC_75 replication in existing scenarios and matched delayed controls.

### Task4 — Independent audit, report and save

- [ ] Reconstruct all accounts, source marks and costs; verify full/commonperiod metrics, mature training, plan continuity and actual cash entry quantities.
- [ ] Report every model/scenario and yearly result, forecast failures and predefined success criteria.
- [ ] Create Italian report/figures and verified Git archive, preserving every prior source/ref.
