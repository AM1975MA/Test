# Task1 implementation report

Implemented the minimally extended native replay engine, shared finite PlanExecutor, PARK8/REDEPLOY12 features, causal selector-order reconstruction, native 42-session counterfactual groups, and freeze-verified resumable paired banks.

## Authorized scope and untouched dependencies

Only Task1-owned source/test/report files were written. The engine was copied from OLC111 and extended only with `allow_initial_targeted=False`, its seeded-state requirement, its initial-mask exception, and documentation. The original simulator remains unchanged. The default output parity test compares exact native daily, order, instruction and alert frames. Existing OLC111 tests were also run unchanged.

No real-market label, fit, baseline replay or account path was executed for this task. The market bundle loader is ready for the root's pre-freeze causal-order preparation; all label and model checks here used synthetic fixtures.

## Mechanics and schemas

- `PlanExecutor` serves both bank and live callers. It maps subset account indices to global identities. It issues the targeted forced sell-only sale, confirms completion from zero actual remaining units and the final actual sell index, waits for an idle weekly Close strictly later than that fill, and makes at most one candidate attempt. Entry target equals actual cash/NAV. Monthly full-target handoff has priority even when pending/queued work remains; subsequent monthly continuation remains native.
- The trace records meaningful transitions and pending-status changes, including sale instruction/confirmation, entry attempt/instruction and monthly handoff. It omits repeated idle daily NOOP records. The summary contains plan/head/asset/signal_idx, sale_complete_idx, entry_attempt_idx, entry_candidate_idx, handoff_idx and phase.
- Candidate selection retains the original explicit `selected_indices` order and original `pair_corr` implementation at the current index. Candidates exclude retained units and must satisfy correlation <=0.85 (+ original 1e-12 numerical tolerance) against every retained asset. The outgoing asset remains eligible to compete.
- PARK8 uses own unit-weight return statistics, actual held weight, the actual retained basket, known monthly distance and 1/NAV. REDEPLOY12 adds only the current compatible candidate statistics and the known first-weekly distance strictly beyond k+1. Future identities and realized waits never enter the initial vector.
- `build_bundle` directly reads OLC110 source inputs and OLC111 selection/state/baseline caches. It calls the unchanged feature builder and selector without invoking the old research bank builder. It writes only OLC114 `SELECTED_ORDER.json` and `SELECTED_ORDER_PROVENANCE.json`, with hashes of its source/input dependencies. Cached half-weight targets must match reconstructed selector weights exactly on every date.
- The returned bundle adds `states` arrays (`k,units,cash,nav,busy`), `weekly`, `selected_order`, and a global-index `baseline_nav` dictionary, plus selector/source identities. It preserves the existing panel/f/core/monthly/feature_monthly/targets/begin interface.
- `counterfactual_group` returns `records` with head/asset/X/y/signal_idx/terminal_idx, per-branch events, all terminal NAV values, BASE endpoint/reference/error, native accounting error and explicit status. Every branch shares k+42 without terminal liquidation. Any branch's unsupported/stale realized mark censors the entire group. Missing seed marks receive `CENSORED_MISSING_MARK`; future/right-edge, busy, scheduled, no-holdings and invalid-feature states have explicit statuses. A supplied frozen BASE endpoint mismatch raises rather than manufacturing labels.
- `build_bank` verifies every BANK_FREEZE `code_hashes` and `input_hashes` entry and the protocol hash before work and again afterward. Root supplies the freeze; no implicit freeze is created. Resume requires identical freeze and selected-order identity, validates event checksums and duplicate dates, and validates existing final artifacts against the saved summary.
- NPZ files contain exactly `X,y,signal_idx,terminal_idx,asset_idx`; X has shape (rows,8) for PARK and (rows,12) for REDEPLOY. The JSONL event record stores global `asset`, mapped to NPZ `asset_idx`. `BANK_SUMMARY.json` seals both NPZs and BANK_EVENTS.jsonl. A partial interrupted JSON line is deliberately rejected rather than guessed/repaired.

## RED/GREEN evidence

The first test run on the unextended copied engine failed the explicit opt-in signature assertion and the new opt-in calls; plan tests could not import the absent new cycle_core module. Default native parity passed before modification. The next implementation produced a green suite. A second RED run demonstrated absent bank APIs before their implementation. A subsequent RED run demonstrated the missing seed-mark classification (returned INVALID_FEATURES instead of CENSORED_MISSING_MARK) and the absent explicit order reconstruction helper; both passed after correction.

Final distinct Task1 tests: 25. Tests cover default parity, seeded opt-in and invalid masks, unaffected quantity preservation through a large gap, no unseeded opt-in, scheduled-mask restrictions, delayed/unfilled sale, partial-sale confirmation, lag1 timing, strict weekly-after-fill, actual cash entry, single no-candidate attempt, pending entry expiration under native handoff, busy-sale monthly priority, global/local mappings, frozen candidate order and retained correlation, feature dimensions/current-candidate absence/future mutation, common 42-session BASE parity, hard BASE mismatch rejection, whole-group stale censor, missing seed marks, busy/right-edge statuses, freeze-required creation, bank schema/resume and mutated-source rejection.

Fresh verification commands and outcomes:

```
python -m unittest discover -s olc114/tests -v
# 38 tests passed at verification time: 25 Task1 +13 Task2.
python -m unittest discover -s olc111/tests -v
# 77 tests passed, unchanged prior suite.
```

Real causal-order reproduction, full historical BASE endpoint reconciliation, frozen bank construction and runtime performance remain the root's post-review integration checks. No result is claimed from an unrun real-market experiment.

## Source hashes

- `src/cycle_engine.py`: `7118993936c540cb053660ba29ac3c65380c600ff7a5c101e6c7af288e6b2297`
- `src/cycle_core.py`: `31fe4843b0e9a1ec70a2cf63a2018322d5c1f9b1390c9ea23ae33077e513a7a5`
- `tests/test_cycle_core.py`: `bebcf94038a48581328ab462b91cc8c104ca61f1ccd8c63f6911d501d8c3560f`
