# Independent review of OLC111 pipeline

## Scope and current status

Reviewed `docs/DESIGN_AND_PROTOCOL.md`, `src/research_pipeline.py`, the relevant native accounting in `src/replay_engine.py` and frozen OLC110 core, and the existing pipeline/replay synthetic tests. The review is independent of the root implementation. No root code, raw data or historical source file was modified, no financial model was fitted, and no historical account research run was started by this reviewer.

**Current status: pipeline primitives and the full `build_research_bundle` integration reviewed; no important blocking finding remains in the reviewed bank builder.** The primary-execution, terminal-calendar, missing-seed-mark and resume-provenance findings below have been corrected and checked. The final targeted suite passes all ten tests. The later learned-policy portfolio runner is a separate integration surface and was not present in this bank-build review. This is code and synthetic-boundary verification, not a claim that an unexecuted historical bank or model has been independently reproduced.

## Findings sent promptly

### P1 — Primary labels must explicitly receive Close execution quotes

The replay engine internally executes from `panel['O']`. The initial counterfactual wrapper simply forwarded the original panel, which would implement next-Open labels unless the caller deliberately supplied a Close-adapted panel. The original synthetic cost/gap fixture had identical Open and Close prices and could not reveal the difference.

**Primitive fix verified:** the implementer added `execution_panel(panel, 'CLOSE')`, replacing execution quotes with raw `panel['C']` and execution eligibility with `panel['observed']`, while preserving original arrays. The new `test_primary_execution_explicitly_uses_next_close_not_open` has different Open/Close prices and passes: the CASH terminal NAV is EUR8,993 with the Close adapter and EUR7,495.25 under the original Open convention. The native counterfactual still receives the panel explicitly, so the runner must use the Close adapter for baseline training states and every training-bank label.

**Bank integration verified:** `primary=execution_panel(p, 'CLOSE')` is passed both to the actual baseline replay that supplies states and to every invested/cash counterfactual call. The bank uses the normal EUR1 +15bp costs. Stress-path reuse of the bank/fits belongs to the later portfolio runner.

### P2 — Future monthly feature calendar must extend to the final known month end

`state_features` requires a monthly event strictly after decision index k. The original OLC110 `decision_mask` intentionally leaves the final panel row False because no later fill is observable. On the restored data, the last date is 2026-10-30 and the last True in the original monthly execution mask is 2026-09-30; there are 22 rows after that event. With that mask reused for features, all three heads return None on 2026-09-30 itself and throughout October, producing unintended missing feature support at inference.

**Fix agreed with implementer:** use a separate feature calendar with the known terminal month end 2026-10-30 set True while preserving the original execution mask. That supplies the strictly future event for 2026-09-30 through 2026-10-29. The terminal 2026-10-30 row itself does not require a nonterminal policy call. The helper can also accept a longer calendar vector when future known calendar events lie beyond the observed price array.

**Fix and bank integration verified:** `feature_monthly_schedule` copies the execution mask, guards that the source endpoint is a known business month end, and sets only the feature mask's last row True. `build_research_bundle` passes that separate mask to `state_features`, retaining the original monthly mask for account execution. The terminal-calendar regression passes. An additional read-only check used the actual panel calendar and synthetic constant returns: at 2026-10-29, all three heads are present, the next-event feature is exactly 1/21, and the original execution mask remains unchanged. A source endpoint inside a month raises `EXPLICIT_FUTURE_EXCHANGE_CALENDAR_REQUIRED` rather than silently treating it as month end.

### P3 — Unsupported seed valuation must also enter the censor path

The counterfactual wrapper catches missing-mark `AssertionError` raised during replay, but a seeded held position with an invalid/nonfinite current `f['C'][k]` is rejected earlier by the replay seed validator as `ValueError('INITIAL_STATE_MARK')`. In the initially reviewed wrapper that error escapes rather than returning a matched censor status.

Actual baseline-derived seeds may satisfy the upstream finite-mark precondition naturally, because their baseline replay already validates marks. The wrapper nevertheless needs either an explicit supported-valuation precheck/censor or a documented and checked upstream guarantee. Other accounting/configuration ValueErrors must continue to stop the run rather than being hidden as missing data.

**Fix verified:** the wrapper now catches only `ValueError('INITIAL_STATE_MARK')` as `CENSORED_MISSING_MARK`, preserving fail-fast behavior for other ValueErrors. `test_unsupported_initial_held_mark_censors_whole_comparison` passes and confirms there is no fabricated `net` result.

### P4 — Resume must validate frozen provenance before trusting caches

The first bank-build version accepted existing selection, baseline-state and event-bank files under `resume=True` without comparing code, protocol or input hashes. A resumed run could therefore mix cached outcomes with changed code or inputs despite the error message requiring an unchanged freeze. This does not affect an initial fresh run, but it is material for interrupted research.

The implementer was notified before bank execution and added a behavioral regression. During the reviewer's concurrent test run, that new test was observed in its intended red phase: `test_resume_rejects_changed_input_instead_of_trusting_cached_labels` failed because the verifier had not yet been implemented. The other nine pipeline tests passed.

**Fix and regression verified:** `verify_bank_freeze(root)` now runs before bundle preparation. It checks every declared code/input SHA-256 and the protocol SHA-256, fingerprints the exact freeze bytes, rejects a different cache fingerprint, and refuses preexisting caches without provenance. The final test run passes all ten tests, including rejection of an altered source while the cache remains present. The freeze manifest must enumerate the transitive frozen selector/core modules, new pipeline/replay/Cboe modules and all relevant NPZ/used-Cboe input files; this reviewer explicitly communicated that requirement to the implementer.

## Price feature review

The code correctly converts each ETF's trailing log returns into simple returns, weights them by today's actual ETF weights without renormalizing away cash, and then converts the basket's simple returns back to log returns. It uses exactly the 63 trailing sessions through decision Close k. The synthetic future-return mutation check confirms values after k do not alter the current feature.

NM21/NM63 divide trailing 21/63-session log-return sums by the trailing 63-session sample standard deviation times the square root of the respective horizon. The daily floor is 0.01/sqrt(252), as frozen. Volatility ratios, gross exposure and held/fresh basket correlation follow the specified shapes. Zero-weight assets with missing history do not contaminate the basket. The monthly-distance helper correctly excludes today's event; its finite-array tail problem is P2 above.

Representative grouping and breadth construction are outside this primitive and therefore remain runner integration checks: original complete-linkage 0.85 representatives at the initial/monthly dates, carry identities forward, and drop representatives that are no longer liquid today.

## Matched counterfactual accounting review

The wrapper retains every initially held asset, every current fresh-target asset and every target asset at future monthly dates strictly before terminal k+21. Because the frozen selector ignores branch current weights, those precomputed targets can be common continuation targets without changing the selector. The native core retains full cash, NAV, sell-first self-financing, actual per-order fees, gaps, immutable instruction timing and delayed fills. Subset asset ordering preserves original order; the omitted assets have neither initial holdings nor any executable target during the comparison.

HOLD sets `issue_initial=False`, retaining units and cash and correctly skipping a monthly intervention at k. CASH/FRESH initial instructions are forced through the engine's existing INITIAL behavior, consistent with an upstream explicit no-op filter. All branches start from the same seed and follow only future monthly decisions j>k. The terminal is exactly Close k+21, with no terminal liquidation. Net advantages are log terminal NAV ratios to the HOLD branch, so transaction costs are already included.

The actual-row no-op/zero-fresh filtering belongs to the bank and daily policy caller, because `counterfactual_values` intentionally accepts an explicit action set and does not enforce that action menu itself. Bank integration is verified: invested FRESH comparisons require `fresh_is_action(current, fresh)` and supported FRESH features; zero-exposure fresh baskets never receive ENTRY labels. Under the frozen selector every positive fresh basket has gross exposure at least 0.5, so the separate ENTRY positive-exposure check also satisfies the 3% zero-account difference threshold. The later daily policy caller must preserve the same action menu.

## Missing tails and matched censoring

The existing stale-mark validator reconstructs held units from the native order ledger, checks the signal Close and every realized Close, derives each last accepted positive raw Close causally, and rejects ages above five calendar days or unsupported marks. Any failed branch returns a censor status for the comparison before a `net` result can be returned. RIGHT_EDGE comparisons return a status and terminal index, never fabricated zero labels. Native nonfills remain in successful outcomes and are counted as deferred sessions. P3 covers the initial valuation exception gap.

## Existing synthetic verification run by reviewer

```text
python -m unittest discover -s tests -p test_research_pipeline.py -v
Ran 7 tests in 0.114s
OK

python -m unittest discover -s tests -p test_replay_engine.py -v
Ran 13 tests in 0.389s
OK
```

The replay suite checks unchanged default outputs against the frozen original, seeded HOLD/no-op behavior, shared economic starts, exact gap/cost examples, resumed monthly continuation, missing Open behavior, no fills beyond the replay window, copied seed arrays, strict default scheduled-None semantics and explicit scheduled-HOLD permission.

After the terminal-calendar, missing-seed-mark and cache-provenance fixes, the reviewer reran the complete targeted pipeline suite:

```text
python -m unittest discover -s tests -p test_research_pipeline.py -v
Ran 10 tests in 0.161s
OK
```

The observed intermediate red resume test is recorded under P4; it was resolved in this final green run rather than omitted from the review history.

## Full bank-build integration review

`build_research_bundle` performs the following correctly by inspection:

1. It loads the preserved OLC110 inputs and unchanged `DEDUP_DUAL_TREND_OPP` selector. The selector's current-weight argument is unused for that frozen arm, so precomputing its causal daily target from a zero-vector argument does not alter selection.
2. It creates complete-linkage 0.85 representative groups at the initial date and original monthly Closes, carries representative identities forward, and removes currently nonliquid or nonfinite-m63 representatives before computing positive-m63 breadth. There is no future-group lookup.
3. It captures baseline units, cash, NAV and pending state inside the account callback **before** returning that Close's scheduled instruction. Snapshot indices are stored explicitly. The bank loop indexes all account arrays by their original `enumerate(snapshot_idx)` position, so skipping the initial snapshot does not shift account alignment.
4. Invested comparisons start from captured actual units and actual cash. The conditional ENTRY comparison starts from zero units and cash equal to the same captured baseline NAV. ENTRY features do not depend on held-book features, so using the already computed fresh-basket ENTRY vector is consistent. These conditional labels are not reported account profits or a hypothetical free liquidation.
5. Pending/queued baseline states are marked busy and excluded from new interventions. Every information ablation will consume the same head-specific bank rows, because Cboe-unavailable dates are excluded before any row is appended. Cash and invested groups preserve their own censor statuses rather than imputing an outcome.
6. The bank retains source-unavailable, busy, RIGHT_EDGE, invested and cash comparison statuses in its event JSONL. Censored comparisons cannot contribute a `y`; successful rows carry both signal and terminal indices. RIGHT_EDGE signal index plus the fixed 21-session horizon gives the endpoint dependency, while successful comparison records store the terminal explicitly.
7. Initial CASH/FRESH orders are forced by the native INITIAL path; future monthly continuation retains the original non-forced monthly band. Costs enter terminal wealth and log-ratio labels once. No learned continuation is used in labels.

## Remaining surfaces outside this bank-build review

- Later learned-policy runner: stress runs must reuse the same models, monthly post-warmup HOLD must remain a true no-order, missing Cboe features must fall back to the matching PRICE model, and missing required head support must preserve the frozen warmup behavior.
- Final study report: source-unavailable/censored counts, readiness dates, endpoint dependencies, model hashes and conditional-label versus repeated-account distinctions must remain visible.

## Reviewed file identities

Recorded at 2026-11-16T19:19:22.253901+00:00. Subsequent code edits require renewed review of the affected behavior.

| File | SHA-256 |
| --- | --- |
| `docs/DESIGN_AND_PROTOCOL.md` | `8c826bb50a67bcf9bbb723aa0eb85f34b788b21713d2c756f8d12ef55995df84` |
| `src/research_pipeline.py` | `64a09ca31077b24696de6d3d95395f9825e045fdc16422dd476f8cf968b84e35` |
| `src/replay_engine.py` | `ad4ebbb81620456e61bf0d833fd999c7a1a0026acb0a5f0370a0c51c33d39a1a` |
| `tests/test_research_pipeline.py` | `5d76ba374722bdf3088c4360efac7dbc33dc0f1c183a5bc5f7e2cd08b27e0e8b` |
| `tests/test_replay_engine.py` | `2d464d380ad77e0362d0f3ecc17c1b763c3d16fa4d5287a6585560132120c737` |

## Bank freeze inspection

The final `docs/BANK_FREEZE.json` was read and independently checked without invoking the mutating verifier: all 12 declared code hashes, all 5 input hashes and the protocol hash match the current bytes. The manifest includes all transitive OLC110 selector/core modules, the new pipeline/replay/Cboe/model modules, both preserved NPZ inputs and the three used Cboe CSVs. No bank preparation, historical replay or fitting was invoked for this check.

The final protocol was reread after its pre-run clarification: monthly fit cutoffs use the first panel session independently of bank-row missingness, and all three heads must be ready before learned overrides. The later portfolio runner should be checked against that all-head readiness condition.
