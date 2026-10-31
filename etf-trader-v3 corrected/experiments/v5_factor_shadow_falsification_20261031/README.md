# ETF Trader V5 — factor shadow falsification on EU165, 31 Oct 2026

**Research-only. Original V5/V2/V3 production and main branch unchanged.**

## Design

Original source-native V5 hierarchical EU165 GBM Top5 ETF selections from frozen annual training, **same monthly execution dates, same 10bps one-way fees**, and exactly the same source MA200 50%/100% exposure schedule. Six first-stage shadow portfolios use no future prices:
- GEO: conditional on V5 current selected holdings' Europe/US/bond classifications, invest in EXSA/SXR8/LYQ2.
- TRACK4: conditional on V5 selections, estimate 126-day *past-only* nonnegative regression/tracking clone using EXSA/SXR8/EXX1/LYQ2; weights sum to 1.
- TRACK9: same on 9 benchmark ETFs including US technology, Nasdaq, world technology and semiconductors. **Contains same tickers selected by V5** and is not an independent control.
- STYLE: conditional on V5 economic classifications, map slots to preselected sector proxies; in 2023 **4.92 out of five slots were the exact same ETF as V5**. Near-identical CAGR is a mechanically overlapping attribution, NOT independent alpha refutation.
- STATIC_US: SXR8-only market portfolio with same V5 exposure MA200.
- STATIC_TECH: static SXR8/SXRV/QDVE/XDWT 25% each, with same V5 exposure MA200. **Proxy set chosen retrospectively after seeing V5 2023 tech leadership**; not a clean pre-2021 universe.
 
Separately execute six **independent-from-V5-ticker-selection** proxy portfolios: 4-factor and 9-factor equalweight, 4-factor Momentum252 Top2, 9-factor Momentum252/126/63 Top3. These use same months and EXSA MA200 trigger but **never consume monthly V5 ticker decisions or V2/V3 rankings**. The nine-proxy universe itself was assembled post-hoc and remains hypothesis-mined.

## Recomputed 2021–24 self-financing results

| policy | CAGR | MaxDD | Sharpe |
|---|---:|---:|---:|
| **Original V5 expert GBM** | **22.03%** | −20.73% | 1.350 |
| Factor TRACK4 (conditional on V5 positions) | 17.99% | **−9.67%** | 1.683 |
| Conditional geography EXSA/SXR8/LYQ2 | 15.84% | −12.11% | 1.256 |
| Conditional TRACK9 (often same ETFs) | 20.34% | −17.10% | 1.311 |
| Conditional STYLE (often exact same ETFs) | 22.00% | −18.56% | 1.273 |
| SXR8 static holdings, same MA200 | 17.09% | −14.73% | 1.269 |
| Tech basket static, same MA200 | 20.08% | −22.67% | 1.128 |
| INDEPENDENT four factors equal | 12.72% | −10.64% | 1.248 |
| INDEPENDENT four factors MOM252 Top2 | 14.73% | −17.22% | 1.006 |
| INDEPENDENT nine factors equal | 16.12% | −17.90% | 1.084 |
| INDEPENDENT nine factors MOM252 Top3 | 11.01% | −24.42% | 0.589 |
| INDEPENDENT nine factors MOM126 Top3 | 15.97% | −22.23% | 0.855 |
| INDEPENDENT nine factors MOM63 Top3 | 14.26% | −26.23% | 0.771 |
| Original V5 WITHOUT V2/V3 ranking feature ablation | 22.06% | −20.82% | 1.357 |

**Monthly 6-month circular block bootstrap** 47 paired monthly returns: V5 minus factor TRACK4 annualized log return +3.42pp, nominal 95% CI [−4.96,+12.34]; V5 minus GEO +5.30pp [−3.58,+14.63]; V5 minus STYLE +0.02pp [−5.02,+5.21]; V5 minus independent nine equal +5.05pp [−3.64,+13.24]. ALL include zero. The V5 factor-timing decision may add value, but there is **no verified stable ETF-level alpha** in this mined period.

**2021–22 / 2023–24 CAGR:** V5 +1.44%/+43.96%; TRACK4 +9.30%/+25.80%; STYLE +1.90%/+43.3%; 4-factor MOM252 +9.00%/+20.10%. **2025**: V5 +20.02% vs 4-factor MOM252 Top2 +38.44%. V5 advantage highly regime-dependent.

## Audit of same-day execution Close

The frozen engine used `np.isfinite(c[idx[t]])` where `c` is the **execution-day forward-filled Close** to gate eligibility at the actual next Open. Although that variable is temporally invalid at order time, a replay copy replacing it with the previously known Close `mark[idx[t]]` yielded **exactly identical daily NAV across all arms (max difference 0)**. On the 89 signal events the as-of valid Open/score eligible universe did not change. This is a **source-code flaw fixed in the isolated test**, not evidence that recorded V5 22% was inflated on this sample. A portable 1-line Git patch is in the downloaded ZIP.

## Caveats / decision

- EU165 is the 2026-curated surviving ETF universe; returns based on vendor price data not certified for dividends, total returns, true transaction spreads, FX or delistings.
- Styles TRACK9 and STYLE are partially tautological because they often hold actual V5 source ETFs; both condition on V5 choices, so neither directly tests predictability of exposures.
- Benchmarks independent of source picks use a 9-proxy set chosen *after reviewing V5*, not pristine.
- 2018–26 multiple hypothesis reuse; block CI exploratory. This comparison does **not** prove absence of alpha, only failure to establish it reliably and shows concentration regime risk.
- **No portfolio promotion.** Next research gate should test factor/sector leadership forecasting with genuine historical PIT instrument taxonomy and independent future data before a full probabilistic HOLD/SWITCH optimizer.

## Executable artifact and input hash

Downloadable supplementary ZIP (scripts, all factor/nav/trade/CI CSV, reports and two charts): **`ETF_TRADER_V5_FALSIFICAZIONE_FATTORIALE_20261031.zip`**, SHA256 **`8eafeda30fb305e913ec93c3fb8603dee5cb47c4ca31096f292786c88cbd04e6`**, 21 files, ~659KB.

Requires the previously frozen original source archive `ETF_TRADER_V5_GERARCHICA_EU165_20261031.zip`, SHA256 **`333286dc00398f39ebcebec984919b3c0bdb2234024f12595d24b7997048b465`**; original 165 raw datasets not duplicated in supplement. Set `ETF_V5_ROOT` to extracted original folder before running the two scripts, then `create_report.py`.

Original source unchanged.
