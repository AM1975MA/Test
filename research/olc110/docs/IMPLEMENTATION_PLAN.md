# OLC110 Protection and Reentry Implementation Plan

> **For agentic workers:** Use the executing-plans / subagent-driven-development workflow for the isolated tasks below, keeping a shared ledger. The user's explicit research autonomy authorizes execution without another design approval.

**Goal:** Test whether causal exits, cash and realized-fill-aware reentry improve the frozen OLC109 selector.

**Architecture:** Preserve the original selector/core and add an optional account-policy interface with masked intramonth execution. A two-slot policy owns risk states; a frozen runner executes all 78 declared paths. Independent auditors reconstruct the accounts and policy states without importing production policy code.

**Tech Stack:** Python3.12, numpy2.3.5, pandas2.2.3, scipy1.17.0, unittest, matplotlib.

**Spec:** `docs/DESIGN_AND_PROTOCOL.md`.

## Global Constraints

- No OLC109 changes, no signals or fills using future information, no actual trades.
- Exactly13 arms ×6 scenarios; all outputs retained; cash zero yield, no account leverage.
- Monthly selection remains DEDUP_DUAL_TREND_OPP except the explicit weekly control.
- Protected events preserve quantities outside the immutable action mask.
- Cash vacancy and probe promotion depend on actual holdings/fills; pending events cannot be discarded by unrelated targeted actions.

## Review Focus

1. Unaffected position jumps at the execution Open: no unintended sale/rebalance from a targeted event.
2. Missing quotes and extra latency: no reinvestment of unsold holdings, no probe promotion before actual purchase.
3. SLOW and exit simultaneously true: remain cash / respect exit precedence.
4. Calendar change with a protected ETF still selected: preserve its risk state.
5. Fresh emerging opportunity correlated with a residual holding: reject it and preserve cash.

## Task1 — Optional account-policy engine

Files: modify `src/engine.py`; create `tests/test_account_policy_engine.py`; preserve reference `research/engine/olc109_engine_reference.py`.

Interface: `simulate(...,account_policy=None)` calls `account_policy(k,current_weights,context)` on every initial/remaining nonterminal Close. Context contains `scheduled`, `initial`, `units`, `cash`, `nav`, `pending`, `queued`, `last_buy_idx`, `last_sell_idx`. Callback returns None only on nonscheduled Close, or dict with `weights`, optional `action_mask`, `sell_only`, `force`, `meta`, `reason`. Initial/monthly callback returns a full instruction (mask None). Legacy path unchanged when callback is None.

- [x] Write failing synthetic tests for no-op equivalence, actual context, next-open/lag, missing masked quote, unaffected gap preservation, buy using only available cash, sell-only prohibition, immutable mask/target and full scheduled precedence.
- [x] Implement interface and masked executions; keep all inherited behavior.
- [x] Run focused tests and complete inherited suite; record evidence.

## Task2 — Two-slot protection policy

Files: create `src/protection.py`, `tests/test_protection.py`.

Interface: `prepare_timing_features(panel,f)` adds causal features; `make_account_policy(panel,f,monthly_mask,weekly_mask,arm,start_index)` returns callable object with `trace` list. `ARMS` is the exact declared ordered matrix. The policy uses unchanged `dedup_selectors.make_policy(...,'DEDUP_DUAL_TREND_OPP')` with no cluster dependency. Controls use the original two-argument policy path.

- [x] Write failing hand-calculated cases for exits/cash, persistent state, slow/fast conflict, rebound hysteresis, post-fill promotion, book-busy deferral, original reentry priority, fresh candidate ranking/correlation and untouched holdings.
- [x] Implement market features and policy under the protocol, no parameter optimization.
- [x] Check prefix invariance and all tests.

## Task3 — Frozen experiment runner

Files: `src/run_protection.py`, docs freeze, results/.

- [x] Freeze protocol/code/input SHA-256 before reading any new strategy performance.
- [x] Run all78 paths; immutable complete ledgers, decisions, daily policy trace, metrics, annual/segment tables, RUN_MANIFEST.
- [x] Compare all five original BASE account paths against OLC109; stop for an implementation mismatch, never tune around it.

## Task4 — Independent audit and analysis

Files: validation/, analysis/, report, figures.

- [x] Independently reconstruct financial fills, fees and target state transitions, including mask and actual-fill effects.
- [x] Audit data-source usage and execution participation, retaining inherited limitations and newly traded events.
- [x] Compare each nested contrast, all years and cost/delay stresses; run paired descriptive bootstrap and bounded same-state event attribution.
- [ ] Review numerical claims, visualize results and save complete new evidence with Git provenance and reproducible data references.

## Completion

Report outcome without promising CAGR30 or treating the best observed trial as a prospective optimum. State if the primary fails even when another arm looks attractive. Archive negatives and explain the cash/rebound tradeoff. No optional strategy search after this frozen matrix.
