# OLC111 resumed-account replay extension

## Scope and API

[`olc111/src/replay_engine.py`](../../src/replay_engine.py) is an isolated copy of the immutable [`olc110/src/engine.py`](../../../olc110/src/engine.py), with only account seeding and optional callback behavior extended. The original execution loop, fees, next-Open timing, missing-Open handling, warmup/window checks, output schema, and instruction precedence remain in place. This is accounting infrastructure, not evidence for a predictive strategy.

```python
simulate(panel, f, policy, decision_mask, *, legacy, ...,
         initial=10000., initial_state=None,
         issue_initial=True, allow_scheduled_hold=False)
```

`initial_state` is a mapping containing `units` (length equal to the asset count) and scalar `cash`, measured at the Close immediately before `start`. The engine copies the arrays, requires finite nonnegative quantities/cash, marks every positive holding using `f['C'][begin-1]`, and requires finite positive seed NAV. Unheld assets need no valid seed mark. Optional `last_buy_idx` and `last_sell_idx` arrays default to `-1`; supplied entries must be integral, between `-1` and `begin-1`. The old `initial` capital is ignored when a seed is supplied. Its existing validation is unchanged when no seed is supplied.

Nonempty `pending` or `queued` instruction state is rejected. Missing keys, `None`, and empty instruction containers are accepted. The seed does not restore a callback's private strategy/controller state. Extra context fields such as previously reported NAV are ignored; NAV is recomputed from cash and actual quantities.

`issue_initial=False` skips only the initial Close callback. It preserves the actual quantities and cash until a later instruction. With the default `True`, the first callback sees the seeded account at `begin-1`; its chosen action becomes executable at Open `begin+lag`.

`allow_scheduled_hold=True` lets an account policy return `None` on a scheduled Close. That produces no instruction and no selector fallback. It therefore preserves quantities through the next opening gap and permits a cash account to remain in cash across month boundaries. Initial account-policy callbacks still require a full instruction. The default remains the original strict behavior.

## Integration contract

For a decision at Close index `k` and a 21-session outcome, use the full original panel/feature calendar, `start=dates[k+1]`, and `end=dates[k+21]` (inclusive). Seed all alternatives with the same actual account at `k`:

| Alternative | Initial call | Subsequent decisions |
|---|---|---|
| HOLD | `issue_initial=False` | Frozen monthly baseline continuation for counterfactual labels |
| CASH | `issue_initial=True`; first target is all cash | Same frozen monthly baseline continuation |
| FRESH | `issue_initial=True`; first target is the frozen fresh basket | Same frozen monthly baseline continuation |

Do not emulate HOLD by returning the current weight vector: a later opening gap would convert that instruction into a rebalance. The learned daily policy may separately use `allow_scheduled_hold=True`; that flag does not impose monthly reentry. Replay callers must exclude decision states with pending/queued instructions or handle them elsewhere. Original defaults remain available for ordinary unseeded simulations.

## Verification

Tests were written before the extension. Against the unchanged OLC110 copy, the new suite ran 13 tests and failed with the expected missing-`initial_state` argument errors. After the minimal implementation, all 13 passed:

```bash
python -m unittest discover -s olc111/tests -p test_replay_engine.py -v
```

[`olc111/tests/test_replay_engine.py`](../../tests/test_replay_engine.py) includes independent hand calculations:

- A HOLD seed of 12.5 AAA units, 7 BBB units and 250 cash retains those quantities through asymmetric gaps: Open NAV 2310 and Close NAV 2442.5.
- CASH from 10/20 units and 500 cash sells at Opens 80/120; ticket 2 plus 1% impact per order leaves 3664 cash, with no same-Close fill.
- Common-state HOLD/CASH/FRESH replays start at the same Open NAV of 1300. Their respective final values are 1400, 1290, and `(1288/1.01)*1.1`, reflecting actual sale proceeds, buy affordability, and price changes.
- Monthly continuation from an original-engine account reproduces daily NAV/cash and later orders exactly, aside from intentionally local instruction IDs. The explicit resumed state is 60/20 units and 1916 cash; the scheduled March 2 transactions leave 1408.02 cash.
- Missing Opens leave liquidation pending. A replay ending before the first accepted quote cannot fill from that future quote.
- Caller mutations cannot alter seeded arrays; invalid capital, quantities, marks, indices, or outstanding instructions are rejected.
- Scheduled HOLD preserves invested quantities through a large gap; cash stays cash until an explicit later ENTRY; initial `None` and default scheduled `None` remain errors.
- Omitted extension arguments and explicit default extension arguments both reproduce every original output exactly, with and without account callbacks, risk reduction, execution lag, missing Opens, and guards.

An additional 44 existing synthetic tests passed when their engine-under-test was redirected in memory to the replay module: all 19 account-policy tests, all 14 guard tests, and 11 synthetic generic engine tests. Frozen files were not modified. The initial adapter attempt had one import-path error (`test_signals`); adding the existing tests directory to `sys.path` resolved it, and the complete 44-test rerun passed. The existing full-panel MOM252 regression was deliberately excluded; no financial study was run for this extension.

Original engine SHA-256: `370958a6f250f60936b50147ae8787b2e590e81660b4d101e5bbdd9d9b0cba5f`.
