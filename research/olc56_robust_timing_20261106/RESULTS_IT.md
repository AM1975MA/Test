# OLC56 — Robust covariance weights and DELAY3 on native OLC19 (6 November 2026)

**STATUS: RESEARCH ONLY. DO NOT PROMOTE.** Original OLC19 engine, main branch and trading production unchanged. Two separately pre-specified research experiments (P1 and P2), both on previously heavily mined historical dates, not a fresh OOS. Full results, scripts, daily and monthly data, independent QA, protocols, XLSX and ZIP are saved in ChatGPT Library at `/ETF_Research/OLC56_Robust_Timing_20261106/`.

## P1: Covariance consensus 63/126 windows — REJECT

Primary policy: same two original OLC19 ETFs, minimum-variance weight estimated separately on 63 and 126 past sessions. If the two estimates tilt toward the same name, use the *less concentrated* weight; if they disagree/missing, hold 50/50. Cap 25/75. No fitted return labels, no historical-return threshold search.

| Policy | EU CAGR 2021–24 | EU FULL Feb2019–Jul2026 | USA CAGR 2021–24 |
|---|---:|---:|---:|
| B0 original 50/50 | 23.20% | 19.76% | 50.77% |
| B1 minvar63 cap25/75 | **29.31%** | 20.84% | 47.73% |
| RB consensus 63/126 | 25.32% | **18.87%** | 47.45% |
| B2 inverse two-factor residual volatility | 25.45% | 20.62% | 49.04% |

90 monthly events/market: 72 same-direction estimates, 11 disagreements, 7 incomplete. For EU May/June2025 both windows still tilt 25/75 and replicate B1 losses (about -243/-155 logbp vs 50/50), while disagreement in EU May2023 causes RB to lose about 382 logbp of the favorable B1 effect. The null inverted-tilt EU main CAGR 20.56%; directional risk shrinkage is not an economically reliable regime gate. No threshold tuning after rejection.

## P2: DELAY3 on original 50/50 — HISTORICAL CANDIDATE ONLY

Single candidate independently identified by prior OLC05/06: use ORIGINAL OLC17 vector engine built-in `policy='DELAY',fraction=3` inside frozen OLC19 FAST_LOCK3. If there is an existing position and a changed pair, the new target executes at the THIRD trading-session index (k+2). Stop monitoring, V6, risk, Top1/Top2 and fee logic remain original. Signal ticker ranks are constant throughout each of the 90 monthly spans. Re-executing the SAME private engine with `policy='IMMEDIATE'` reproduces the **seven OLC19 arrays bitwise** in both markets.

| Market/window | Original B0 CAGR | DELAY3 CAGR | Original MaxDD | DELAY3 MaxDD |
|---|---:|---:|---:|---:|
| EU 2021–24 | 23.20% | **28.11%** | -28.61% | -28.65% |
| EU FULL | 19.76% | **22.05%** | -28.61% | -28.65% |
| USA 2021–24 | 50.77% | **55.31%** | -20.23% | -17.08% |
| USA FULL | 39.48% | **43.26%** | -26.12% | **-30.40%** |

EU DELAY3 annual actual returns 2021 25.87% vs 21.83%, 2022 -1.79% vs -6.30%, 2023 76.21% vs 67.30%, 2024 25.85% vs 22.44%, 2025 14.32% vs 17.95%, 2026 partial 18.81% vs 16.51%. USA annual delta (pp): 2021 +32.01, 2022 -14.57, 2023 -4.59, 2024 +1.75, 2025 +3.41, 2026 partial -6.47.

Fee coefficient .003 (instead of .001), 2021–24: EU B0 19.88% vs DELAY3 24.67%; USA B0 42.73% vs DELAY3 47.19%. POSTRESULT stop-fill friction stress .005: EU B0 22.60% vs DELAY3 27.53%; USA B0 48.35% vs DELAY3 52.80%.

## Critical uncertainty and inference

EU 2021–24 25/48 months have positive DELAY3 paired delta, USA 26/48. BEST THREE MONTHS account for 84% of the total EU and 142% of total USA positive main log uplift. Descriptive 6-month circular block bootstrap CI95 for DELAY3 minus B0 **annualized paired LOG** return (not CAGR delta): EU main +3.97pp [~0.00,+7.84]; USA main +2.96pp [-8.61,+15.05]. FULL bootstrap intervals both include zero. No multiple-comparisons correction. OLC06 already exposed the favorable timing hypothesis: this is a native OLC19 replication, **not independent confirmation**.

## Source and methodology limitations

Source original OLC19 checkpoint sha256 `3b5799dae060c104408f581c70280cef8ce4d84c3978434d4e6ba81108f16540`, located in ChatGPT Library original `/ETF_Research/OLC19_Rischio_Rientro_20261102/`. B1 OLC51/OLC52 NAV parity to <=1e-12. Fee legacy on half-turnover and stop bar fills lack broker-grade quote evidence, opening-auction reproducibility, true spreads, dividends, PIT/delisted ETF histories, and USA original-quote observed mask. Research calendars end on first opening of July 2026; no new unexplored period. Single combined policy DELAY3×25/75 is **not** executed here and cannot be inferred by addition.

**Decision:** reject P1. Preserve P2 as research candidate pending venue-level first-two-session execution QA, independent future observations and risk-adjusted robustness. Do not deploy or optimize timing grid against 2019–2026. Full archived source code and outputs in the Library folder above.