# EU148 root-cause: universe opportunity + parsimonious signed-excess Ridge — 2026-10-26

**Study completed** in research branch; production untouched. Dates: 101 monthly signals 2018-01-31–2026-05-29; positions first next available Xetra open 2018-02-01, terminal daily mark 2026-07-01; all EUR; cost 10bp per traded side; no future eligibility or next-open fallback. Retrospective present-day roster selection is NOT independent untouched out-of-sample.

## Main discovery

Original EU148 was **Europe underlying exposures only**: 45 European sectors, 25 European country, 22 factor, 20 broad, 25 sovereign EUR, 11 real estate. It lacked investable global/US/EM/technology Xetra UCITS. Original US149 had all those exposures. Directly comparing CAGR and IC on those two different opportunity sets conflates ability to forecast with opportunity to earn returns.

Added **10 Xetra-traded EUR UCITS ETFs** from the actual issuer/ISIN mappings: SXR8.DE (IE00B5BMR087, S&P 500), SXRV.DE (IE00B53SZB19 Nasdaq-100), EUNL.DE (IE00B4L5Y983 MSCI World), IUSQ.DE (IE00B6R52259 ACWI), IS3N.DE (IE00BKM4GZ66 emerging), QDVE.DE (IE00B3WJKG14 S&P IT), XDWT.DE (IE00BM67HT60 world IT), VWCE.DE (IE00BK5BQT80 world), IUSN.DE (IE00BF4RFH31 small world), VVSM.DE (IE00BMC38736 semiconductors). 4GLD.DE (DE000A0S9GB0) is separately reported **ETC, not UCITS** and NOT included in winning UCITS-only test. Each ticker first becomes eligible after 252 prior common closes and historic 63-session pre-signal traded-volume + EUR turnover filter. Never backfilled dates before inception.

## First predeclared fixed strategy, before rerunning ML

[GitHub Actions run 40415451722](https://github.com/AM1975MA/Test/actions/runs/40415451722): **success**, 11/11 new Xetra prices obtained from Yahoo Finance as actually downloaded 2026-10-26, time series archived with ISIN/ticker/start-date/zero volume provenance, alongside manifest, 101-month EUR daily NAV, trades, original EU148 same engine. [Predeclared reproducible Python source](ucits_global_opportunity_predeclared_20261026.py) and [workflow](../../../.github/workflows/v3-eu-global-ucits-opportunity.yml) (the workflow is actually at repository root; resolve there).

Same 252 past valid close prerequisite, past 63 sessions >=90% vendor-reported positive volume, median daily Close*Volume >=EUR50,000, no use of execution day volume as pre-signal information, 10bps notional one way, next actual Open. Simple 12–1-month momentum (252 days excluding latest 21) top3, **NO ML**:

| Universe | CAGR net EUR | Max drawdown |
|---|---:|---:|
| Europe-only original EU148 | **+5.31%** | -39.28% |
| Xetra 10 global UCITS only | **+17.90%** | -31.26% |
| Xetra 10 global UCITS + gold ETC | +19.01% | -31.26% |
| EU148 + 10 UCITS global | +9.26% | -36.41% |

The two other predefined simple controls show global UCITS only Top3 +18.35% (63d momentum) and +18.36% (risk-mix momentum); avoid selecting an ex-post winner because all historical OOS periods already mined.

## Chronological retrained signed-return Ridge in research container (full sources+outputs attached to conversation ZIP)

15 price/volatility/volume features plus cross-sectional pct feature (16 total), same **universe-relative** portfolio policy and same observed price source/market calendar. **Fixed Ridge alpha 250, StandardScaler/median-impute, pre-2018+ annual training 2018–26, 21-common-session open-to-open forward return minus EXSA forward return**, weights equal per training signal month, strict label exit before Jan1 yearly vintage, no test-label screening. This experiment simultaneously changes features, target and eligibility compared to earlier 125F LM; do not attribute skill gains to one change. Roster all present-day known survivors; no true untouched future holdout.

| EU EUR market universe | Mean Spearman monthly IC | Top3 CAGR net | Top3 MaxDD | Top5 CAGR |
|---|---:|---:|---:|---:|
| EU148 only, retrained new 16F Ridge | +0.08536 | +6.56% | -29.69% | +6.88% |
| Xetra 10 UCITS, same Ridge | +0.06202 | **+20.33%** | -35.23% | +18.00% |
| Xetra 10 UCITS + separate gold ETC | +0.03009 | +17.16% | -35.51% | +16.71% |
| EU148+10 global UCITS, same Ridge | +0.09876 | +9.02% | -30.43% | +12.77% |

**Decisive interpretation**: mean IC of EU148 new Ridge **+0.0854**, which exceeds the old US149 original Ridge +0.0795 on the earlier incomparable study — so European instrument predictions can contain directional signal. But CAGR on Europe-only economic opportunities remains far lower. Global UCITS on Xetra +20.33% reflects opportunity set PLUS model, not just alpha.

In global UCITS Top3, selected 101 months (303 ETF-month slots), XDWT world IT **70**, QDVE US IT **57**, VVSM semiconductors **47**, SXRV Nasdaq **32**, IUSN small world 34, IS3N emerging 24, IUSQ ACWI 21, SXR8 S&P500 10, EUNL World 4, VWCE World 4. Approximately 68% positions tech/Nasdaq/semiconductor: **technology concentration substantial**, not factor-matched to EU148 or SPY/EUNL.

Native same-currency Xetra passive **SXRV Nasdaq100 ~+20.7% CAGR**, MaxDD -31.2% (no trade fees besides initial), versus Ridge UCITS +20.33%, -35.23% — hence **NO proof of alpha vs strong passive Nasdaq benchmark**. Relative to passive global EUNL +12.59%, index growth is less but different beta/exposure.

Within sample 2018–2021 vs 2022–mid-2026, descriptive annualized CAGR:
- Ridge Xetra-only: **+23.0% / +18.0%**
- Ridge EU148-only: +5.6% / +7.4%.
- Classic momentum Xetra-only: +25.1% / +11.9%.

Paired circular 6-month 20k bootstrap on same 101 monthly NAV log returns (not adjusted for hypothesis selection):
- Ridge Xetra − Ridge EU148: **+13.72 CAGR pp**, nominal 95% CI **[+1.90,+25.80]**.
- Ridge Xetra − momentum Xetra: **+2.45pp**, CI **[-4.70,+10.50]**. **Incremental predictive economic value over simple momentum NOT statistically proven.**

### Data integrity and execution checks

11/11 new Yahoo adjusted OHLCV files available, each price first historical quoted date recorded, 0 missing fills across all relevant 101 monthly signals. **0 zero-volume execution-day selected lines** in Ridge EU148, global UCITS, +ETC, and EU148+UCITS (Top3 and Top5). That is not a spread or book depth certification. Price envelope issues 2 SXRV 2010, 2 4GLD; SXR8/SXRV both have an apparent ~25–28% simultaneous 2010-11-01 vendor discontinuity at low/zero trade volume. This PRE-DATES 2012 training and 2018–26 testing, but warrants separate vendor verification. In tested 2018–26 windows no >20% new global UCITS daily jump evident. Newly downloaded total-return-adjusted historical OHLC prices versus original EU raw prices are **not proven corporate-action-identically adjusted** without independent vendor reconciliation. The vintage-based screening and 2026 ISIN selection impose **survivorship bias**. No claims of certified real executions, calibrated risk or prospectively independent predictive success.

### Correct architecture to pursue

1. Separate **EU venue/investment currency** from **underlying geographic region** and expand a genuinely comparable, complete UCITS universe: US, world, emerging, sector tech, defensive fixed-income and commodity ETC only if permitted.
2. Create region/asset liquidity and vintage filters, **strict as-of** per ETF before training and trading; get independent exchange issuer EOD/corporate actions and dealer spread/market-depth feeds.
3. Two-stage allocator: eligibility/asset-region budgets and within-bucket signed risk-aware forecasts. No one pooled global ranker with unresolved target-mix conflict.
4. Benchmark on the **same risk and underlyings** and never declare regression alpha based on higher raw CAGR alone. Include Nasdaq passive, World passive, original EU148, simple 12–1 momentum, sector/beta matched, liquidity + costs.
5. Freeze features, universe vintage and model before new prospective paper trading. Existing 2018–26 repeated hypothesis exploration lacks a truly blind holdout.

Source files in conversation deliverable EU_GLOBAL_UCITS_BREAKTHROUGH_20261026.zip include both complete Python scripts, downloaded new 11 ETF adjusted OHLCV rows, as-of signal and annual 9x4 fit audit, original-148 comparators, exact daily NAV and trades, scorecards, source logs, 20k paired bootstrap, Xetra execution-volume audit, data-quality screen.
