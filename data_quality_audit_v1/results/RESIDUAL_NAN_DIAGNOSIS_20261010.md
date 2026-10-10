# Compact21 remaining missing-input diagnostic — confirmed 2026-10-10

## Data-only completed
GitHub Actions [38083355019](https://github.com/AM1975MA/Test/actions/runs/38083355019) SUCCESS, original immutable independently cleaned-downvol 3 frozen Original149 vintage feature panels (original source prep run 37936573578), 125 Compact21 features, all 40230 ticker-date rows/vintage.

Each vintage:
- 34876 rows have at least 30 valid features (current XGB eligibility).
- 31827 rows have ALL 125 valid features.
- 3049 rows current gate admits while missing at least one feature.
- These 3049 rows contain 51814 missing feature cell values (not independent causes).
- All three vintages share exactly the same 3049 incomplete-row mask: pairwise mismatches 0.

Top missing columns **within only the 3049 currently eligible incomplete rows**, per vintage:
- mom252 1634; mom252_ex21 1634; mom252_pct 1634; mom252_dev 1634; mom252_ex21_pct 1634; mom252_ex21_dev 1634.
- breakout_pos252 1572; breakout_pos252_pct 1572.
- drawdown21_dev 1411.
- ma_gap200 1228; ma_gap200_pct 1228.
- drawdown126_dev 844; mom126 740; beta_mkt126 740.
These counts are dependent aliases/derivatives and NOT independent market source defects.

Stored artifact includes ELIGIBLE_INCOMPLETE_BY_FEATURE.csv, ELIGIBLE_INCOMPLETE_BY_YEAR.csv, ELIGIBLE_INCOMPLETE_BY_TICKER.csv, ROW_MISSINGNESS.csv, RESULT.json.

## Root-cause classification status
This run identifies exact affected dates/tickers and mathematical feature families, but DOES NOT yet prove all missingness is due to insufficient trading history. A 252-bar lookback has a genuine cold-start undefined period. Some robust `_dev` features can be undefined when cross-sectional MAD=0 or local distribution degenerate; investigate separately. Other technical sources include unavailable close on calendar and division by zero. No blanket fillna and no production gate adoption before those causal categories are validated against raw per-ticker OHLC.

Identical missing masks across repeats are evidence against stochastic availability changes, **not proof that values are correct**. Model stability and economics have NOT been re-tested or improved by this census.

## Next implementation gate
Audit each of the 3049 eligible-but-incomplete row causes using its own frozen raw close history, explicit 252/200/126/63/21 windows and the original cross-sectional ranks/robust deviation denominators, grouped by first live instrument dates. Classify feature NA as (1) genuine cold start, (2) unusable raw price gap, (3) structural undefined/constant MAD, (4) formula defect, or (5) unexplained; retain full ticker-date-level evidence. Correct only (4) with financial mathematical proof; no future data, no synthetic backfill and no optimizing based on CAGR. Only after this review can we decide to make all-125 complete-case gating mandatory.

Production Etf_trader repository unchanged.
