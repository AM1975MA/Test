# EU165 + GLOBAL UCITS — six-cluster rebalance research dataset (2026-10-28)

Research-only new dataset. **B0, USA149 and EU155 frozen original archives are not modified.**

## Dataset delivered
- 155 original verified-ISIN European-market ETFs plus 10 archived global UCITS ETF series, **165 distinct ISIN**; commodity ETC **4GLD.DE excluded**.
- 527,846 price bars until common cutoff **2026-07-01**, 527,841 usable; 1,660 small OHLC High/Low envelope adjustments derived deterministically, 5 unusable bars quarantined, 2 close-to-close jumps >30% left flagged for verification.
- 142 of 155 old raw files match the catalog's expected SHA256; six alternate-venue series use different files from archived expected digest and seven new country funds have no expected catalog digest. Both groups remain provenance-audit items.
- Original 101 historical month-end signal dates (2018-01-31 to 2026-05-29), point-in-time 252-bar/63-day liquidity screen: >=57 positive-volume days and median EUR turnover >=EUR50,000; no future prices or fabricated volume.
- Equal-count six-cluster cohort per month, with decorrelation from trailing 126 daily returns and EU/global inclusion when possible; 4-7 funds per cluster (24-42 total) across 101 signals. Snapshot 2026-07-01: **5 per cluster / 30 total**, 23 Europe-underlying + 7 non-European UCITS. Equal 1/6 cluster references express coverage, **not an investment recommendation**.

## Critical limitations
Global ETF OHLCV sources stop 2026-07-01, making the new panel stale relative to October 2026. Global REIT and global sovereign government-only ETFs still lack certified price series: property is the bottleneck (only five LIQ50 eligible at latest common cutoff); broadening bond aggregate products like VAGF is NOT equivalent to euro sovereign debt. Dividend total-return and venue spreads are not independently certified; ETF cohort selected in 2026 carries survivorship bias, and the period has already been mined. Not live-ready or virgin OOS.

## Reproduction and full artifacts
Full source archives, 165 individual raw CSVs, 528k price rows (both vendor-original and High/Low-normalized), as-of membership, 101 monthly basket records, audits, full Python builder, automated tests, and an Excel summary are delivered in the conversation attachment `ETF_UCITS_6_CLUSTER_CORRECTED_20261028.zip` (SHA256 `94f0b13782d0df0fba0199180093f196861357bc1ee161a308b3b34307ffca43`).

Inputs (original frozen user Library archives):
- `EU148_EU155_YAHOO_ISIN_QUALITY_AND_48_RETTEST_20261027.zip`, input SHA256 `8c0028d66fd66b8b5c73438980aac759c6e2b4b37729276db2adfd23b77138a8`.
- `EU_GLOBAL_UCITS_BREAKTHROUGH_20261026.zip`, input SHA256 `b25ca11da38b8ceb06e4b52c9d04d8be97d99d0de824636cc72818f936d57f52`.

**This GitHub branch contains the summary and frozen provenance; the full dataset ZIP is attached to the conversation, not pushed into GitHub.**
