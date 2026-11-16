# OLC112 independent focused review

Review date: 16 November 2026. Scope: `src/run_rotation_overlay.py`, its six focused tests, the OLC112 design and freeze, and the completed OLC112 ledgers. The already reviewed OLC111 implementation was inspected only at the interfaces reused by this overlay. No model, policy, parameter, source file, or result was changed during this review.

## Disposition

**No Critical or Important correctness finding was identified.** The frozen overlay implements the single declared mechanism change, and the completed run contains all 12 planned paths. One nonblocking interruption/resume issue is recorded below. It does not affect the completed results.

Reviewed implementation SHA-256: `8cb26a10e67afa42e12d5b816d9c8cf9c52db7a1c79323a3431e12f075fd1a2f`.

## Policy and execution checks

| Requirement | Review finding |
| --- | --- |
| Invested scheduled rotation only | The new branch requires a scheduled, noninitial decision and actual marked gross exposure above the unchanged `1e-8` threshold. `current` comes from actual units marked at the decision Close and actual cash, via the unchanged replay engine. It is not an earlier target allocation. |
| All heads ready | All three saved heads must be available at the existing monthly cutoff before the new branch is used. Otherwise the original initial/warmup policy remains authoritative. |
| Pending and queued orders | The new branch requires both no pending order and an empty queue. A ready but busy account delegates to the original BUSY behavior. |
| Baseline target and band | The branch copies the original frozen target, issues reason `SCHEDULED`, and explicitly sets `force=False`. The unchanged engine therefore retains its original 3% rebalance band. |
| No learned override at that monthly Close | The branch records the scheduled action without evaluating CASH or FRESH predictions. This matches the protocol's deliberate restriction. |
| Cash entry and nonmonthly actions | Cash accounts, including scheduled cash decisions, and all nonmonthly decisions delegate to the unchanged OLC111 policy. `allow_scheduled_hold=True` prevents a cash HOLD from falling back to a monthly selector entry. |
| Metadata | The trace and instruction/decision metadata identify the OLC112 output arm while retaining the underlying OLC111 arm. Learned actions retain the original prediction and model-hash metadata. |
| Execution and metrics | Scenario costs and fill conventions are imported from OLC111. Replay, path summaries, annual summaries, drawdown summaries, and common-window calculations use the existing functions without a new metric definition. |

The six focused tests pass. They cover the negative learned-switch monthly case, cash staying out, positive cash ENTRY, a pending order, nonmonthly equivalence, and an actual replay showing that a small monthly allocation difference does not force a trade.

## Fits, freeze, and path accounting

The OLC112 freeze verifies successfully, including its protocol, implementation, 102 input entries, and the recursive OLC111 freeze. Those OLC112 inputs include all 81 saved monthly fit files and the six reused BASE/STATIC_75 control paths' daily, order, and metric artifacts.

The runner checks that every required cutoff file exists before preparing the cache. The existing cache checks provenance, fit options, and serialized model hashes when loading each file. In a separate read-only verification, all 81 cutoffs loaded successfully with `fit_head` replaced by a function that would immediately fail if called. The resulting readiness record exactly matched the frozen OLC111 record. The unchanged options include seed 111, 100 bootstrap samples, 504 minimum dates, 24 minimum blocks, and penalty 1.0. The common first execution remains 4 July 2022.

The completed manifest and score table contain 12 unique path IDs: four arms crossed with three scenarios. Each has daily accounts, orders, instructions, decision arrays, decision metadata, policy trace, and metrics. All three MEAN parity records are present. The 18 original OLC111 accounts remain the source study; the combined research account count is 30, with six original controls reused rather than rerun in OLC112.

Across the saved OLC112 traces, every `INVESTED_MONTHLY_ROTATION` row is scheduled, noninitial, ready, and invested. Its CASH/FRESH/ENTRY prediction fields are empty, as intended. Every corresponding saved decision has `force=False`, the scheduled reason, and the correct output/underlying arm metadata. Monthly cash HOLDs remain visible: 11 in each PRICE path, 18 in each VIX path, and 13/13/15 in TERM NEXT_CLOSE/DOUBLE_COST/NEXT_OPEN.

Recomputing full-window and common-window financial fields from the saved daily accounts using the unchanged native metric function reproduced all 72 checked values exactly. Full-window accounts begin on 2 March 2020; common-window accounts begin on 4 July 2022 using the actual preceding Close NAV. Warmup performance is therefore not credited to the learner in the common-window result.

## Completed-ledger observations

Source: OLC112 `results/SCORES.csv`, `results/MEAN_BASE_REPLICATION.json`, and the corresponding OLC111 score table and daily control accounts.

MEAN_ROTATION has no discretionary orders and reproduces BASE exactly in all three scenarios. The maximum difference is zero for each checked daily field: `nav_open`, `nav_close`, `cash`, `gross`, and `positions`. This is a strong implementation control for restoring the original monthly default on this frozen dataset.

Primary NEXT_CLOSE observations:

| Account | Full CAGR | Full sampled MaxDD | Common-window CAGR | Common-window sampled MaxDD |
| --- | ---: | ---: | ---: | ---: |
| BASE / MEAN_ROTATION | 22.57% | -36.51% | 20.01% | -36.51% |
| STATIC_75 | 18.38% | -30.08% | 16.53% | -28.64% |
| OLC111 PRICE | 18.56% | -36.53% | 14.02% | -36.53% |
| PRICE_ROTATION, declared primary | 15.90% | -36.52% | 10.10% | -36.52% |
| VIX_ROTATION | 12.85% | -36.53% | 5.67% | -36.53% |
| TERM_ROTATION | 21.44% | -36.10% | 18.32% | -27.11% |

The primary price overlay is unsuccessful: it reduces CAGR materially relative to BASE and to its OLC111 counterpart, without a material primary sampled-drawdown improvement. It spends 215 sessions fully in cash. The VIX overlay also loses return relative to both references.

TERM_ROTATION improves relative to the original TERM account, but its CAGR remains below matched BASE in all three scenarios. Its NEXT_CLOSE common-window drawdown is shallower, while full-window drawdown remains dominated by earlier losses. This is an adaptive structural comparison and cannot reverse OLC111's rejected incremental information result or justify selecting TERM after observing these returns.

No OLC112 path meets 30% CAGR. Every actual action family in every OLC112 path has fewer than 12 separated interventions; the maximum family count is eight. The final report must retain this limited-evidence qualification and the protocol's source-mark support disclosures. This focused review does not independently establish source-mark admissibility.

## Nonblocking robustness observation

`previous.save_path(...)` writes `METRICS.json` before the MEAN-specific parity JSON is created. A process interruption between those writes would leave a path that the resume branch initially treats as saved, then rejects when the parity JSON is absent. This is an explicit resume failure rather than silent acceptance or a change in financial calculations. All parity artifacts exist in the completed run, so no frozen-code change or rerun is warranted for this review. A future runner can make the parity artifact part of the completion transaction.

No additional model fitting, parameter search, or account replay was performed for this review.
