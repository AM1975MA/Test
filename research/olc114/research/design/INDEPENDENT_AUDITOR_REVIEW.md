# OLC114 independent review of the results-only auditor

Reviewed on 2026-11-16. Scope: material false passes in `src/analyze_cycles.py` and `tests/test_cycle_audit.py`, including account reconstruction, masks and delayed instructions, actual plan execution, source identities, and whole/common-window metrics. The reviewer did not implement the auditor, change frozen financial code, refit models, or rerun historical policies.

## Disposition

**The bounded review is closed with no remaining Critical or Important finding after the corrections below.** A fresh targeted run passed 13/13 audit tests. The separate final 15-path numerical audit must complete successfully using the reviewed bytes; this document does not replace that execution receipt.

| Reviewed file | SHA256 |
|---|---|
| `src/analyze_cycles.py` | `f718626065a6addae2f4c4dc5de0b8407e312a479b0d99285aeae141e0114bd9` |
| `tests/test_cycle_audit.py` | `2e4b5b3b63d3b6878408c23bd83e969575989364672863a9a0520d0da88991f2` |

## Resolved material false pass

The original reconciliation checked order arithmetic, price acceptance, fees, masks, instruction timing and the account balance, but did not independently constrain trade sizes to the immutable instruction target. The reviewer reproduced a false pass with the auditor's synthetic fixture:

- Account wealth: EUR10,000.
- Recorded BUY: 40 units at EUR100, EUR4,000 notional.
- Altered immutable target: 20%, implying a EUR2,000 requested holding.
- Other order and daily fields remained internally consistent.

`reconcile_account` originally returned `pass_all=True` with every reported numerical error equal to zero. This was an auditor-boundary defect; it did not establish an error in any frozen financial path.

The corrected auditor now independently calculates the execution implied by each already-recorded instruction. It applies the actual marked account wealth, forced versus 3% band behavior, sell-first sequence, available cash, fixed and proportional fees, executable quote mask, stale sell-only clamp and proportional purchase affordability. It checks the number, side, asset, quantity and notional of all observed fills. The reproduced case now raises `TARGET_EXECUTION_MISMATCH`.

The auditor also verifies the signal's raw-to-final target transformation against reconstructed account weights, including preservation of unaffected exposure and the involved budget cap. This closes the related possibility of valid-looking fills executing an unintended final target.

Two narrow attribution contracts were completed during the same review:

- Every nonscheduled instruction ID must belong to an attributed plan sale or replacement entry, regardless of its reason string. The previous reason-specific checks alone could omit an unexpected instruction name. Inspection of all 15 actual instruction ledgers found only prescribed instruction reasons.
- A PARK or REDEPLOY sale must request a completely zero raw target, in addition to the correct single-asset mask, sell-only flag and forced execution. This prevents a consistently recorded partial reduction from passing as the prescribed full-position sale. The new partial-target test fails before the correction and passes after it.

No native account path, trained model, bank label or financial-source freeze was changed to resolve these findings.

## Other reviewed boundaries

The account reconstruction follows immutable due indices, including the extra-session execution delay, and the native rule that only a newly matured instruction supersedes an older pending one. Quote availability outside a targeted instruction's mask does not create an execution deferral. The auditor checks accepted execution prices, fees, quantities, cash, NAV before and after fees, exposure, inventory counts, unaffected units and five-calendar-day held-mark support.

The policy audit reconstructs actual account states and independently regenerates the specified feature vectors and saved-model predictions. Plan qualification, ranking, full-position sale, first eligible weekly attempt, candidate identity, available-cash entry budget, monthly handoff and attribution are checked against native instructions and orders. Sale confirmation is derived from actual fills and zero inventory before the applicable callback boundary, rather than trusted from a phase label. A sale on the terminal or handoff Close can lack a subsequent policy confirmation while still being a real fill; the audit preserves that distinction.

Each result receipt is bound to its expected path, arm, scenario, experiment freeze, metric payload and complete artifact set. Bank rows are reconciled with their sealed event outcomes, and saved fits are checked for strict maturity, date weights, training hashes and paired bootstrap support. Source and result hashes are recorded for review. The auditor imports no fitting or policy-simulation entry point. Its new fill calculation is arithmetic verification of recorded instructions, not a new strategy run.

Whole-period and common-period metrics are calculated independently from daily NAV. The common period uses each account's own actual Close NAV immediately before its first evaluated return. Native metrics and score-table fields are compared with those recomputations. These calculations preserve the distinct economic interpretation of the two windows.

## Independently checked primary results

The reviewer separately recomputed the following values directly from the frozen daily ledgers using the independent metric helper:

| NEXT_CLOSE account | Full CAGR | Full sampled MaxDD | Common CAGR | Common sampled MaxDD |
|---|---:|---:|---:|---:|
| BASE |22.5708075% |−36.5142343% |20.0121340% |−36.5142343% |
| TREE_CYCLE |23.4912916% |−36.1035644% |21.4033591% |−27.2365351% |

The full window is 2020-03-02 through 2026-10-30. The common window is 2022-07-04 through 2026-10-30. Both accounts happen to have the same actual preceding Close NAV, EUR17,631.835384592854, because their earlier warmup paths match; the calculation nevertheless reads each account's own value.

TREE therefore improves common-period sampled drawdown by 9.2776992 percentage points while increasing common CAGR by 1.3912251 points. Its full-period CAGR improvement is 0.9204841 points. The drawdown improvement after model availability should be reported clearly. The predeclared +3-point CAGR criterion in both windows and the separate 30% CAGR aspiration remain unmet.

## Verification receipt

Fresh bounded verification after all corrections:

```text
python -m unittest discover -s olc114/tests -p test_cycle_audit.py -v
Ran 13 tests
OK
```

The tests include the reproduced balanced-but-target-inconsistent fill, full-zero sale target, retained-budget transformation, out-of-mask fill, lag-one maturity, unrelated missing quote, altered fees, actual preceding NAV, strict weekly entry, terminal sale confirmation and 42-session counting. No core/model/runner suite or additional financial experiment was repeated for this review.
