# OLC114 independent review before bank construction

Reviewed on 2026-11-16 by an agent that did not implement the core or model modules. The scope is `cycle_engine.py`, `cycle_core.py`, and `cycle_model.py` against `docs/DESIGN_AND_PROTOCOL.md` and `docs/IMPLEMENTATION_PLAN.md`. The live runner was not present at the time of this review and is **not approved by this document**.

## Finding and limits

**No remaining Critical or Important implementation defect was identified in the reviewed modules.** Their synthetic accounting, causal-feature, plan-timing and model contracts support proceeding to the frozen bank-construction stage. This finding does not certify historical data, the eventual bank, live integration, forecast skill, or account performance. Historical endpoint reconciliation and the later independent account audit remain required.

No historical panel was loaded by the reviewer. No market-data labels, historical model fits or historical account paths were generated. The reviewer edited only this report and `tests/test_independent_boundaries.py`; the implementation was unchanged.

## Source identities reviewed

| File | SHA256 |
|---|---|
| `src/cycle_engine.py` | `7118993936c540cb053660ba29ac3c65380c600ff7a5c101e6c7af288e6b2297` |
| `src/cycle_core.py` | `31fe4843b0e9a1ec70a2cf63a2018322d5c1f9b1390c9ea23ae33077e513a7a5` |
| `src/cycle_model.py` | `cf636346ded649b9be0b1225d7ed34c69d5a34ef91fc933d431332a990252478` |
| `tests/test_independent_boundaries.py` | `043cad847a364cc542adee194b278d3969274f0a93bf3d05901e479545d23717` |

Recheck these identities before relying on the review. Source changes require a targeted reassessment.

## Accounting and complete-plan review

The engine diff against `olc111/src/replay_engine.py` contains the intended opt-in argument, its seeded-state requirement, and the initial action-mask exception. The existing scheduled-mask restriction remains. Default engine paths retain the original implementation; the existing exact frame-equality test passed.

`PlanExecutor` emits a targeted forced sale, recognizes completion only after the held units reach the numerical zero threshold and the last actual sale index follows the signal, and forbids a redeployment decision on the final sale Close. It attempts candidate selection once on the next eligible weekly Close. Its replacement target uses actual cash divided by current NAV, while the engine freezes quantities outside the action mask. Current holdings and future candidate identities are addressed with global asset indices even when a branch executes a reduced panel.

Scheduled handoff is checked before busy-state or discretionary entry logic. It emits the full baseline target with `force=False` and ends the plan. After handoff, the same executor continues to issue the baseline monthly targets through the label endpoint. This matches the protocol's continuation.

**Handoff is not immediate order cancellation.** Under the native scheduler, an older pending instruction may still execute after the handoff signal but before the new monthly instruction matures. The review explicitly tested this at lag one: a monthly signal on index302 is due at304, while the previously pending sale fills at303. This behavior is intentional under the prescribed native scheduling semantics. Reports and plan summaries must not imply that the handoff signal guarantees immediate completion or cancellation. Actual order ledgers govern those events.

The branch subset is the union of current holdings, future monthly targets and future weekly selector candidates. It preserves global ordering and contains every asset that a branch can hold or target; the future union only sizes the execution panel. Initial features and later candidate selection continue to read their own decision dates. An independent full-universe replay confirms every supported plan's terminal NAV and log advantage on a synthetic changing-selector history, including original and future holdings and an unused fifth asset.

`counterfactual_group` enforces the42-session endpoint, branches from the same units and cash, and checks the BASE endpoint against the frozen full-baseline reference when supplied. It invokes the existing held-mark checker on the seed and all realized branch dates. A stale or missing held mark in any branch returns an empty-record censored group, preventing branch-specific survival selection. The existing synthetic stale-branch and forced BASE-mismatch tests passed. Market-data reconciliation remains a separate gate.

## Causal features and selector order

The reviewed PARK8 and REDEPLOY12 vectors match the specified ordering. Held and retained-basket statistics use trailing completed returns. The candidate part describes the candidate available at the initial decision only; the future entry selector is called later by `PlanExecutor`. The known calendar feature uses the first weekly signal strictly beyond `k+1`, not a realized future fill delay. The current absence of a candidate does not invalidate the whole REDEPLOY plan.

`reconstruct_selected_order` preserves the original selector's explicit metadata order and checks half-weight targets exactly. `candidate_for` excludes retained positions and applies the existing126-session pair-correlation condition to each retained position. It permits the outgoing ETF to compete again after its actual sale, as the protocol requires.

An independent future-selection mutation leaves the initial feature vector exactly unchanged but changes the later entry candidate. A separate test confirms that the outgoing ETF is bought again when it becomes the first compatible selector candidate. These are intentional causal behaviors, not an undocumented permanent exclusion.

## Model and training review

`fit_head` admits only terminals strictly before the fit cutoff and numerically inspects only those mature features and outcomes. It validates the42-session horizon for mature rows. Distinct dates, distinct signal months and greedily nonoverlapping42-session outcome intervals all contribute separately to readiness. Repeated legs on a date cannot satisfy independent-date readiness.

Every signal date has total base training weight one. Fixed63-session blocks originate at global index zero; bootstrap multiplicities preserve every row of each sampled date. Matching occupied block support produces paired draws across heads and model families. Ridge uses the full-training weighted representation for bootstrap coefficient refits and an unpenalized intercept with the fixed mean-loss penalty. The single small tree has the specified fixed parameters. Complete numerical estimators, draw provenance, scaler and hashes are serialized without pickle.

The tree inference implementation converts inputs to float32 before testing the stored double-precision thresholds, matching sklearn. Existing tests separately compare the full estimator and all32 bootstrap trees against sklearn, including a boundary that would branch differently without the conversion. These tests passed. Independent duplicated-leg tests additionally confirm that MEAN, RIDGE and TREE forecasts, including their lower percentile, remain unchanged to numerical tolerance when every date's identical legs are duplicated.

The lower tenth percentile remains a heuristic value buffer. This review supplies no evidence that it is calibrated or that complete-plan targets eliminate reference-policy state shift or repeated-history research bias.

## Verification performed

Fresh reviewed-module tests:

```text
python -m unittest discover -s olc114/tests -p 'test_cycle*.py' -v
Ran38 tests
OK
```

Independent adversarial tests:

```text
python -m unittest discover -s olc114/tests -p test_independent_boundaries.py -v
Ran6 tests
OK
```

The six added checks cover:

1. All per-leg plan outcomes and labels against full-universe native replays after asset subsetting.
2. Exact preservation of the retained quantity when its price gaps by170% at the replacement execution.
3. Native maturity of an older pending sale after monthly handoff but before the new monthly instruction becomes executable.
4. Invariance of initial features to future selector changes, while the actual later candidate changes.
5. Outgoing-asset eligibility to compete again after the sale.
6. Date-balanced model invariance to duplicated identical legs, including paired draws and bootstrap lower values.

The first independent run contained one error in the new reviewer fixture: attempting to deep-copy a Python module. Copying only the changed selector-order list corrected the fixture, and all six checks then passed. No implementation fix was required and no historical experiment was involved.

## Remaining integration gates

- Review the runner's monthly cutoff/cache, earliest activation boundary, plan selection, at-most-one-active-plan control, and state/model provenance.
- Freeze the bank inputs and source identities before construction; verify every supported BASE replay and all censor statuses.
- Freeze the completed bank and runner before fits and the15 historical paths.
- Confirm existing BASE and STATIC_75 account parity, matched delayed controls, all path ledgers and common-window denominators.
- Audit actual sale/entry/handoff order relationships independently; do not infer fills solely from plan phase labels.

These gates are separate work and are not claimed complete here.

## Subsequent integration review, before experiment freeze

The root subsequently supplied `src/run_cycles.py` and its integration tests. This section extends the review to that runner; it does not change the earlier source identities or bank review.

| Additional reviewed file | SHA256 |
|---|---|
| `src/run_cycles.py` | `38889e0099ec4f19d1fdcad483bf570e1012a45069b2b266e537690cd23dfadf` |
| `tests/test_run_cycles.py` | `7c6ff8101f07873ed8447b6d7030eea7c5dd19ff56a51e5f1afba5b38d6ad41d` |

**No Critical or Important integration finding remains for the declared populated bank and a nonempty ready evaluation window.** The reviewed runner may be frozen and run under the protocol, subject to its explicit historical parity and independent result-audit gates.

The monthly cache derives each cutoff from the first panel date of that month, applies the mature-only fitting API, validates saved fit provenance and numerical model hashes, and rejects cached maximum training terminals at or beyond the cutoff. The live policy uses its own historical cutoff and requires both heads ready plus the minimum activation index. Preparing later monthly fits in advance does not make them available to an earlier decision.

The policy checks scheduled handoff before busy-state gating or opportunity selection. While a plan is active, it calls the same `PlanExecutor` as the bank and cannot select another plan. It records the actual eligible holdings, units, cash, NAV, feature vector, training-support diagnostics and selected model identity. Qualifying plans use positive mean and positive lower value, then the prescribed lower-value/head/ISIN ordering. Actual branch features are calculated from deployed account states, not copied from reference-bank states.

Path completion writes and hashes all declared ledgers before the metrics file. Resume checks bind a receipt to the requested arm/scenario, experiment freeze, metrics payload and every artifact checksum. Existing-scenario BASE and STATIC_75 paths are compared against all original daily and order columns with exact values. Delayed paths use their own matching controls. Full and common-window metrics use the original native metric function and each path's actual immediately preceding Close NAV.

Fresh integration verification:

```text
python -m unittest discover -s olc114/tests -p test_run_cycles.py -v
Ran9 tests
OK
```

These include the actual live REDEPLOY sequence, pending monthly priority, at-most-one-plan behavior, strict action qualification/ties, cache portability and future-label mutation, activation boundary, exact synthetic controls, and rejection of changed metrics or ledgers. Together with the38 reviewed-module tests and six independent adversarial tests,53 distinct checks were verified across the three commands.

The reviewer also exercised `forecast_diagnostics` independently with a hand-constructed ledger containing unequal leg counts, five rows on three dates, and signals0/21/42. It returned two nonoverlapping42-session intervals, a date-balanced outcome mean of10.666666666666666 and MSE168.88888888888889, matching the hand calculations. The no-action mean control retained zero realized selected advantage, while equal positive plans followed the declared tie order. This confirms the diagnostic does not silently reuse the old21-session interval count or give dates with more legs more total weight.

### Nonblocking reporting edges retained

- If no head pair ever becomes ready, `run()` currently passes `start_idx=None` when assembling `COMMON_POST_WARMUP`, which would compute the full window. That is a generic no-readiness reporting edge, not an executable opportunity or a change in financial paths. A run with absent readiness must not present that table as a ready common period. The actual `FIT_READINESS` must be checked by the result auditor.
- A sale that finishes on the handoff Close, or an older pending sale that fills after handoff but before supersession, may not be reflected in `PlanExecutor.summary.sale_complete_idx` because scheduled handoff has priority. The native order ledger remains authoritative. Derived audit columns should reconcile sale timing and counts from those orders; a missing summary confirmation alone does not establish an unfilled sale.
- The heuristic bootstrap buffer, reference-policy state shift, repeatedly examined history, current-catalog survivorship and price-vintage limits remain unchanged. Passing implementation checks cannot establish predictive information or the target economic improvement.

The reviewer did not construct or refit any historical model, alter the frozen code, or run any historical path while extending this review.
