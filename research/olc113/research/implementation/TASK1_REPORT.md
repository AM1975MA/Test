# OLC113 Task 1 implementation report

Status: policy and runner implemented; synthetic verification passes. No real OLC113 financial path was executed by this worker. No experiment freeze, saved model, or remote Git operation was created or changed by this worker.

## Scope and behavior

Only these assigned files were authored:

- `olc113/src/run_monthly_reset.py`
- `olc113/tests/test_monthly_reset.py`
- `olc113/research/implementation/TASK1_REPORT.md`

`ResetOverlay(bundle, arm, fit_cache)` derives from the unchanged OLC111 `AccountPolicy`. After readiness of all CASH/FRESH/ENTRY heads, every idle noninitial monthly signal returns the original baseline target, including a fully cash account with a negative ENTRY estimate. Its reason remains `SCHEDULED`, force remains false, and status is `MONTHLY_BASELINE_RESET`. Initial, partial warmup, nonscheduled and busy-account cases delegate to the parent. Metadata/trace preserve both the output RESET arm and underlying source arm.

The native simulator is reused directly: no execution logic was copied. The original 3% scheduled band and the next accepted bar govern fills. The four RESET arms and three inherited scenarios yield exactly twelve paths.

`monthly_cash_reset` in trace/instruction metadata identifies an issued postreadiness scheduled reset whose preinstruction gross exposure was at most 1e-8. Metrics report issued instructions, instructions with at least one actual order, instructions with no actual order, and order count. These remain separate from the inherited learned ENTRY counts. An unfilled instruction is not represented as a completed entry or as a discarded pending instruction; missing quotes can keep it pending at study end.

`SavedOnlyFitCache` reuses cutoff/readiness methods and deserializes the frozen model representation with original provenance, options and model-hash checks. There is no fitting branch or call to `fit_head` in the implementation. A missing saved fit raises `SAVED_MODEL_MISSING_REFIT_FORBIDDEN`.

`verify_freeze(root)` validates the OLC113 hashes/protocol/matrix and recursively invokes the OLC112 verifier, which checks OLC111. `run(root, resume=False)` calls this before building the bundle or simulating any financial account. Root owns creation of the actual freeze.

Artifact saving uses the old pure serializer in a temporary staging directory. It publishes all normal account artifacts, computes the exact same-scenario MEAN baseline comparison, writes all receipts, and writes the final path `METRICS.json` last. The parity comparison covers every daily field and every field/row of the complete order ledger with exact numeric comparison. If MEAN has no discretionary filled orders, any difference raises. A discretionary MEAN result retains an honest parity-false receipt instead of asserting unconditional parity.

Every path has a `PATH_RECEIPT.json` containing hashes of all required artifacts and the canonical metrics payload. Final METRICS links to that receipt. Resume validates all artifact hashes, metric payload, path identity and required receipts, and independently recomputes MEAN parity against frozen BASE. A missing receipt or a corrupted artifact/metric aborts resume rather than accepting a completed marker.

## Test-first evidence

Before authoring the runner, the initial new suite ran with thirteen expected assertion failures because `olc113/src/run_monthly_reset.py` did not exist. The failure message was `OLC113 monthly reset runner has not been implemented`; all failures had that cause. Command:

```bash
python -m unittest discover -s olc113/tests -v
```

After implementation the same thirteen tests passed. A synthetic matrix/resume test then exercised all twelve paths without real input data or fitting. A further test exposed that edited METRICS values were initially accepted even with intact data: its red run failed with `AssertionError: ValueError not raised`. Adding the metrics-payload digest repaired that case. Final new-suite size is fifteen tests.

The meaningful cases cover negative-entry cash reset; suppression of a same-close learned exit; next accepted bar with an intervening rejected quote; unavailable reset remaining unfilled; unchanged 3% band; pending and queued preservation for invested/cash accounts; nonscheduled prediction/target equivalence; initial and partial readiness equivalence; a no-fitting sentinel on missing saved fits; deserialization of actual ready saved models without fitting; exact daily and whole-order parity including tiny numeric mutations and identity changes; receipt-before-marker ordering; missing/corrupted receipt/artifact/metrics rejection; a complete synthetic twelve-path run and resume without refitting or reexecution; and the prefreeze execution gate.

## Verification

All commands were run from `/workspace/scratch/23237d81ce2c`:

| Command | Result |
| --- | --- |
| `python -m unittest discover -s olc111/tests -v` | 77 passed, zero failures/errors |
| `python -m unittest discover -s olc112/tests -v` | 6 passed, zero failures/errors |
| `python -m unittest discover -s olc113/tests -v` | 15 passed, zero failures/errors |
| `python -m py_compile olc113/src/run_monthly_reset.py olc113/tests/test_monthly_reset.py` | Passed |

The new test matrix uses constant-price, two-instrument synthetic accounts in temporary directories. The logged toy CAGR/DD figures are validation output and are not OLC113 research findings. New tests create no fitted models; they use constant predictors or read an existing ready model file. The inherited OLC111/112 suites retain their own original synthetic fit tests.

## Integration notes and limits

The inherited `build_research_bundle(source, resume=True)` rewrites deterministic OLC111 aligned-data/bank archives and summary metadata, as OLC112 already does. This worker did not invoke that real-data preparation. Source selection/state/bank artifacts must already be present; recursive freeze validation at run end checks frozen inputs for any changed bytes. Root was notified of this inherited side effect before any real run.

No actual economic result, real MEAN baseline parity, audit of the twelve real paths, or final source freeze is asserted here. Those belong to the independent review/freeze/run and audit tasks. Exact baseline parity is enforced before the real MEAN path completion marker, so any mismatch will fail visibly.
