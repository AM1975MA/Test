# OLC05 — representation and gradual capital transfer

Read RESULTS_IT.md and the three chronological protocol documents. This batch tests known synthetic aliases and capital transitions. It does not train a time-to-event model, establish real economic ETF equivalences, or certify live execution. Original CL01 selectors stay frozen.

## Repository versus delivered checkpoint
This directory preserves the complete new computational core, unit tests, input-restoration code, verification/replay runners, protocol and numerical summary. Large position books, input prices, frozen forecasts and source dependencies are in the delivered conversation archives, NOT implicitly uploaded here. The full Italian REPORT_IT.md, all CSV tables,112NAV/position books, logs, full reflections and hashes are in those archives. The complete checkpoint additionally contains the exact input subset needed to rerun, the original action engine and eight archived reference paths. No new market download is required.

For this checkout or the small package, obtain the previously delivered OLC01 checkpoint and paired-frontier results ZIP and run `python restore_inputs.py --archives /path/to/archives`. SHA256 is checked before extraction. The full checkpoint already contains source/. Never load an unverified pickle from a different source; the included Open files belong to the hashed parent archive.

## Reproduce
Environment used: Python3.13; numpy2.3.5; pandas2.2.3; pytest9.0.2; matplotlib3.10.8. From this directory:

```
python -m pytest -q
python src/duplicate_audit.py
python src/parity.py
python src/run_transitions.py
python src/run_finite.py
python src/run_sensitivity.py
python src/verify_and_analyze.py
```

These commands reproduce alias diagnostics,8reference checks,72initial paths,16finite paths,24post-observation sensitivity paths and numerical checks. There are112final economic paths, not112independent observations. pytest.ini limits this experiment to tests/. Initial collection of restored historical fixture tests had four import errors, retained in the delivered logs; the whole historical repository is not declared green.

ALL_SCORECARD uses actual next-Open valuation dates and excludes the terminal flat observation. LEGACY_DATE_CONVENTION retains previous2021–2024labels for reconciliation. Paired bootstrap uses48complete2021–2024months or completeFeb2019–June2026months; resampling support is not a posterior probability. BEFORE_* outputs in the checkpoint are superseded and excluded from conclusions.

Legacy fees are not per-side broker tariffs. Primary ticker-net costs have an explicit ordered-slot bridge; V6/cash retain separate accounting. V6 targets are frozen. LAG1 delays shared gap/breadth inputs and also changes stop eligibility; it does not certify fills. Fractional quantities, survivor/price data, quote timing and minimum order size remain live-trading limitations.

Branch research/olc05-representation-transition-20261031. Protocol527d115503dc06c57658d56b91fb64b9964fac46; finite follow-upb833d611dedb36e03f24fc9067cbff330b86fd21; sensitivity1506503b3c597b2e7014051fdd05bc96544ed7ce. Main unchanged. No new model fit, trading action or background computation promised.
