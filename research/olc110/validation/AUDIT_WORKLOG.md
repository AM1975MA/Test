# OLC110 independent validation work log

Scope: Task 4 in docs/IMPLEMENTATION_PLAN.md; source contract is docs/DESIGN_AND_PROTOCOL.md. All work remains under validation/. No production or prior-study changes.

Independent reference files import only standard Python/numerical libraries and each other. The selector/account reconstruction adapts the independent numerical conventions in OLC109 validation, with local copies and explicit provenance. Separate prefix behavior tests may import production; they are not claimed independent reconstructions.

Pre-flight: the masked account-policy interface adds actual holdings, last-fill dates, and pending instructions. The reference must independently derive nominal intentions, mask, executable target, timing, all fills, and slot states. It must not accept recorded targets as its decision oracle.

Ruling: no new worktree or commit is created by this audit worker because the parent owns the existing isolated OLC110 research directory and controls financial freeze/versioning. All validation edits are confined to the assigned directory.

Progress: protocol read; independent selector, state, and account reference construction in progress; results not yet available. Final raw-weight serialization alignment awaits production freeze. Behavioral verification and full 78-path run are required before completion.

Completed: independent price/selector reference reproduces all 80 OLC109 monthly targets. Protocol reference includes frozen vacancy latch and active-owner monthly matching. Ten literal account/state cases pass.

Ruling: post exact serialized fills only after independently deriving and validating each order's size, price, cost and date. A separate arithmetic chain produced 5.68e-14 residual units at signal 789; strict-positive descriptive positions differed despite NAV within 1e-11 EUR. This is documented in AUDITOR_PRECISION_NOTE.md; no production/input/result alteration. The cost of this ruling is explicitly limiting the claim to independently checked decisions and a verified-fill ledger, rather than asserting bitwise equivalence of unrelated floating-point arithmetic chains.

Completed: 78/78 paths passed; 32,533 orders, 20,810 targets, 183,492 slot-state rows; five OLC109 baseline replications exact; 546 annual rows and 312 segment rows validated. Future perturbation: 78 comparisons pass across three dates, all arms and delayed-Open/NEXT_CLOSE modes. Ten in-memory material corruptions rejected. No material production discrepancies were found; no financial code modifications were made.
