# Europe-only ETF cleanup — active research universe (2026-10-17)

The inherited research label `EU120` was misleading. **Ticker trading location and currency do not establish underlying investment geography.** The original 120-ticker frozen snapshot remains forever in `data/eu120/` for exact replication of PRs #91–#94; do NOT delete or rewrite archived prices or retrained scores.

## Non-destructive user-requested geographical deletion
| Cohort | Tickers | Eligibility |
|---|---:|---|
| Original120 (immutable old study) | 120 | Mixed Europe, US, world, Emerging Markets, USD duration and commodities; not suitable for "Europe only" |
| **Europe-only75 geographical whitelist** | **75** | European company equity / Eurozone sovereign bonds; European UCITS/trading access; exclude US-domiciled/non-UCITS even when they track European stocks |
| **EUR trading lines of Europe-only75** | **60** | The first **retrained** common-open economic comparison (USD/GBP/CHF currency mixing not allowed) |
| Europe-only, non-EUR trading lines kept separately | 15 | Europe geography valid, but exclude from zero-FX-conversion euros-only economic replay |
| EXCLUDED from Europe-only75 | **45** | Detailed source-group-level reason in `GEOGRAPHY_AUDIT.csv` |

The 45 exclusions cover US-listed Europe-exposure funds (**IEUR**, **IEV**, **EZU**, **DAX**, **GREK**, **EUFN** etc.; geography alone not a problem, their non-UCITS legal vehicle/exchange is), global/US/EM instruments (**IQQW.DE** MSCI World, **IQQH.DE** Global Clean Energy, **SXR8.DE** S&P 500, **EUNL.DE** MSCI World, **EUNM.DE** emerging markets, **IS3N.DE** emerging markets, **IUSQ.DE** ACWI, **ZPRG.DE** global dividends, **ZPRV.DE** US small cap, **SPY5.DE** S&P500, **4GLD.DE** global gold), USD/EM government bonds (**IDTL.L**, **SEMB.L**), and euro-denominated credit funds where exclusive European *issuer* exposure is not part of the mandate (**ICOV.MI** holds Canada, **IS3M.DE/ERNE** hold Wells Fargo/Canadian banks, EUR corporate credit). Tickers with insufficient issuer-geography proof are excluded conservatively. There is **no identifiable dedicated Argentina ETF ticker** in the original120; Argentina exposure may exist within global/emerging-market portfolios, which are excluded by mandate.

**This is a conservative universe definition, not a performance-based filter.** No future return, Sharpe or CAGR was used for inclusion. Keep UK and Switzerland in the geography set; 15 excluded from EUR-only economic test because of listing/FX, not for being outside Europe. The EUR-likely listing convention `.DE, .MI, .AS, .PA, .MC` must still be verified against exchange-specific trading-currency metadata before portfolio production. Duplicate share classes/listings of a single underlying ETF may still exist and must be de-duplicated by ISIN in a later live-universe gate.

## Evidence supporting classifications (underlying benchmark, not exchange)
- iShares MSCI Europe / IQQY: https://www.ishares.com/de/privatanleger/de/produkte/251860/ishares-core-msci-europe-ucits-etf
- iShares Europe min-vol / EUN0: https://www.blackrock.com/de/privatanleger/produkt/251381/ishares-edge-msci-europe-minimum-volatility-ucits-etf
- iShares STOXX Europe 600 sector ETFs (EXV*/EXH*): https://www.ishares.com/de/professionelle-anleger/de/produkte/etf-investments
- Xtrackers European Real Estate / D5BK/XDER: https://www.justetf.com/en/etf-profile.html?isin=LU0489337690
- iShares euro sovereign / SEGA IEGA EUNH: https://www.ishares.com/uk/individual/en/products/251740/SEGA
- iShares 7–10 year euro sovereign / IBGM: https://www.ishares.com/it/investitore-privato/it/prodotti/251738/ishares-euro-government-bond-710yr-ucits-etf
- iShares global clean energy / IQQH: https://www.ishares.com/de/privatanleger/de/produkte/251911
- iShares world / IQQW: https://www.ishares.com/de/privatanleger/de/produkte/251881
- iShares EM / IS3N: https://www.ishares.com/de/professionelle-anleger/de/literature/fact-sheet/eimi-ishares-core-msci-em-imi-ucits-etf-fund-fact-sheet-en-de.pdf
- iShares S&P500 / SXR8: https://www.etfs.de/etf/sxr8-xetra/
- iShares EUR covered / ICOV contains Canadian issuers: https://www.justetf.com/en-it/etf-profile.html?isin=IE00B3B8Q275
- iShares ultra-short Euro corporate / ERNE/IS3M contains US issuers: https://www.ishares.com/de/professionelle-anleger/de/produkte/258114/ishares-euro-ultrashort-bond-ucits-etf
- SPDR dividend / ZPRG global: https://www.ssga.com/at/en_gb/institutional/etfs/state-street-spdr-sp-global-dividend-aristocrats-ucits-etf-dist-zprg-gy

## New trained study
The refit is in `europe_only75/refit.py`; for the FX-consistent first pass it **trains 60 XGBoost ranker seed models + 20 Hybrid Tail learner models anew** on just 60 eligible European ETF returns (not on the 149 ETFs or 120 mixed ones), with annual expanding as-of label maturity audit. Frozen original149 is read ONLY as market references SPY/HYG/IEF/BIL/SHV; those never enter the investable universe. Evaluates BASE, Return-NDCG, Tail Hybrid alone, BASE+Tail and Return+Tail in same European common-open execution, plus simple 50/50 diagnostic.

This is a different investable universe: it **cannot** reuse prior EU120 fitted model outputs. No production modification.

### Important limitations
- Original120 membership was chosen with the July 1 2026 price availability requirement. Filtering these historical tickers does not repair universe-level survivorship/point-in-time eligibility bias.
- Multiple ticker lines may represent identical funds and live tradability/currency must be checked before prospective research.
- Reconstructing annual predictions on original frozen 2017–2026 history is OOS by label timing but NOT genuinely independent prospective validation after repeated research.
- GitHub holds **all research source code** and frozen CSV/manifest. Actions artifacts (model binaries/equity) are retained for 90 days per workflow, not permanently committed to Git.

## Refit source compatibility gate — original MA3 A4 clustering
The original 120-ETF MA3 feature generator requires **8 source-only persistent clusters**: a defensive sleeve with at least 8 ETFs and seven dynamic clusters with at least 8 tickers each. It mathematically cannot be applied unchanged to a strict EUR60 candidate universe, which contains only seven eligible euro sovereign lines. We did **not** pad the universe with US/global ETFs or weaken the geographic filter. Instead `build_ma3_euro60.py` changes **only this source-only upstream cluster preprocessing stage** to six dynamic clusters (min7) and one EU-sovereign defensive sleeve (min7), for seven clusters total, keeping historical label cutoffs, 42 Hybrid features and learners unchanged. The wrapper checks the original upstream constants and aborts if they drift; all 120-era sources remain unmodified. This deliberate structural adjustment makes new historical results **not an exact apples-to-apples replication** of the EU120 model and must be disclosed.
