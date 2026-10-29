# EU165 native V2/V3: global Top5, concentration, blending, causal MA200, early-regime check

**2026-10-30 — Exploratory research; no production changes.** Archived source-native V2 and V3 European annually fitted OOS ticker scores 2018–26, historical PIT 500×24 stable-hash basket union, genuine next-Open trades at 10 bps one-way and persistently accounted capital and Close-marked NAV. 2026-survivor selection and dividends unverified.

Previous **GLOBAL_V3_TOP5** source simulation reproduced max NAV difference **6.66×10^-16**. Input 165 native ticker histories/source scores/baskets remain in separately archived EU165 research ZIPs; this branch is new research-only overlay.

**2021–24 (46 monthly native trades)**:
- V3 Pair127 Top5 unrestricted union CAGR **12.7849%**, maxDD **−21.6465%**, annual turnover 16.50×.
- V3 Top5 cap3 per macro group **11.1934%**, DD −22.3713%; cap2 **6.8451%**, DD −25.6371%; cap1 **5.0532%**, DD −24.9303%. Macro groups are NOT unique exposures/factors.
- V3 Pair25 Hybrid24 **15.7265%**, DD −25.0914% and turnover 14.34×.
- V3 Pair25 + half equity exposure when ex-ante EXSA.DE Close below its own past 200-session SMA **15.6662%**, DD **−16.5102%**, Sharpe 0.921.
- V3 Pair25 + zero equity exposure below MA200 15.1320%, DD −14.6508%, Sharpe 0.979.
- V2 Full Hybrid24 Top5 14.9006%, DD −26.2474%.
- V3 Pair25 minus V3 Pair127 annualized paired log advantage +2.62pp, circular 6-month block 95% CI **[−6.70,+12.12]pp**, includes zero; not proven.

**Unretuned 2019–2024 extension**: V3 Pair127 Top5 11.00% CAGR, −34.14% DD; V3 Pair25 full 12.52%, −32.03% DD; **V3 Pair25 + half MA200 12.27%, −22.69% DD**; 100% cash below MA200 11.21%, −14.68%. In 2019–20 half-MA200 achieves only **6.80%** annual CAGR and -22.69% DD; 2023–24 yields **24.11%** and -13.54%. The model remains regime-sensitive. Limited 2019 score coverage: 66 actual rebalance months for 2019–24; missing calendar months are held, no fabricated trades.

**Passive benchmark negative controls (same price-only Open execution, cash 0% and EXSA MA200 timing, 2019–24)**: SXR8.DE S&P500 UCITS buy/hold 17.20% CAGR / -33.78% DD, same half EXSA MA200 15.33% / -23.59%; XMEU broad Europe buy/hold 8.58%/-35.38%, half filter 7.76%/-23.59%. This refutes any assertion that V3 outruns *all* simple passive alternatives; SXR8 exposure not category matched to Europe, so stronger factor-matched benchmarking still necessary.

**Interpretation:** PIT basket union as discovery pool is worth investigating, but comparing one global 5-position portfolio against average of 500 3-position baskets changes structure; not controlled attribution. Concentration caps on coarse macro categories seriously reduce return. V3 Pair25 full ranking is a credible separate candidate, risk timing changes risk substantially, but extensive multiple testing of 2018–26 and wide bootstrap CIs disallow claims of alpha or production promotion.

All 165 histories used for portfolio pre-2025 include survivor/total-return/spread risks, mark-to-market ffill of missing Close. Future genuinely unmined vintages and verified PIT sector/currency/total-return data are required.

**Complete new experiment**: `ETF_TRADER_EU165_STRUTTURALE_ROBUSTEZZA_V4_20261030.zip`, SHA256 `65002274b737cead8c72677fd10b34dde79ffd1c4a009948fd26c8f96088b0ed`; 34 files, ~1.25 MB with replay scripts, all trade ledgers and annual/monthly CSV scorecards, bootstraps, source checks, NAV, passives and Italian report; references unchanged prior source-input archives, not a fully standalone dataset. No production modification.
