# Prespecified ETF Trader V2 exact-risk integration for causal predictive ADAPT4

**Freeze before V2 outcomes:** the ADAPT_4_CAUSAL online supervised-free past-only 12-month experts predictor is now fully computed using the 65 original ETF Trader V2 source months and 48 ETF ISINs. The rank-only result is +15.37% CAGR Top5 without stops, but that is NOT a V2 result. User previous requirement: preserve the original US SPY/HYG/IEF market risk reference. We must test it, with exact old EUR V2 curve parity.

## Fixed controls, no parameter search, same 1374 European common venue days
1. ORIGINAL_MA3 Top2, original EUROPE risk & EURO short-duration government defensive, standard source V2 with HighCAGR24, DD-first, V6, 5.5% stops, 10bp; must exactly equal archived +1.6362% and -37.193%.
2. ADAPT4 Top2, SAME EU controls.
3. ORIGINAL_MA3 Top2, SPY/HYG/IEF USD-original risk, EUR short-duration defensives, V2; must equal prior controlled +0.6460%/ -37.093%.
4. ADAPT4 Top2, SAME US original risk source (PRIMARY, per user original refs request). Keep BIL/SHV outside primary EU-only candidate universe.
5. EXACT same raw rank score Top2 for ORIGINAL and ADAPT4, no exposure controller, no stop, no V6 defensive alt, 10bps trading cost: isolate selection ability from controllers.
6. ORIGINAL and ADAPT4 Top2 with US original SPY/HYG/IEF risk but NO STOP, same V2 margin/weights, original euro defensives; isolate stop layer effect under authentic user macro refs.
7. No additional TopK/weights hyperparameter exploration. 48 ETF symbols remain single 48 legal ISIN choices, historical price input same archival originals and source 49 High/Low envelope corrections previously disclosed. V2 criterion still 3% margin + both original frozen ET/XGB better than second during risk off. Note: changing rank scores means V2 confidence margins inherit same numeric 0..1 rank scale but distribution of spreads differs; acknowledge this.
8. Exactly the prior source 65 signals (Jan2021–May2026) and 1374 daily marks (Feb2021–Jul2026). Strictly past US USD market close asof for risk signal; same-day US close enters next-European-day only through the original shift. BIL/SHV placement out-of-scope in this primary study since prior test found only +0.06pp impact; currency-genuine choice is EUR short sovereign.
9. Original ADAPT4 next month 65x48 scores must RECONSTRUCT original archived Top5 picks exactly, proving no post hoc selections or hidden future data. All original MA3 Top1 also reproducible and daily V2 cash account 1e-11 exact.
10. Research-only 2026 survivors and revisited historical outcome window, no pristine OOS guarantee, no production patch, no rerun fitting. If full V2 does poorly, do not claim the Top5 result transferred.
