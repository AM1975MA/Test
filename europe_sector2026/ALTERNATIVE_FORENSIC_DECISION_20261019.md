# Europe sector ETF alternative forensic — verified yfinance acquisition, 2026-10-19

## Source status
GitHub Actions both successful: 21 independent Amundi/Xtrackers candidates run **39301818369**, 8 alias/venue check run **39302147115**. All the raw Yahoo market price archives, dividend-adjusted prices, listing/currency metadata, and quality audit rows are saved at europe_sector2026/alternatives/results and europe_sector2026/aliases/results. Original sector30 Action 39300948098 completed and original 30 archive preserved on this branch. No production or trained-model edits.

21 independent ETF candidates: 12 Amundi STOXX Europe 600, 9 Xtrackers Europe sector/REIT. Direct yfinance 16/21 EUR, five unresolved Yahoo names; **4 of those 5 rescued by verified Xetra Yahoo aliases DXSK.DE, DXSE.DE, DXSL.DE, DXSC.DE**, despite vendor exchange short names historically XS3R, XSDR, XSNR, XSPR. XSKR communications from Xetra and Stuttgart remains missing in yfinance; this is NOT evidence the security is delisted (issuer DWS has a 2026 factsheet). Thus **20/21 independent funds have EUR Yahoo market histories**.

**2017–July 2026 historical eligibility:** 8 Xtrackers independent 2026-survivor tickers with full prior-to-2017 252 day warmup and quotes through 2026-07:
| EUR Xetra Yahoo ticker | Europe sector | Yahoo zero volume bars / study observed bars | rounded zero volume | 2017–26 |
|---|---|---:|---:|---|
| XS7R.DE | Financials | 50 / 2389 | 2.09% | yes |
| XS8R.DE | Information Technology | 78 / 2389 | 3.26% | yes |
| DXSK.DE | Consumer Staples | 69 / 2389 | 2.89% | yes |
| DXSE.DE | Health Care | 40 / 2389 | 1.67% | yes |
| DXSL.DE | Industrials | 399 / 2389 | 16.70% | yes, sparse Yahoo volume |
| DXSC.DE | Materials | 195 / 2389 | 8.16% | yes |
| XS6R.DE | Utilities | 483 / 2389 | 20.22% | yes, sparse Yahoo volume |
| XREA.DE | European property ex UK | 105 / 2377 | 4.42% | yes, very small underlying ETF fund |

The last four recovered from alias run, NOT counted as separate funds. Actual yfinance USD/EUR quotation metadata all EUR on these eight, from 2008-01-02 (XREA from 2014-09-25) through 2026-10-19.
**Strict caution:** some Xtrackers MSCI Europe sector funds changed index screens and names during 2021 / early 2025; preserve point-in-time benchmark if comparing returns/features. Their sector coverage is not guaranteed exactly equal to the older STOXX supersectors or newer GICS sector ETFs.

**12 Amundi funds:** Yahoo available EUR 12/12 but first observations **March–June 2024**, so NONE usable for 2017–23 backtests. Relevant recent-sample alternatives:
LHTC.DE Healthcare (1/552 study-day Yahoo zeros, 0.18%);
LTUG.DE Technology (4/552, 0.72%);
LOGS.DE Energy Screened (6/552, 1.09%);
LBRE.DE Basic Resources (5/552, 0.91%);
LBNK.DE Banks (16/574, 2.79%);
LTVL.DE Consumer Discretionary (14/512, 2.73%);
LFOD.DE Staples (17/512, 3.32%);
LIRU.DE Insurance (24/574, 4.18%);
LUTI.DE Utilities (40/552, 7.25%);
LTCM.DE Telecommunications (64/552, 11.59%);
LIGS.DE Industrials (64/512, 12.5%);
LCHM.DE Basic Materials (119/512, 23.24%).
**These are fund-share or listing launches in 2024, even if fund lineage or parent trust dates further back. Do not backfill fund prices with unverified predecessor index prices.**

**A key improvement vs weak SPDR reference**: original SPDR Xetra 2017–26 Yahoo zero volume approximately SPYT.DE communications 48.13%; SPYQ.DE Industrials 30.58%; SPYK.DE Tech 20.62%; SPYP.DE Materials 31.58%; SPYU.DE Utilities 26.98%; SPYH.DE Health Care 18.4%. Xtrackers DXSE (Health 1.67%), XS8R (Tech 3.26%), DXSC (Materials 8.16%) show noticeably fewer zeros, and DXSL (Industrials 16.7%) improves SPYQ but remains poor. The original iShares STOXX 600 same-sector Xetra alternatives frequently have **~0.25–0.42%** vendor-zero-volume rates and remain the stronger historical Yahoo data source.

**Same ISIN other venue control (not new independent funds)**: Milan alternate historical Yahoo EUR quotes:
STTX.MI (SPYT.DE same underlying Communications ISIN IE00BKWQ0N82): 991/2293 =43.22% zeros; SPYT.DE 48.13%.
STQX.MI (SPYQ.DE Industrials ISIN IE00BKWQ0J47): 585/2288=25.57%; SPYQ.DE 30.58%.
STWX.MI (SPYH.DE Health ISIN IE00BKWQ0H23): 224/2351=9.53%; SPYH.DE approx 18.43%.
Changing trade venue helped data completeness in these instances, but remains insufficient to establish reliable executable next-Open prices; do not double-count multiple listings of same ISIN as different investments. Yahoo zero volume may mean provider missing reported activity. No actual bid/ask depth verified.

## Implication for EUR ETF architecture
For the original 2017–26 forensic, priority is **clean iShares STOXX Europe 600 supersector lines plus selective Xtrackers**, accounting for different STOXX vs MSCI sector taxonomy and 2021/25 ESG benchmark history. Add Amundi ONLY for a new 2024+ analysis or genuinely forward validation. Use explicitly dated rules and original source raw bars; never fill historical 2017 sector holes from modern restructured share classes. Sector ETF assets do not replicate six original149 macro groups (EM, US, duration, credit, commodities) — making a sector-only European universe is a different experiment and still cannot establish original US-model portability.

## Evidence and no-run constraints
- 30 original ETF quotes: europe_sector2026/results/*
- 21 new competitors: europe_sector2026/alternatives/results/*, run 39301818369
- 8 exchange-alias controls: europe_sector2026/aliases/results/*, run 39302147115
- New ticker catalog and raw/adjusted histories with SHA256.
- No F3/H1, R_H, ETF Trader retraining or ETF portfolio test was run for this retrieval task.
- Yfinance available quote history reflects 2026 Yahoo revisions, not historical as-of vendor snapshots; survivorship and inactive ETF exclusions unresolved; ISIN and fund lineage across historical share-class changes must be validated before production.

Issuer / benchmark official evidence: Amundi 2026 provider listings and DWS Xtrackers April 2026 factsheets. Yahoo chart data independently retrieved in GitHub Actions.
