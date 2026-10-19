# Verified yfinance procurement outcome — 30 European sector UCITS in EUR
2026-10-19 | GitHub Action https://github.com/AM1975MA/Test/actions/runs/39300948098 SUCCESS.

## Successful download
- All 30 issuer-mapped Xetra/Deutsche Börse European equity sector UCITS candidate tickers downloaded from yfinance 0.2.65: **30/30 Yahoo currency EUR**, 0 errors / missing complete histories, each has >252 observations prior to 2017-02 and still reaches 2026-07-01. Earliest source history 2008-01-02, latest archived 2026-10-19. Raw_vendor preserves Yahoo unaltered adjusted Close and OHLC, dividends/splits, Volume. adj_price preserves per-row Yahoo historical AdjClose/Close-adjusted OHLC, but no synthetic repaired highs/lows. SHA256 checksums present.
- 19/30 already in previously frozen Europe-only EUR60 cohort. **11 truly incremental ticker lines**: EXV5.DE (Automobiles & Parts) and SPYT.DE (Communication Services), SPYR.DE (Consumer Discretionary), SPYC.DE (Staples), SPYN.DE (Energy), SPYZ.DE (Financials), SPYH.DE (Health Care), SPYQ.DE (Industrials), SPYP.DE (Materials), SPYK.DE (Technology), SPYU.DE (Utilities). ZPRP.DE property and the other 18 iShares names were already present.
- All **11 broad stock sectors** represented; personal/household ICB supersector EXH7.DE kept separate CONSUMER_MIXED. STOXX ICB and MSCI/GICS sector buckets are not equivalent so use exact index-based groups for future domain tests.

## Critical data quality audit (direct from DOWNLOAD_AUDIT.csv, 2017-02 to 2026-07)
- 71,508 ticker-day observations; Yahoo vendor Volume=0 on **6,272** observations, **8.77%** of total; 5,457 OHLC flat bars (open=high=low=close), 5 recorded inconsistent price envelopes, 1 daily close-to-close adjusted move >25%. Original Yahoo rows remain preserved; none filtered by realized performance.
- Particularly illiquid/stale quote candidates according to Yahoo daily Volume=0:
  * SPYT.DE (Communication Services): **1,146/2,381 48.13%**
  * SPYP.DE (Materials): **749/2,372 31.58%**
  * SPYQ.DE (Industrials): **730/2,387 30.58%**
  * SPYU.DE (Utilities): **639/2,368 26.98%**
  * SPYR.DE (Consumer Discretionary): **534/2,368 22.55%**
  * SPYK.DE (Technology): **489/2,372 20.62%**
- Yahoo zero-volume may signal low exchange trade activity OR incomplete Yahoo transaction-volume reporting, not incontrovertible proof of no real trades. Neither day-level Open in these files nor a constructed OHLC envelope is guaranteed executable. Do NOT use new ETF quotes for transaction replay without independent spread/liquidity/reference fair-value verification.
- No new model was trained or backtested. Original 60/75/120 selection and etf_trader production are unchanged. 2026 survivor-biased membership remains a serious issue for any later 2017-2026 simulation. The 30 proposed tickers include different funds tracking overlapping sector indexes; sector repetition is not diversification.

## Source files
- CATALOG.csv: issuer-linked 30 ETF candidates and mapped sectors
- results/DOWNLOAD_MANIFEST.json
- results/DOWNLOAD_AUDIT.csv
- results/raw_vendor/TICKER.csv for each EUR line
- results/adj_price/TICKER.csv for each EUR line
- results/SHA256_MANIFEST.txt

Provider identity sources: iShares 2026 sector catalog, State Street 2026 11 European sector fund list. Download source yfinance Yahoo historical quotes, not PIT vendor-vintaged archive.
