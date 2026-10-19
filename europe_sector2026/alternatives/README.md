# 21 alternative European-sector UCITS — compare against existing 30 
Freeze catalog October 19, 2026 before fetching Yahoo outcomes.

12 **Amundi STOXX Europe 600** Luxembourg UCITS as 2026 EUR/Xetra sector lines: Banks, Health, Technology, Energy Screened, Utilities, Insurance, Industrials, Telecommunications, Basic Materials, Basic Resources, Consumer Discretionary, Consumer Staples. Some are legacy 2006 tracking classes, some newer classes from 2024; they DO NOT all have 2017 price-history eligibility. Amundi sector classifications (ICB) are not precisely equivalent to MSCI/GICS. Amundi Energy Screened has ESG index differences from the originally retrieved SPDR Energy.

9 **Xtrackers European** Luxembourg/Ireland UCITS EUR/Xetra candidates: Consumer Staples, Financials, Health Care, Industrials, Technology, Materials, Utilities, Communication Services and European ex UK Property. Core Xtrackers MSCI sector products often have 2007 long history. Note: Xtrackers historically renamed some index exposure to ESG-screened; exact benchmark vintage and historical sponsor details require a separate as-of factsheet check. XREA explicitly excludes UK, small fund, not equal to Europe full real estate. For three Xtrackers tickers the exact ISIN wasn't confirmed in issuer web evidence yet; record as UNKNOWN, do not assert verified 2017 availability.

All ticker candidates use Yahoo .DE Xetra history. The download workflow checks actual Yahoo currency metadata for EUR; records Yahoo quote instrument name, venue and currency, WITHOUT changing any historical series. Market data obtained directly from Yahoo yfinance and stored in raw_vendor and separately in dividend-adjusted OHLC, not repaired by OHLC envelope or historical performance/trend filter. No future cap/delist exclusions to be imposed without evidence. Major issue: source present-day 2026 survivor list is not true as-of 2017 membership. Yahoo historical Volume 0 may indicate missing volume data instead of absent execution. A less zero-volume series is a **quality indicator only, NOT proof of better bid-ask liquidity**.

Reference: earlier sector 30 source and audit europe_sector2026/results/DOWNLOAD_AUDIT.csv. Compare zero-volume share, all-OHLC-flat share, 2017–26 span per fund to PRIOR same-sector 30. Do not combine exposures or recommend an actual buy solely because ticker is present. All artifacts stored only on separate branch. No production / etf_trader modifications.

Official Amundi:
https://www.amundietf.lu/en/individual/products/equity/amundi-stoxx-europe-600-technology-ucits-etf-acc/lu1834988518
https://www.amundietf.lu/en/individual/products/equity/amundi-stoxx-europe-600-energy-screened-ucits-etf-acc/lu1834988278
https://www.amundietf.lu/en/individual/products/equity/amundi-stoxx-europe-600-basic-resources-ucits-etf-acc/lu1834983550
Xtrackers:
https://www.justetf.com/en/etf-profile.html?isin=LU0292105359
https://www.justetf.com/en/etf-profile.html?isin=LU0292100806
https://www.justetf.com/en/etf-profile.html?isin=LU0292104469
https://www.justetf.com/en/etf-profile.html?isin=IE00BP8FKB21
