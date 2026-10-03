# YFINANCE_REPEATABILITY_V1

Date: 2026-10-03
Parent line: `ETF_TRADER_149_VS_EU120_GAP_ANALYSIS_V1`
Status: **PREREGISTERED BEFORE NEW DOWNLOADS**

## Question

Does Yahoo/yfinance return materially different historical Original149 data across repeated acquisitions made close together under one identical contract?

This is a data-lineage diagnostic only. It does not fit, tune, select, or promote any trading model.

## Frozen contract

- universe: `evidence_v1/data/original149/universe.csv` (149 unique tickers);
- provider: Yahoo Finance via `yfinance`;
- `yfinance==0.2.66`;
- `pandas==2.2.3`;
- start: `2004-01-01`;
- end exclusive: `2026-08-01`;
- `auto_adjust=False`, `actions=False`, `threads=False`;
- adjusted OHLC: same-row `Adj Close / raw Close` factor applied to raw OHLC;
- Volume: raw Yahoo Volume;
- CSV precision: `%.17g`;
- exactly three sequential acquisitions in one CI job.

## Frozen diagnostics

For each of the three pairwise comparisons (`1-2`, `1-3`, `2-3`) save:

1. number of ticker CSV files with different SHA256;
2. number of tickers with row/date-set differences;
3. number of tickers with any Volume difference;
4. maximum absolute relative OHLC-level difference on matched dates;
5. maximum absolute difference in close-to-close daily returns;
6. per-ticker maximum OHLC relative difference and return difference;
7. whether each changed ticker is compatible with an approximately constant multiplicative OHLC rescaling.

## Interpretation rule

- If repeated acquisitions are numerically identical or differ only by near-constant OHLC rescaling with negligible return deltas, reject the hypothesis of random download-to-download instability as an explanation of the 43.146% vs 31.604% CAGR gap.
- If material return/date/volume differences appear across immediate repeats, classify Yahoo acquisition instability as a live candidate cause and quantify it before any model comparison.

No threshold will be tuned after observing the result. Raw acquisitions are artifacts; compact diagnostics are persisted in the repository.
