# OLC24 checkpoint01 — inputs and pre-outcome verification

2 November 2026. No OLC24 portfolio outcome inspected yet.

- Exact monthly label is archived execution Open-to-Open from the current signal entry to its calendar exit/next entry.
- EU requires the preserved `observed` mask at both endpoints for both compared tickers.
- The authenticated USA state does not contain the original `observed` mask (known upstream gap already documented in OLC17–20). OLC24 therefore requires finite positive prepared Open values for USA and does not claim these certify original observed quotes. No missing value is filled or interpolated.
- Label availability is the next execution date and must be strictly before each annual fitting cutoff.
- Four candidates remain exactly as preregistered: pooled/stratified × recursive/TTL1.
- Local pre-outcome suite: 3/3 tests pass (exact Open label arithmetic/cutoffs; union+TTL1 constraints; AUTH decision parity).

This is a data-availability clarification, not an empirical parameter change.
