# ETF Trader EU165 — B0 / V2 / V3 / Momentum252 parallel attribution, corrected pilot

**29 Oct 2026; research-only. Do not merge to production.**

## Structural correction
The original EU165 2025 pilot matched signal `2025-12-31` against a PIT basket dated `2025-12-30` using exact equality, leaving all 500 portfolios with no Top2 selections in January 2026. The corrected version maps each signal to the most recent same-month basket as of the signal date (never a future date). Pre-2026-Jan allocations and 500-basket NAV paths of V2 and V3 reproduced to maximum numerical differences of 4.44e-16 / 6.66e-16 respectively. This supersedes previous 2025 full-year pilot CAGR numbers.

## Same dataset, architecture, cost, horizon
- Source real **2025** fits: V2 Titanium 3-seed XGBoost + Hybrid24; V3 corrected XGB Pair127 three seeds blended at 25% into V2 base; isolated layer ablations use the same trained scores, no retraining or future labels.
- Six clusters, exactly 4 ETFs per cluster in each of 500 as-of monthly baskets, 165 ETF universe, 12 monthly decisions, 255 master trading dates 2025-02-03..2026-02-02.
- Same original monthly Top2 dynamic 60%–100% top weight (after HighCAGR24), original market gross / DD-first intraday stops, 10bp one-way turnover; V6 **alternative recovery** unused in original pilot (all ALT=-1), hence disabled in all ablations.
- The strategy-specific risk/cash proxy is LYQ2.DE, **not** cash without duration risk.
- **CAGR normalization**: normalize to first pilot session NAV; 254 daily intervals, annualize by 252 periods. Never confuse with CAGR from initial capital 1 at time zero.

| Model | CAGR normalized after conservative no-quote substitute | MaxDD | bank-risky sleeve weight |
|---|---:|---:|---:|
| MOM252 on EXACT SAME EU165 Top2/risk engine | **42.23%** | -15.73% | 42.29% |
| Ported V3 Pair127 25% + V2 Hybrid24 | **18.88%** | -17.44% | 0.80% |
| Ported V2 Titanium + Hybrid24 | **16.54%** | -17.92% | 0.96% |
| V3 corrected Pair127 isolated | 22.25% | -15.31% | 6.80% |
| V2 Titanium alone | 14.43% | -16.56% | 9.79% |
| MA3 Tail alone | 11.00% | -20.51% | 0.095% |

Banks (5 names EXX1.DE/EXV1.DE/SC0U.DE/S7XE.DE/LBNK.DE) are present in 46.12% of the 500×12 eligible PIT baskets. Conditional on a basket containing >=1 bank ETF, the model selects a bank: 100% MOM252, 34.2% Titanium, 22.1% Pair127 pure, 5.1% V2 full, 4.2% V3 full, 1.1% Tail pure. Therefore the 52.5% Tail weighting suppresses a sector signal that other rankers see **during the exceptional 2025 bank rally**; no assertion Tail is ineffective in bear markets.

The 200-session EXSA.DE benchmark MA risk cap at 50% is inactive at all 2025 month-end signal dates. Separate daily version active on 11 sessions and reduces sample annualized CAGR in all three strategies with almost no drawdown reduction. Do not infer 2022 applicability from 2025.

No raw Open available for SXRY.DE at 2026-01-02 in just 1–2 baskets/500: separate conservative fallback to LYQ2 for those baskets has <0.01 percentage point CAGR impact. Details in `RAW_OPEN_TRADE_ENTRY_DETAIL.csv`.

**Critical limitations:** 2025 is historically mined and not an untouched test; nominal bootstraps over 12 calendar months do not compensate for multiple testing; 500 baskets heavily overlap, not 500 independent returns; 2026-survivor fund sample; vendor historical distributions and total returns not certified; market beta and spreads unverified. Full EU165 native 2018–26 V2/V3 remains NOT RUN. Do not promote anything until bearish 2020/2022 and other yearly native fits, PIT issuer histories and dividends are audited.

## Complete artifacts
- Conversation downloadable `B0_V2_V3_PARALLEL_RANKER_AND_RISK_20261029.zip`, SHA256 **0185fa29efeb9f1b4ae9cbd4ad61f594b68f6ff3aee056f30bddf50aa9e85b12** — full executable ablation script, 12 signal skill table, all daily NAV, model scorecard, missing-Open audit, risk overlay, nominal bootstrap and report.
- It must be run with **previous complete original input/fit archive** `EU165_V2_V3_NATIVE_PAIR127_PILOT_20261029.zip`; original archive is not duplicated here.
- Frozen original USA149/V2/V3/B0 source and main branches unchanged.
