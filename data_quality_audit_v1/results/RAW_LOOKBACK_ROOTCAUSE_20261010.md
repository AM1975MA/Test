# Verified raw-window diagnosis — 2026-10-10

Run [38083480515](https://github.com/AM1975MA/Test/actions/runs/38083480515) **SUCCESS**, original Original149 3 frozen independent raw Yahoo acquisitions + independent downvol-cleaned Compact21 panels.

Among the currently 30/125-eligible rows, missing inputs cross-referenced with raw ticker-date price history:
- mom252: 1634 missing/vintage, **1634 insufficient historical observations**, 0 raw-gap and 0 unexplained with history.
- mom252_ex21: 1634 missing/vintage, **1634 insufficient historical observations**, 0 raw-gap and 0 unexplained.
- breakout_pos252: 1572 missing/vintage, **1572 insufficient historical observations**, 0 raw-gap and 0 unexplained.
- ma_gap200: 1228 missing/vintage, **1228 insufficient historical observations**, 0 raw-gap and 0 unexplained.
- mom126: 740 missing/vintage, **740 insufficient historical observations**, 0 raw-gap and 0 unexplained.

Repeat2/3 match exactly all counts. These were compared against each ETF's own raw chronological session index; no future prices used. Some lookbacks are inclusive differently (e.g. moving average 200 needs 200 bars, whereas 200-lag momentum needs 201), but no anomalies arise under the checked bins.

**Decision**: these cases are genuine cold-start absence rather than corrupt downloaded OHLC bars or faulty finite-history formula. Do not backfill, interpolate or zero-impute. Preserve an explicit `INSUFFICIENT_HISTORY` availability cause; eventual inference contract may exclude until the required history is present, after measuring universe/portfolio survivorship effects.

The rest of missingness (**including drawdown21_dev 1411/vintage, drawdown126_dev 844/vintage and other robust _dev transforms**) is *not yet root-cause certified*. The code `cs_robust_dev` converts zero cross-sectional MAD to NaN; require exact source-date-level diagnosis and verify stable treatment is mathematically meaningful before considering any repair.

Earlier descriptive residual census [38083355019](https://github.com/AM1975MA/Test/actions/runs/38083355019): 3049 otherwise-eligible incomplete ticker-date rows and 51814 missing feature cells per vintage, same incomplete-row mask in all 3; these are overlapping feature aliases and may overlap multiple causes. No model fit, no new CAGR. Production unchanged.
