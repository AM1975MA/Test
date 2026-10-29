# EU155 B0 — sector trend selection and reversal forensic audit (2026-10-29)

**Exploratory research only. No production, USA149, B0, V2 or V3 change.**

Input is frozen original 29-Oct? actual archive version 2026-10-27: `EU148_EU155_YAHOO_ISIN_QUALITY_AND_48_RETTEST_20261027.zip`, SHA256 `8c0028d66fd66b8b5c73438980aac759c6e2b4b37729276db2adfd23b77138a8`.
Policy: EU148_PLUS_INDEX / LIQ50 / MOM252 / Top5. Exactly 101 monthly selections, 2,076 market dates 2018-02-01–2026-07-01. Original frozen NAV CAGR **8.7936%**, DD **-35.284%**. A source-derived original `sim_all` replay yields **8.7995%** CAGR, **-35.284%** DD, with maximum relative daily NAV discrepancy **0.168%**; no exact parity claim. Zero future data used in signals; execution next common Open / 10bps per traded side.

## Historical selection and the banking trend
- Bank category here comprises five European bank-sector ETFs (EXX1, EXV1, SC0U, S7XE, LBNK). Shares of all monthly Top5 slots: **2021:15/60, 2022:5/60, 2023:24/60, 2024:30/60, 2025:57/60 (95%)**. 2018–20: zero.
- Banking positions rose to 3/5 by signal **2024-03-28**, to 4/5 by **2025-01-31**, to 5/5 by **2025-04-30**. This is true momentum selection, not manual retrospective sector assignment.
- Selected Top5 next-month Open return beat contemporaneously LIQ50-eligible ETF cross-sectional mean in **59/101** months overall and **10/12** in 2025. Mean monthly gross excess **+0.244 pp**, nominal 6-month block 95% CI **[-0.392,+0.936] pp**; through **2018–24** (84 signals), **-0.020 pp**, nominal 95% **[-0.494,+0.423] pp**. 2025 +3.365 pp (10/12), 2026 first 5 months -2.804 pp (1/5). This benchmark is diagnostic, not cost/risk-matched.
- **2018–2024 B0 CAGR only 2.60%**; 2025 annual NAV gain **+76.82%**, whole-window 8.8%. The full performance is not generalizable evidence of persistent alpha.
- 2026 exit risk: banks 5/5 in 2026-01, 2/5 in 2026-02, 0/5 in 2026-03. After **2026-05-29** signal B0 fell **-5.64%** while eligible bank ETFs gained **+6.38%** on average in the same subsequent Open-to-Open window. These 2026 diagnostic comparisons are NOT untouched holdout validation.

## Perturbation tests on identical archived 2018–26 calendar (CAGR / MaxDD)
- Unmodified B0 reconstructed: **8.80% / -35.28%**
- CAP3 macro-category (not sector) allocation slots: **9.20% / -32.84%**, paired six-month bootstrap annualized log difference +0.363pp [−2.019, +2.846]pp. No significant advantage.
- European broad `EXSA.DE` close below its own 200-session MA → all cash until next monthly signal: **8.11% / -26.97%**; nominal paired CI annualized log [-5.423, +4.453]pp. Reduced DD but cost in CAGR. Cash 0% assumed, no UCITS substitute certified.
- Selected Top5 median 63d momentum ≤0 → all cash: **8.16% / -36.44%**. Unhelpful.
- Rank hysteresis keep previous ETF as long as eligible rank ≤10: **7.86% / -34.27%**; ≤8: **7.04% / -34.27%**. Less turnover but worse CAGR.
- Maximum two bank ETFs: **5.98% / -35.28%**. Removing 2025 concentrated sector beta damaged historical performance.
Other results in the archived audit.

All 2018–26 data have been mined repeatedly, historic 2026 survivor ETF universe, incomplete vendor dividend/total return documentation, zero-volume traded lines and uncertified executable spreads. No test variant promoted. Main research recommendation: preserve B0 ranker, measure cross-sectional within-sector skill with provider index benchmarks / true point-in-time constituents, treat MA200 as optional risk-budget **candidate only**, require new prospective data.

Full self-contained archival ZIP (includes original frozen input, audited Python scripts, dated nav/selection CSVs, monthly trades, bootstrap and source-parity checks): conversation artifact `B0_EU155_SELECTION_TREND_REVERSALS_AUDIT_20261029.zip`. This GitHub branch stores provenance and summary; the complete source bundle is available in the user-visible ZIP.
