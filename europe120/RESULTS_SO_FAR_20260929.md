# EU120 transfer test — results so far (2026-09-29)

The final P45 transfer backtest has **not** been run yet because the frozen 120-ETF European holdout universe is not complete.

Canonical raw-data semantics are unchanged from ETF Trader: Yahoo Finance via yfinance, requested start 2004-01-01, end-exclusive 2026-07-02, same-row Adj Close / raw Close adjustment for OHLC, raw Volume. The evaluation replay will remain 2017-02-01 through 2026-07-01.

The holdout is required to be disjoint from the original 149-ticker universe and selection uses no performance criterion.

Latest one-pass catalog result:

| Macro cluster | Valid disjoint European-exposure ETFs |
|---|---:|
| C01 broad/style | 22 |
| C02 sectors/themes | 20 |
| C03 countries/regions | 20 |
| C04 small/factor | 6 |
| C05 EUR bonds/cash/credit | 0 |
| C06 European real assets/infrastructure | 0 |

The zero/low counts in C04-C06 are discovery limitations of Yahoo Search, not a failure of the raw price downloader. The next step is to use explicit Yahoo tickers for known UCITS/equivalent instruments in those clusters and subject every candidate to the exact same raw-coverage check. No performance data will be used to choose replacements.

Examples already validated with the canonical raw window include IEUR, IEV, SPEU, HEU.PA, EZU, FEZ, FEP; EXV1.DE through EXV9.DE and EXH1.DE/EXH2.DE/EXH3.DE/EXH4.DE/EXH5.DE/EXH6.DE/EXH8.DE/EXH9.DE; DAX, EFNL, GREK, EDEN, EWK.MX; and for C04 IEUS, CES1.L, CSEMUS.MI, SXRJ.DE, DFE, EUDG.
