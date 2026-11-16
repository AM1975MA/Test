# OLC113 independent design and code review

16 November 2026. Read-only review of financial source and result files. This report is the reviewer's only owned artifact.

## Design review before implementation/results

**Status: no blocking design finding. The completed code review and its verification evidence are below.**

Reviewed `DESIGN_AND_PROTOCOL.md`, `IMPLEMENTATION_PLAN.md`, the complete OLC112 runner, the OLC111 counterfactual-label and action-policy implementations, and the prior research review and OLC110 report.

The experiment addresses a concrete continuation mismatch: the OLC111 label branches follow baseline targets at future monthly events inside a 21-session window, whereas OLC112 cash accounts can remain uninvested beyond those monthly events. The proposed change restores the scheduled target for idle cash accounts. It leaves the saved model predictions, buffers, candidate selector, costs and nonscheduled decisions unchanged.

The following scientific distinctions are correctly preserved:

- Monthly reentry was already tested with technical exits in OLC110. The new question concerns the scheduled continuation of the existing learned-action architecture.
- OLC113 is designed after observing OLC111/112. The historical sample is not an untouched holdout.
- A scheduled reset removes a specific inconsistency but does not make repeated daily actions or the actual policy-state distribution identical to a one-intervention label bank.
- Some trading months exceed 21 sessions; delayed or missing fills can prolong realized cash spells. The protocol makes no universal 21-session limit claim.
- PRICE_RESET remains primary; VIX_RESET and TERM_RESET remain secondary. A favorable secondary account cannot replace a failed primary result or reverse OLC111's rejected incremental TERM forecast result.
- The material economic criterion is fixed before results: at least +3 percentage points CAGR versus BASE with no worse sampled MaxDD on both the complete and common learned windows under next-Close execution. The 30% CAGR aspiration is separate.
- This criterion defines growth improvement with risk non-deterioration. The report must separately state the actual drawdown delta rather than describe a drawdown reduction unless one occurs.
- Matched BASE/STATIC_75 and OLC112 controls, identical dates, actual preceding NAV, cost stress, all years, sparse-cycle limitations and retained negative outcomes are specified.

The implementation contract is sufficiently precise for the runner: scheduled, noninitial, all-head-ready, idle accounts receive the ordinary baseline target with `force=False`; other states delegate to the prior behavior. Missing saved model files must raise before fitting. Complete-path markers follow required receipts.

## Code review

**Status: no Critical or Important finding in the reviewed runner. Ready for root-owned freezing and the predeclared financial run.**

Reviewed the complete `src/run_monthly_reset.py` and `tests/test_monthly_reset.py`, including the final metrics-payload receipt change. The final reviewed identities are:

- Runner SHA-256: `2593078d2acac274a0902ccdaf04423429c6ac38b49692a9f4d15753e01ee798`.
- Tests SHA-256: `350f2ec23e75a00cbb785e2ed9786e4ca10c361a93f84add198a84e45a83a069`.

### Financial behavior

The sole financial policy change relative to OLC112 is removal of the invested-state requirement from an idle, noninitial, all-head-ready scheduled baseline reset. The copied target retains `force=False` and the original three-percent band. The reset branch does not evaluate or issue a simultaneous CASH action. Every other state delegates to the inherited account policy, preserving initial entry, incomplete readiness, pending/queued handling and nonscheduled decisions. The simulator, execution-panel adapter, candidate data and financial summaries are reused without edits.

`monthly_cash_reset` is attached to the trace and instruction metadata only for an issued post-readiness scheduled reset from effectively cash state. Metrics distinguish issued instruction IDs, IDs with at least one actual filled order, IDs without a fill and actual order count. An instruction is not reported as realized merely because its signal date has passed. As the metric's own definition states, one filled order does not imply every intended leg filled.

The source-only fit cache has no fitting branch. It checks source-study provenance, cutoff, fit options and canonical model hashes before reconstructing the saved objects. Missing files fail explicitly. Model readiness is checked against the original artifact before accounts run.

### Artifact integrity and controls

The save routine stages the financial files, writes any exact MEAN daily/order parity receipt and the path receipt, and writes `METRICS.json` last. The path receipt includes all required artifact hashes and the canonical financial metrics payload hash. Resume validates these identities and rejects changed metrics, changed trace bytes, missing required receipts or a different path identity. An interrupted incomplete write may fail explicitly; it cannot silently be accepted as a verified complete path.

The MEAN control checks every daily field and the entire order ledger exactly, including dates and instrument identities, with round-trip CSV parsing. It is stronger than comparing only final equity or a few float columns.

### Verification actually executed by this reviewer

- `python -m unittest discover -s olc113/tests -v`: **15 tests passed** on the final source. The suite includes negative ENTRY overridden by a scheduled reset, unchanged band, deferred/unfilled execution, pending/queued states, warmup/initial behavior, nonscheduled parity, absent-fit refusal, exact MEAN checks, receipt integrity and a synthetic 12-path run/resume.
- Independently deserialized **all 81 existing monthly fit files** using both the original loader and the new saved-only loader. All **648 individual fitted model objects**, head metadata and model hashes match exactly. Readiness is identical. `fit_head` was replaced by a failing sentinel throughout: **zero fitting calls**.
- The synthetic run/resume is a software test on artificial prices. This reviewer did not run new historical financial account paths or inspect OLC113 strategy returns before this review.

The experiment freeze, complete historical account audit, economic materiality criterion and result interpretation remain root-owned subsequent steps. Passing this review establishes implementation conformity on the reviewed behavior; it establishes no strategy performance or predictive advantage.
