# OLC53 source & validity gates

- **Primary ECB source**: https://www.ecb.europa.eu/stats/policy_and_exchange_rates/key_ecb_interest_rates/html/index.en.html
- **ECB yield curves (not tested)**: https://data.ecb.europa.eu/methodology/yield-curves
- **ECFIN BCS archive (not tested; vintages unavailable)**: https://economy-finance.ec.europa.eu/economic-forecast-and-surveys/business-and-consumer-surveys/download-business-and-consumer-survey-data/time-series_en
- **Eurostat revision policy**: https://ec.europa.eu/eurostat/cache/metadata/en/ei_bcs_esms.htm

Controls: source effective_date <= entry_date minus 7 calendar days; train label exit < entry; zero duplicated market-month events; same policy data support; OLC52 original risk-gate predictions and actions identical; OLC19 accounting baseline bitwise equal; OLC52 risk-gate native replay CAGR identical.

**Data limitations:** 2019–2026 already analyzed repeatedly, historic market data Open and stop fills not broker-verified, USA source observed mask unavailable, historical universe/delisted not PIT certified. ECFIN BCS revised series deliberately omitted. No claim of improved economic alpha.

Full source & local reports: Library folder `/ETF_Research/OLC53_Macro_20261105`.
