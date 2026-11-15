# Auditor CSV precision correction

The first stage2 audit stopped at `DEDUP_DUAL_EXIT63__DOUBLE_COST` because the
independently reconstructed deferred-session count was zero and the recorded
count was one. Every order quantity, signal, cash balance, and NAV reconciled.

The discrepancy was localized to **12 December 2022**, instruction43,
`FR0010405431`. Reading order quantities through pandas' default CSV parser
erased a floating-point cancellation residue. Reading the same frozen CSV with
`float_precision="round_trip"` preserves **1.8189894035458565e-12** adjusted
economic units. The strictly positive executable target is
**1.0721187511947793e-16**. That opening quote is unavailable, so the engine's
literal `(units > 1e-10) or (execution_target > 0)` condition counts a pending
session. The residue is below the economic-position threshold and has no
material financial effect.

Only the auditor's financial CSV ingestion was corrected. The exact deferred
count assertion remains in place; the economic-position threshold remains
`1e-10`. Numerical-residue-only pending sessions are reported separately.
No price, protocol, selector, engine, target, order, cost, or financial result
was modified or rerun to resolve this diagnostic.

`check_csv_precision_regression.py` reproduces both parsing outcomes on the
frozen account and saves the exact event evidence to
`CSV_PRECISION_REGRESSION.json`. The corrected complete account audits are
rerun after this precision correction.
