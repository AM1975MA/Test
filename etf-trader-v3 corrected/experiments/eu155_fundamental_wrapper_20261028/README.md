# EU155 non-momentum: ETF fundamental index wrappers — 2026-10-28

**STATUS: RESEARCH ONLY / REJECT AS INCREMENTAL ALPHA. Do not change production, B0 or USA149.**

## Thesis
Compare a factor-index portfolio (using ETF indices that internally select securities on valuation, small-cap value and minimum volatility, not ETF price momentum) against frozen historical B0 and a broad Europe accumulating ETF. This is NOT a stock-level ML paper replication and NOT a virgin OOS test.

101 monthly signals, 2018-02-01 to 2026-07-01, EUR, same next-open calendar, 10 bp one-way traded notional, no cash yield, original B0 NAV is read-only.

Portfolio CORE4: 25% XMEU MSCI Europe (LU0274209237), 25% CEMS Europe Value (IE00BQN1K901), 25% ZPRX Europe Small Value (IE00BSPLC298), 25% EUN0 Europe Minimum Volatility (IE00B86MWN23).
Portfolio FACTOR3: equally weighted CEMS/ZPRX/EUN0.
All four ETFs are accumulating. EU155 LIQ50 same-as-of screening; factor leg failing LIQ50 is allocated to eligible XMEU; if XMEU fails, previous portfolio allocation is frozen (2026-03-31 vendor data hole). No parameter selection based on historical CAGR.

| Portfolio | EUR CAGR | MaxDD | Annual vol | Sharpe rf0 |
|---|---:|---:|---:|---:|
| B0 frozen | 8.7936% | -35.2840% | 19.9903% | 0.5322 |
| Europe broad XMEU | 8.8352% | -34.8115% | 16.7211% | 0.6022 |
| CORE4 | 8.6005% | -35.0555% | 16.2191% | 0.6022 |
| FACTOR3 | 8.5124% | -35.1903% | 16.1837% | 0.5980 |

Annualized paired log return delta CORE4-XMEU: -0.216 pp, 95% circular 6-month block bootstrap [-1.609,+1.242] pp. Sharpe diff -0.00005, 95% block bootstrap [-0.091,+0.113]. No incremental economic evidence. ZPRX fails strict LIQ50 in 31 of 101 decision months, so it is NOT continuously held.

## Structural bottleneck — highly correlated ETFs
Correlation-matrix effective dimension (eigenvalue participation ratio) for complete-case daily-returns windows:

| Window | All fund count | Effective dimension all | Equities count | Effective dimension equities |
|---|---:|---:|---:|---:|
| 2018–19 | 123 | 3.21 | 95 | 2.21 |
| 2020–21 | 137 | 2.29 | 102 | 1.58 |
| 2022–23 | 136 | 2.29 | 103 | 1.61 |
| 2024–25 | 136 | 2.80 | 104 | 1.95 |

This is **contemporaneous covariance risk dimension**, not the number of actionable alpha signals. Highly redundant ETF wrappers make it unsafe to transplant claims from stock-level ML papers.

## Data-quality veto
Archived Yahoo OHLCV lacks a documented corporate-action/total-return provenance for dividend cash flows. At least 98/505 B0 ETF-month positions belong to three funds verified as *distributing*: EXX1 (43), EXV1 (31), EL4C (24). Need to validate historical adjusted-close mechanics and dividend reinvestment BEFORE calling any price-only CAGR an investable total return. ZPRX liquidity and 2026-03-06 missing raw quote block require a separate venue audit. The 2018–26 sample has been mined repeatedly; bootstrap intervals are nominal only.

## Next scientific experiment (requires new PIT data)
Acquire a survivorship-free stock-level European universe with timestamped fundamentals (book-to-market, profitability, net investment, earnings revisions), listed/delisted flags, liquidity, spreads, corporate actions and pricing. Replicate European evidence from Fieberg et al., OR Spectrum 45 (2023), DOI:10.1007/s00291-022-00693-w: 12,000 European shares with strong non-linear ML gains primarily outside large caps. Compare Elastic Net, small GBDT and simple equal-weight factor ranks with chronological nested OOS, size/sector-neutralization, costed long-only portfolio vs Europe broad market, then evaluate whether ETF implementability dilutes the signal. USA149 and B0 remain FROZEN controls.

Source catalog and NAV data: EU148_EU155_YAHOO_ISIN_QUALITY_AND_48_RETTEST_20261027.zip (user's existing dated source archive).
Reproducible runner, audit CSVs, bootstrap and full report are supplied as conversation artifact EU155_FUNDAMENTAL_FACTORS_AUDIT_20261028.zip.
