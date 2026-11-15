# OLC109 optional guard engine

## Change and API

`src/engine.py` is a minimal adaptation of the immutable OLC108 engine. The
four positional arguments and every existing keyword retain their meaning.
The only new keywords are `guard_policy=None` and `guard_mask=None`.

```python
result = simulate(
    panel, features, monthly_policy, monthly_decision_mask,
    legacy=core,
    guard_policy=trend_guard,
    guard_mask=guard_review_mask,
    lag=2,
)
```

`trend_guard(k, current_weights)` receives a copy of the actual account weights
marked at close `k`. It can return `None`, a weight vector, or
`(weight_vector, metadata_dict)`. Metadata is accepted for policy compatibility
and is not recorded by this adapter. A missing mask disables evaluation. A
provided mask must have one boolean value per panel date.

The callback runs only on requested nonfinal closes without a scheduled policy
decision. The initial policy call remains at `begin - 1`; guards do not run on
that initial signal. Ordering on a subsequent close is:

1. A scheduled policy decision.
2. A guard instruction if the guard requests a reduction.
3. The existing volatility reduction if neither earlier branch emits an instruction.

Every returned vector must be finite, nonnegative, correctly sized, and have
total weight at most `1 + 1e-9`, matching the existing engine validation. A
guard addition exceeding `1e-12` in any instrument raises `ValueError("GUARD_ADDS")`,
including when total portfolio exposure falls. Tolerated floating-point
additions are clipped to current weights. A reduction must exceed `1e-12` in
at least one instrument to emit an instruction. `None` and unchanged vectors
create no alert or instruction and do not block the existing volatility rule.

The planned trend guard sets failed held ETFs to zero and returns the other
actual close weights unchanged. That choice belongs to the supplied policy;
the generic engine also permits other reductions. The guard cannot purchase
or reenter a position. Reentry is available through the existing scheduled
policy, whose mask is monthly in OLC109 experiments.

## Execution and accounting

Each emitted guard is an immutable `TREND_REDUCE` instruction with `force=True`
and due index `signal_idx + 1 + lag`. Signal target weights are copied; later
callback calls cannot rewrite earlier instructions or their execution dates.
At every execution attempt, the executable target is the elementwise minimum
of the immutable requested target and the actual opening weights. This is the
same sell-only protection used for `VOL_REDUCE`; it also applies after delayed
execution, asymmetric opening gaps, and partial fills from missing opens.

Guards use the existing pending-instruction machinery, fees, open-observation
mask, missing-open handling, and self-financing account core. The engine does
not synthesize an opening fill. The newest matured instruction supersedes an
older pending instruction, while future instructions remain queued.

`alerts` and `instructions` contain guard events alongside existing events.
For a guard, `raw_weights` contains actual pre-instruction close weights and
`target_weights` contains the immutable requested reductions. `decisions`
remains the initial/scheduled policy ledger; no guard row is inserted. Existing
volatility behavior remains unchanged when the guard is disabled. Combined
guard-plus-volatility operation has a precedence test, although the planned
OLC109 guard arms do not combine both controls.

## Verification

Tests were written before the adaptation. The first guard run executed 14
test methods: the existing-engine equality test passed and the guard cases
failed on the absent public API. The 16 reported failures include validation
subtests. See `guard_tests_red.txt` for the original output.

The final scoped command is:

```bash
cd tests
python -m unittest test_engine test_guard_engine test_signals -v
```

All **34 scoped tests pass**: 12 inherited engine regressions, 14 new guard
tests, and 8 inherited signal tests. `scoped_suite_green.txt` is the final
output and `engine_qa.json` records its timestamp and file hashes. A full
discovery run also passed the 34 tests before concurrent selector tests were
added; its output is `full_suite_green.txt`. A subsequent independent review
observed a temporary missing `cluster_selectors` import during that concurrent
work. This engine handoff does not claim completion of the separate integrated
selector suite.

Guard coverage includes exact no-guard output parity against OLC108 with and
without volatility control; actual close weights; next-open plus two-session
delay; missing-open partial fills; asymmetric opening gaps; immutable queued
targets; schedule boundaries; monthly precedence and reentry; no-op results;
invalid and additive targets; guard/volatility precedence; and complete prefix
invariance under future price, observation-mask, and guard-schedule changes.
The inherited suite includes the frozen TR29 monthly MOM252 parity check at
`1e-10`, account reconciliation, and causal execution regressions.

An independent read-only review found no correctness blocker. It also identified
the regression test's initial dependency on a sibling OLC108 directory; the
final test instead uses the bundled immutable reference below.

## Provenance

`olc108_engine_reference.py` is an unchanged copy of the source engine, included
only to keep the regression tests portable. `engine_change.diff` contains the
complete production-engine change. The source account core, inherited tests,
inherited signals, and TR29 fixture were copied unchanged.

| File | SHA256 |
|---|---|
| Adapted `src/engine.py` | `30af3a38b90b81f502cf95d979209c032416418fd9b31ee60857937e1d1b004a` |
| Immutable OLC108 engine/reference | `5e5dbe59323f355bc4aba57a0f97eb59b0903b78691254aa5df6998fdeb8e2ee` |
| Immutable `source/src/core.py` | `e49bd609bf9e65b6270b03fb9b706070edb3d2717765f37a856dff3d559551d9` |

No original OLC108 file was modified. This adaptation changes simulation
infrastructure only; it makes no claim about investment performance.
