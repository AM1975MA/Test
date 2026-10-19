# Cinque ISIN europei: scoperta justETF pubblica → prezzi yfinance, 2026-10-19

**ISIN = chiave giuridica. Yahoo ticker = quota su una specifica borsa.** Nessuna API privata o scraping automatico justETF usati: gli ISIN e ticker sono stati letti tramite il normale indice web pubblico delle pagine justETF. Ogni ticker Yahoo è verificato come possibile quotazione EUR, con controprova del registro ufficiale Deutsche Börse Xetra per *.DE, conservando le quotazioni originali e quelle aggiustate per dividendi. Quando il ticker Yahoo è diverso dalla sigla principale su justETF, utilizzare l'alias RIC esplicitamente riportato nella pagina justETF, senza mai presumere che tutti i suffissi siano disponibili su Yahoo.

| ISIN | Sottostante | justETF ETF | Quotazioni EUR da testare |
|---|---|---|---|
| LU1681042518 | **solo Europa** | Amundi MSCI Europe Value Factor UCITS ETF EUR | CV9.PA, VCEU.MI |
| LU1900066033 | **globale, ESCLUSO** | Amundi MSCI Semiconductors UCITS ETF Acc (MSCI ACWI Semiconductors) | LSMC.DE, CHIPL.MI, CHIPM.PA, CHIP.MI |
| NL0011683594 | **globale, ESCLUSO** | VanEck Developed Markets Dividend Leaders UCITS ETF | VDIV.DE, TDIV.AS, TDIV.MI, TDIV.PA, TDIV.BR |
| LU1834987973 | **solo Europa** | Amundi STOXX Europe 600 Insurance UCITS ETF Acc | LIRU.DE, LYYQ.MI, LYYQ.PA |
| IE00B5MTXJ97 | **solo Europa** | Invesco European Insurance Sector UCITS ETF Acc | SC0Y.DE, XIPS.DE |

justETF checked profile URLs:
- https://www.justetf.com/en-be/etf-profile.html?isin=LU1681042518
- https://www.justetf.com/en/etf-profile.html?isin=LU1900066033
- https://www.justetf.com/en-it/etf-profile.html?isin=NL0011683594
- https://www.justetf.com/en/etf-profile.html?isin=LU1834987973
- https://www.justetf.com/en-lu/etf-profile.html?isin=IE00B5MTXJ97

**Historical pitfalls:** justETF "inception" can describe historic economic fund lineage, NOT necessarily the first tradable trading line / current ISIN. Amundi moved ETF share classes and benchmarks in 2018/2024; never backfill 2017 without first-class lineage checks. Yahoo adjusted OHLCV is retrospective vendor-vintaged, not true PIT. Yahoo zero-volume often incomplete, not sufficient evidence of actual inability to trade. More than one quote venue per ISIN means **one fund**, not independent holdings. The issuer or index geographic investment restriction, not domicile or quote exchange, defines EUROPE-ONLY.

Results format: raw OHLC/AdjClose/Volume/events, adjusted OHLCV, ticker-to-ISIN/EUR/2017-QA, first/last dates, cross-venue same-ISIN return diagnostics and one candidate listing per ISIN. **No trading/backtesting** or changes to old EUR60/Test production.
