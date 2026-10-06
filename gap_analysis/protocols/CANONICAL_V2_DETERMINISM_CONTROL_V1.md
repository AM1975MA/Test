# Canonical V2 determinism control V1

Date: 2026-10-03
Parent line: `ETF_TRADER_149_VS_EU120_GAP_ANALYSIS_V1`

## Motivation

Three consecutive Yahoo/yfinance 0.2.66 downloads of Original149 differed only at ppm-scale in OHLC/returns, yet canonical Annual V2 replay CAGR ranged from 29.7534% to 34.6771% (span 4.9236 pp). Before attributing that spread to raw-data perturbations, isolate computational non-determinism.

## Frozen raw input

Use **only `_repeat2`** from workflow run `37121749852`, artifact `yfinance-repeatability-v1-raw`. The exact same raw bytes are used in every replay below. No new Yahoo download is permitted.

## Frozen productive source and environment

Use the same canonical V2 Git-blob gate already used by the 31.603995% fresh replay and the repeated-snapshot replay. Use the same canonical runner blob `ebd578e0d92e986adb5c2fbf265a346f87b7218e` from `research/v2-same-source-149-vs-70-20261002`.

Pinned versions:
- Python 3.13
- numpy 2.3.5
- pandas 2.2.3
- scikit-learn 1.8.0
- xgboost 3.1.3
- numba 0.65.1
- yfinance 0.2.66

Thread contract:
- OMP_NUM_THREADS=2
- OPENBLAS_NUM_THREADS=2
- MKL_NUM_THREADS=2
- NUMEXPR_NUM_THREADS=2
- ETF_TRADER_XGB_THREADS_PER_WORKER=1
- ETF_TRADER_XGB_WORKERS=3

## Control A — cross-runner repeatability

Run the full source-only Annual V2 rebuild three independent times on three GitHub-hosted Ubuntu 24.04 jobs. All three use byte-identical `_repeat2` raw input, source blobs, package versions, runner script and thread contract.

Purpose: detect run-to-run / hardware / process / library nondeterminism while raw data is held constant.

## Control B — same-runner sequential repeatability

On one GitHub-hosted Ubuntu 24.04 job, execute the same full source-only Annual V2 rebuild three times sequentially in independent output directories against the exact same `_repeat2` raw directory.

Purpose: remove cross-runner hardware/region variation and test algorithm/process nondeterminism on the same host.

## Predeclared diagnostics

For each replay save:
- CAGR, MaxDD, Sharpe, terminal equity, turnover;
- SHA256 of Titanium, MA3 panel and predictions from `RESULT.json`;
- SHA256 of `DAILY_LEADERS.csv`;
- raw-directory aggregate SHA256.

For each control compute:
- CAGR min/max/span in percentage points;
- number of unique Titanium hashes;
- number of unique MA3 panel hashes;
- number of unique prediction hashes;
- number of unique daily-leader hashes.

## Interpretation rules

- **Deterministic PASS:** all three CAGR values agree to `1e-10`, and Titanium, MA3 panel, prediction and daily-leader hashes are each unique-count 1.
- **Numerically different but economically stable:** CAGR span <= 0.25 pp, regardless of non-economic serialization/hash differences.
- **Material computational instability:** CAGR span >= 2.0 pp with byte-identical raw input.
- Between 0.25 and 2.0 pp: non-trivial instability requiring localization before interpreting the 149-vs-EU120 gap.

No model parameter, seed, thread count, source file or raw data may be changed after observing these controls. Any subsequent single-thread or deterministic-algorithm ablation must be preregistered separately.