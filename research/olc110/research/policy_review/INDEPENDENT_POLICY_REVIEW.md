# Independent OLC110 policy review before financial tests

Date: 2026-11-15. Scope: read-only review of the declared protocol, implementation
plan, protection policy, account-policy engine, immutable core, and their focused
tests. No production files were edited. No market-data strategy runs or financial
result files were used. The only additional execution was literal policy-state
regression testing.

## Priority findings

### 1. A base ETF held in the other slot prevents the fresh fallback

**Confirmed by a failing literal-state regression.**

In `src/protection.py`, the admission loop tests whether the slot's primary ETF
is assigned at a positive level to the other slot. Its `continue` skips the entire
slot, including the fresh-opportunity fallback.

A reachable sequence is:

1. Start with base A in slot 0 and base B in slot 1.
2. A exits and is sold; C enters slot 0 as a fresh opportunity.
3. B exits and is sold; recovered A enters slot 1 as a fresh opportunity while C
   remains in slot 0.
4. C exits and is sold. On a valid weekly search date, D is an eligible and
   compatible opportunity, and the account has usable cash and no pending work.

Slot 0's base A is already held in slot 1, so admitting A again is correctly
disallowed. However, this also blocks D, which the independent call to
`fresh_candidate` accepts. The protocol gives base reentry priority and permits
a fresh opportunity when that base cannot be admitted; it does not say that a
duplicate base disables the fallback.

**Required regression:**
`test_primary_held_elsewhere_does_not_suppress_fresh_fallback` in
`test_cross_slot_admission.py`. Expected D target is 0.25; current response is
`None`. The fix should prevent duplicate base entry while still evaluating the
fresh branch.

### 2. A stale CASH asset can claim a different slot's new holding

**Confirmed by a second failing literal-state regression.**

A CASH slot retains its previous fresh asset in `asset`. A later base admission
checks duplicate assignments only when the other slot's level is positive.
Therefore an old CASH assignment and a newly invested slot can both point to A.
The CASH admission loop then checks the total account's A units and interprets
the other slot's new investment as its own unsold outgoing holding.

Reproduction extends the same reachable crossed-slot state:

1. Slot 0 is base A / actual C; slot 1 is base B / actual A.
2. Slot 1's probe A fails and is actually sold. B remains inadmissible.
3. Slot 0's C exits and is actually sold.
4. A recovers and reenters its original slot 0. Slot 1 is still CASH but retains
   `asset=A` from its already liquidated probe.
5. B subsequently satisfies SLOW with usable cash and a free instruction book.

The policy returns `None`: slot 1 sees slot 0's new A quantities as unsold
inventory and suppresses B. This can persist until another transition or the
monthly reset.

**Required regression:**
`test_old_fresh_asset_does_not_claim_other_slots_later_holding` in the same file.
Expected B target is 0.50 after its recovery. The fix needs to release or
distinguish a previously liquidated assignment without weakening the genuine
unsold-position gate while an exit is pending. A cash slot's remembered asset is
not sufficient to establish ownership of later account-level holdings.

### 3. Masked sell-only validation used irrelevant nominal weights

This issue was independently identified by both this reviewer and the root
agent; the root assigned its fix to the engine author. It is recorded here for
traceability, not as a second implementation request.

For current weights `[0.4, 0.6]`, a protective exit of B validly returns nominal
weights `[0.5, 0.0]`, mask `[False, True]`, and `sell_only=True`. The original
engine checked additions across every asset before restoring the untouched
exposure, and raised `ACCOUNT_ADDS` because A's irrelevant nominal 0.5 exceeded
its actual 0.4. Validation must apply to the action mask for targeted actions;
the full-instruction rule should remain unchanged.

### 4. A blocked new slot could immediately enter a probe on its first signal

This was explicitly assigned to the root before this review began. The root
reported adding a regression and a new-assignment admission guard. This review
did not duplicate the fix or its test.

## Focused review observations

The following behavior is supported by the inspected implementation and existing
focused tests, subject to the two cross-slot findings above:

- Targeted execution removes executable quotes outside its immutable mask while
  retaining those prices for NAV marks. The immutable core sells before buying
  and scales purchases to available cash, preserving quantities outside the
  action mask.
- Queue maturity is chronological, and future monthly instructions do not
  prematurely supersede an older eligible instruction. The policy defers new
  intramonth actions while any instruction is queued or pending.
- A probe's promotion requires an actual buy index and a strictly later close.
  The short rebound failure is evaluated before promotion, and SLOW includes
  the configuration's exit veto.
- Monthly retained assignments are matched by asset, so rank reordering does
  not itself reset an existing risk state. Fresh assignments are preserved until
  their exit or the next monthly selection.
- The daily price gates use current `observed` status. Timing-feature rolling
  windows are trailing; `high5_prev` excludes the current close. Candidate
  correlation uses exactly the trailing 126-return window through the signal.
  I found no new future-data access in these inspected policy calculations.

These are code-review observations, not an independent financial audit or a
claim that all simulation paths have been validated. The existing feature
prefix test covers the new timing features; a complete policy/engine prefix
replay remains appropriate for the later declared audit.

## Reproduction

Run from the workspace root:

```sh
python olc110/research/policy_review/test_cross_slot_admission.py
```

At review time, both tests failed with `unexpectedly None`, at the admission
assertions described above. The file imports the existing hand-specified test
fixture; it does not load price panels or call the financial simulator. All
review-created files are confined to this directory.
