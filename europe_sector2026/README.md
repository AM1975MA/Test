# European equity sector UCITS quotes — direct vendor source archive

Purpose: user specifically requested downloading European sector-equivalent ETFs. Data procurement only, not portfolio optimization or fresh forensic conclusions.

## Frozen issuer catalog (30 candidate Xetra/EUR listings)
19 iShares STOXX Europe 600 supersector funds: EXV1 through EXV9, EXH1 through EXH9 and EXI5 (including EXV5.DE automobiles, absent from the older Europe EUR60 roster); 11 SPDR funds: SPYT, SPYR, SPYC, SPYN, SPYZ, SPYH, SPYQ, SPYP, SPYK, SPYU, ZPRP. All Yahoo tickers here use .DE (German Xetra listing) and are required to be EUR-denominated at issuer source. The official iShares and SPDR issuer catalogs identify the name and underlying geography; Yahoo venue/currency/history metadata are independently recorded.

IMPORTANT: STOXX Europe 600 supersectors follow Industry Classification Benchmark, not exactly 11 GICS industry sectors. SPDR MSCI Europe sector products align more closely with broad 11-sector labels. The sector_11 column is an approximation; EXH7 Personal and Household Goods explicitly remains CONSUMER_MIXED. ZPRP is Europe real estate ex UK, not total pan-European property.

Original Europe EUR60 already contains 17 of the iShares supersectors plus iShares EXI5 real estate and SPDR ZPRP. This batch adds potentially 11 newly listed sector ticker lines (EXV5 plus 10 SPDR sector funds). Real coverage and additions depend on Yahoo responses.

## Source processing and bias
Use pinned yfinance to fetch each ticker 2004-01-01 through 2026-10-19 inclusive. Keep raw OHLC, Adj Close, Volume, Dividends and Stock Splits as original quote rows. Separately produce same-row dividend/split Yahoo-adjusted OHLC for apples-to-apples datasets. Do not backfill missing trading days, never fabricate High/Low envelopes, do not truncate >25% returns or remove zero-volume days silently, preserve anomalous vendor rows with flags in audit. Mark non-EUR Yahoo currency and API failures without substituting other instruments. Store hashes and snapshot retrieval date.

These are present-day historic quotes and the roster consists of 2026 surviving funds, NOT point-in-time membership or historically vendor-vintaged prices. Historic tickers may have stale opens, very low volume, or repeated same-fund ISIN (multiple venues). This data-only import is not a trade-ready universe.

Original data/eu120, trained European models, portfolios and production etf_trader all remain unchanged.

Verified official issuer sources:
iShares: https://www.ishares.com/it/investitori-professionali/it/prodotti/etf-investments
State Street current fund directory: https://www.ssga.com/it/en_gb/intermediary/fund-finder
State Street sector listings: https://www.ssga.com/it/en_gb/intermediary/library-content/products/fund-docs/etfs/emea/spdr-product-list-short-italy.pdf
Yahoo data vendor: https://finance.yahoo.com/
