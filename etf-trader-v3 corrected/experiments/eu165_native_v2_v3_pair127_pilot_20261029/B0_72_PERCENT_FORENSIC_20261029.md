# B0 EU155 72% claim — independent forensic check (2026-10-29)

**Finding:** NAV of archived strategy `EU148_PLUS_INDEX / LIQ50 / MOM252 / Top5` actually rises **+71.8102%** over **2025-02-03 through 2026-02-02** (364 elapsed calendar days; **+72.1298%** calendar CAGR). This is **one unusual historical year**, **not** annual expected or full-period strategy CAGR. B0 is **not** the ETF Trader V2/V3 production full-stack.

Whole 2018-02-01 — 2026-07-01 sample: annualized CAGR **+8.8066%** and maximum drawdown **-35.2840%**. Calendar 2025 (last 2024 session to last 2025 session) +76.8239%, accounting for **80.2938% of the full sample log wealth gain**.

In 2025, **57/60** monthly Top5 slots are bank ETFs (EXX1.DE, EXV1.DE, SC0U.DE, S7XE.DE, LBNK.DE). B0 daily returns versus EXX1.DE daily Open-to-Open returns over 2025-02-03 through 2026-02-02: **r=0.989235**, **R²=0.978585** (244 paired daily returns). Passive price-only EXX1.DE over precisely the same window: **+80.1215%**, compared with B0 +71.8102% net simulated; ETF dividends and transaction cost semantics not exactly comparable.

Independent validation: STOXX® Europe 600 Banks 2025 +72.33% EUR gross, iShares EXX1 2025 +89.24% NAV with reinvested distributions. Source archived ETF prices from `EU148_EU155_YAHOO_ISIN_QUALITY_AND_48_RETTEST_20261027.zip` SHA-256 `8c0028d66fd66b8b5c73438980aac759c6e2b4b37729276db2adfd23b77138a8`. No new downloads in numeric calculation.

**No demonstrated independent alpha.** Most of the 2025 performance is a concentrated bank-sector beta; the 2026-defined universe is not survivorship-free, 2018–2026 is extensively mined, dividend adjustment and real execution costs remain uncertified. No look-ahead *directly in MOM252 signal* was found in the separate bounded replay audit, but this is not certification of absent research leakage.

Reproducibility: conversation downloadable archive `B0_AUDIT_72_PERCENTO_20261029.zip`, containing independent `reproduce.py`, raw-archive SHA, annual returns, 2025 bank selections, ETF price comparison and JSON metrics. This GitHub record is summary only, frozen models unchanged.
