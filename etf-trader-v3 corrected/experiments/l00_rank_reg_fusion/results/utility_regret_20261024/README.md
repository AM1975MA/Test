# V3 2026-10-24 — expected-regret hurdle model

Nine verified immutable experiment archives, including all original changed ETF decisions and monthly OOS outcomes; SHA256 in ARCHIVE_MANIFEST.json.

## Method

4 families (Decision Tree original features, Decision Tree as-of-price-regime, HistGradientBoosting regime, Random Forest regime), 2 fixed downside aversion coefficients (1.0 and 1.5), fixed 20-bp proxy switch cost, quarterly mature-label meta refits with 60-calendar-day lag, 101 verified 500-basket months.

Regime features use last known <= signal-date closes, 21/63-trading-day momentum, volatility, drawdown, breadth and SPY. No future price row admitted to features.

## Files

- archives/: all full original GitHub Actions results, zipped and checksum verified
- tables/: direct CSV economic and forecast competence statistics
- ARCHIVE_MANIFEST.json: source run IDs and immutable checksums
- ../../EXPECTED_REGRET_RESULTS_20261024.md: interpretation and decision

IMPORTANT: Previously researched historical 2018–2026 calendar is NOT an independent holdout; no variants have been promoted to production.
