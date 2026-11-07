# OLC64 — Ex-ante component-utility association check

**Research only. Do not promote.** A narrow, preregistered *diagnostic* on existing OLC63 outputs; no new training, weights, trading rule or price data. 2019–2026 history is mined and not fresh OOS.

## Run

Requires Python 3.10+, NumPy, pandas, SciPy and original OLC63 files from the Research Library under a sibling directory `/OLC63_Fusion_Attribution_20261107/results`.

```
python run_olc64.py
python verify_olc64_independent.py
```

## Outputs

- `PROTOCOL_PRE_RESULTS.md` — preregistered, committed before running outcomes.
- `REPORT_OLC64_IT.md` — Italian result and interpretation.
- `results/OLC64_MONTHLY_DIAGNOSTIC.csv` — one row per month × hypothesis × horizon (472 rows).
- `results/OLC64_ASSOCIATIONS.csv` — correlations and descriptive circular block CIs.
- `results/OLC64_YEARLY_ASSOCIATIONS.csv` — year-specific diagnostic correlations.
- `results/OLC64_QA.json`, `results/OLC64_INDEPENDENT_QA.json` — provenance and checks.