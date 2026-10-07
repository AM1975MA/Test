# TARGET_REDESIGN_LEVEL2_V1 — Local synthetic validation

Execution date: 2026-10-08. Scope: only branch `research/target-redesign-level2-v1` in `AM1975MA/Test`. Production repos untouched.

## Source identity

- `target_redesign_level2_v1/targets.py`: Git blob SHA `b00843276ad81ed7e5e9f4ad468446db4b0dbb55`.
- `target_redesign_level2_v1/tests/test_targets.py`: Git blob SHA `bcc5d9d73be899f64974a21013b01ba3cbf6a561`.
- Hashes verified by comparing the GitHub connector's blob SHA with local `git hash-object` of the exact Python bytes.

## Execution

Local isolated Python environment with `pandas 2.2.3`; command:

```bash
PYTHONPATH=<parent_of_target_redesign_level2_v1> python -m unittest discover -s target_redesign_level2_v1/tests -q
```

**11/11 synthetic invariant tests PASSED; 0 failures**, including strict next-open entry/exit, source-return parity, cash/market alpha and two-leg cost math, missing BIL without backfill, 21/42/63 horizons, strictly mature training subset, exclusion of intraday Low after exit Open, missing Low risk label without forward filling, order invariance with repeated dataframe indices, and explicit failure on inconsistent labels or absent benchmark.

The same 11 tests passed both with and without an `__init__.py` in the local namespace package; no `__init__.py` was committed.

## Repository baseline facts, not experimental results

According to frozen `evidence_v1/data/original149/coverage.csv`, SPY source history begins 2004-01-02, BIL 2007-05-30, SHV 2007-01-11; all end 2026-07-31 in that frozen coverage table. **BIL cannot support the cash-alpha target before its own availability**. No data were silently synthesized to solve that.

## Not yet performed

No historical all-universe forward-target generation, inter-vintage stability measurement, fit, new-model ranking evaluation, ETF economic replay, CAGR or Sharpe computation occurred in this validation. Passing synthetic tests is correctness evidence for the target generator, **not** evidence of better trading performance.
