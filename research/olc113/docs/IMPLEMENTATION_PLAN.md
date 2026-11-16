# OLC113 Continuation Contract Implementation Plan

> **For agentic workers:** use subagent-driven development for the isolated runner and a separate read-only reviewer. Root owns the protocol, freeze, run and integration. Follow the tests before implementation.

**Goal:** Measure the effect of restoring baseline monthly reentry to cash accounts without changing predictions.

**Architecture:** A small `ResetOverlay` derives from the existing learned `AccountPolicy`. A study runner reuses the OLC112 artifact format and all saved OLC111 fits. Existing directories remain unchanged.

**Tech Stack:** Python, NumPy, pandas, existing native simulator and unittest.

**Spec:** `docs/DESIGN_AND_PROTOCOL.md`.

## Global constraints

- Four arms MEAN_RESET/PRICE_RESET/VIX_RESET/TERM_RESET, three unchanged scenarios, 12 paths.
- No new fitting or data; preserve the original 3% scheduled band and execution timing.
- No financial-result execution before the experiment freeze is created.
- All new source/tests under OLC113; exact inherited interfaces and saved paths remain usable.

## Review focus

- A fully cash account must receive the monthly target even with a negative ENTRY estimate.
- Pending instructions must not be replaced, and initial/warmup behavior must match the old account.
- Nonscheduled decisions and predictions must match the unchanged parent on the same state.
- No implicit same-close execution or forced small monthly trades.
- Missing model files must fail before fitting; completed-path markers must follow all required receipts.

### Task 1 — Policy and runner

**Create:** `src/run_monthly_reset.py`, `tests/test_monthly_reset.py`.

**Interfaces:** `ResetOverlay(bundle, arm, fit_cache).__call__(k, current, context)`; `verify_freeze(root)`; `run(root, resume=False)`. Consume the OLC111 bundle/cache and native simulator exactly as OLC112 does. Produce the same artifact schema and `MEAN_BASE_REPLICATION.json`.

- [ ] Write meaningful tests: negative-entry scheduled cash executes baseline; scheduled invested rotation preserves the band; no same-close fill; pending/queued state remains untouched; nonscheduled predictions/targets match parent; initial/warmup matches; absent saved models raise without fitting.
- [ ] Run the new tests and record expected failures before writing the implementation.
- [ ] Implement the specified monthly default; retain source arm in metadata and record status `MONTHLY_BASELINE_RESET`.
- [ ] Write complete artifact receipts before completion markers. Reuse pure serialization/account functions instead of copying the simulator.
- [ ] Run the OLC111, OLC112 and new suites; report all failures.

### Task 2 — Independent review, freeze and run

**Root creates:** `docs/EXPERIMENT_FREEZE.json`; reviewer writes `docs/INDEPENDENT_CODE_REVIEW.md`.

- [ ] Review against the protocol, especially cash/initial/pending cases and inherited execution assumptions.
- [ ] Freeze protocol, runner and exact source/model/control identities. Recursively verify the old freezes.
- [ ] Run the 12 predeclared accounts once with zero refitting and save a run manifest.

### Task 3 — Audit, interpretation and archive

**Create:** `src/analyze_results.py`, `results/INDEPENDENT_*`, `RAPPORTO_OLC113_IT.md`, `README.md`.

- [ ] Independently verify accounting, source marks, calendars, full/common metrics and baseline parity using the already tested audit utilities.
- [ ] Diagnose each cash reset and the effect on annual return; retain all negative and secondary outcomes.
- [ ] Report the material-improvement and30% criteria without retrospectively changing them.
- [ ] Preserve source/fit hashes, archive on a new research branch in Test, verify the remote tree and prior branch heads.
