# EU165 economic-leadership, geographic-scope and ex-post factor attribution — 2026-10-30

**RESEARCH ONLY. No production modifications. No new ranker fit or selected hyperparameters.**

## Which universe?
The native source-trained 165 ETFs are **European-listed UCITS ETF tickers (EU165)**, not USA149 nor the original EU155 B0 dataset. The 2026-built metadata classifies **155 underlying EUROPE; 10 NON_EUROPE** (USA, Nasdaq, World Tech, etc.). EUROPE-only filter in this test is NOT automatically identical to original EU155 benchmark.

## Controlled action — same V3 scores/Top5/costs/month/MA200, change *underlying exposure eligibility*
- Full EU165 Pair25/Hybrid24 with half exposure below EXSA 200-day MA: **2019–24 CAGR 12.27%, maxDD -22.69%**.
- EU underlying only: **2019–24 CAGR 8.66%, maxDD -27.50%**.
- 2021–24: **15.67% vs 11.70%** respectively.
- 6m month-block nominal paired log difference EU only minus full 2019–24 **-3.40pp/year; CI [-6.53,-0.72]**. This is NOT a pristine inference after dozens of previous tests.
- Replay exact source NAV parity for original V3 Pair127 Top5, V3 Pair25 Top5 and V3 Pair25/MA200 to <1e-15.

## Group vs within-group diagnostic (65 complete prior-trade-Open to next-trade-Open intervals, no futures in ranking)
Relative to same-month equally weighted PIT eligible pool, V3 Pair25/Hybrid24 equal-5 selected securities (gross, NO costs or MA200):
- 2019–20: between coarse macro groups +0.20pp per interval; within group +0.02pp.
- 2021–22: +0.01pp and +0.49pp.
- 2023–24: +0.32pp and +0.81pp.
- 2019–24: **+0.18pp group; +0.46pp within; sum +0.64pp per interval**. Neither term's 6-month block-bootstrap CI excludes zero in the full period. This is NOT an exact contribution to a self-financing NAV and macro group within can include selection of distinct industries: this is NOT proven factor-neutral alpha.

V3 Pair25 selected NON_EUROPE ETF *slots* by regime: 2019–20 **6.0%**, 2021–22 **9.1%**, 2023–24 **25.2%**. For V3 Pair127 comparable percentages 5.0%, 7.3%, 8.7%. Shares of *slots*, not exact underlying risk exposures.

## Risk-matched negative controls
A self-financing geographic shadow portfolio uses V3's signal-date Europe/NON_EUROPE slot weights, but holds only EXSA.DE for European component and SXR8.DE for extra-European; exact monthly trade dates, same 0.1% per side and same EXSA MA200 exposure. Source risk-off MA200 as-of gate matched **exactly at all rebalance dates**.
- 2019–24 full V3 Pair25/MA200: **12.27% CAGR**.
- Geographic shadow EXSA/SXR8 with same weights: **9.80% CAGR**, MaxDD **-22.39%**.
- Fixed 80% EXSA + 20% SXR8 / MA200: 9.34%.
- 100% SXR8/MA200: **15.33%**.
- Incremental annual log return V3 above shadow **+2.47pp, block CI [-3.29,+8.29]pp**: not statistically established, and style clone does NOT replicate tech/semiconductor factor exposures.

Monthly ex-post HAC lag3 regression on EXSA.DE, SXR8.DE, Euro sovereign LYQ2.DE, bank ETF EXX1.DE:
- Pair25 unprotected: R² .675, annualized intercept +2.15%, HAC95% [-7.04%,+11.35%] (not significant).
- Pair25 with half MA200: R² .561, intercept +4.62%, HAC95% [-2.17%,+11.41%] (not significant).
- Pair25 minus Pair127 factor-adjusted annual log difference: +0.96pp, HAC95% [-8.37,+10.30], p .84.
Ex-post regressions are not OOS strategy tests; omitted risk factors, collinearity and shared benchmark exposures limit interpretation.

## Quality and limitations
- Verified 165 source OHLCV histories, **65 complete ex-post trade-to-trade attribution intervals** for each V3 arm; exact additive decomposition error <1.4e-17; zero selected ETFs outside preceding as-of PIT basket union, zero selected missing future Open at endpoint in attributed periods.
- Vendor series and 2026-curated survivorship; no certified historical total-return/dividend, true spread/slippage, ETF delisting or fully historical underlying classification.
- 2018–26 already researched extensively, nominal CIs do not account for all prior selection; cannot declare alpha or promote deployment.

Complete replay package with code, original-source SHA checks, 27 files of pre-2025 diagnostics, monthly factor regressions, scope ablation, shadow NAV, portfolio trade ledger and figures: `ETF_TRADER_EU165_ATTRIBUZIONE_LEADERSHIP_GEO_20261030.zip`; **SHA256 ed99457ded1a19bdaad033615a7c474e6c28c19e7dc5b8b37929e8d24cc43b23**. Prior 165 input source dataset and prior large frozen score archive are NOT duplicated in this small new ZIP.

**Decision:** retain global V3 as research benchmark, but do not conflate EU-listed funds with European underlying exposure; require genuine PIT fine-grained industry/factor taxonomy and factor-matched tradeable benchmark before concluding new ranking alpha. Production unchanged.
