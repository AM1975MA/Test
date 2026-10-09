# Execution plan — Compact21 training-source attribution

1. Freeze and version the experiment contract in PREREGISTRATION.md, use a research branch from the already verified 2026-10-07 rolling-window research tree.
2. Test a pure training-cohort mixer: identical keys required, only the 125 features or the label-side columns may be replaced, strict cutoff, reject malformed/mismatched inputs and unexpected mutation.
3. Reuse the existing pinned CI environment and source/BASE gates; fail closed on any mismatch before treatment fitting.
4. Execute 2017–2026 year-parallel native/common source factorial, with exact independent refits; retain full common predictions, source and matrix audit hashes.
5. Validate complete year/pair/vintage coverage and read metrics pooled by actual query date, retaining all pairs separately.
6. Report scientific attribution, known development-data limitations and next single-target experiment. Do not rerun financial optimization or change production. Remain draft/no merge.
