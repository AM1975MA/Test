# V3 Corrected: verified tree robustness archive, 24 October 2026

Nine complete artifacts reproduced locally in GitHub Actions and persisted as tracked V3 files.

## Interpretation

Research-only frozen-signal stress tests. No model/risk parameters tuned on CAGR.
All historical 2018-2026 months were previously examined: NOT an independent holdout.
Correlated baskets are not 50,500 independent data points.

## Experiments

- Fees: 0, 10, 25, 50, 100 bps on identical 500-basket next-open executed trades.
- Tree correction gate, alternative held fixed as original ranker's runner-up (10/50bps).
- Fixed original risk logic off/on for baseline vs tree (10bps), certified original no-risk equity parity within 1e-10.
- OOS structural and regime stress: six-month paired bootstrap, exclusion of whole years, 786 unique ticker-pair-month events, clipped outliers and basket quintiles.

## Files

- `archives/*.zip`: all 9 complete original research outputs, including decisions and NAV paths.
- `tables/<experiment>/*`: human-readable CSV summaries and audit tables.
- `ARCHIVE_MANIFEST.json`: immutable GitHub Actions IDs and SHA-256 of every artifact and source file.
- `../../ROBUSTNESS_COST_RISK_20261024.md`: methodology, numeric results, limitations and decisions.
