# OLC67 — Full native OLC19 risk × allocation × execution factorial (PRE-OUTCOME)
7 November 2026. Research only; main and OLC19 production unchanged. The 2019–2026 calendar is heavily mined, so NO new independent OOS is available. This experiment is a post-hypothesis mechanical composition/interaction test, not a search over parameters.

## Question and fixed arms
Do the two independently studied candidates (OLC51 63-session MINVAR cap25/75 and OLC56 3-session DELAY) combine successfully inside the **original** full-accounting OLC19, and how does that interact with the known alternative BASE vs FAST_LOCK3 exit regime?

Fixed 2 × 2 × 2 grid:
- Original OLC19 TOP2_CONTEXT_REVALUE selections and V6, original 42-feature ET/XGB/Return FUSION, same OHLC inputs and dates for both markets EU165/USA149.
- Weights W0=0.5/0.5 vs W1=OLC56 frozen B1_MINVAR63_CAP25 weight from contemporaneous trailing observed Close (63 sessions), fallback 0.5, cap .25/.75. Original OLC56 EU/USA_DECISIONS frozen source, verify event keys and dates.
- Timing T0=original immediate vs T1=original OLC17 native DELAY fraction=3 (target at third trading session index k+2). No new grid of lags.
- Risk R0=original OLC19 FAST_LOCK3 vs R1=original BASE, identical stop friction .001 and original V6/risk gross logic. R1 explicitly accepts worse 2020/USA FULL drawdown; never silently choose by retrospective CAGR.
- Fee .001 and .003 fixed, no tuned costs. Whole 2x2x2x2x2 = 32 new or parity reruns.

The eight policy cells are compared on matching dates MAIN 2021–2024, FULL Feb2019–first open Jul2026, late 2025 and partial 2026; same native Python metrics() and independent recomputation of paired daily log-R. Record CAGR, MaxDD, turnover, fee, annual returns, and paired annualized log-return versus W0/T0/R0, not just CAGR.

## Prior selection rule, not return-data optimized
Define the **defensible** choice to be unchanged OLC19 unless a variant improves FULL CAGR in BOTH EU and USA, does not worsen FULL MaxDD by >3 percentage points in EITHER market, and does not worsen MAIN 2021–24 CAGR in either market. Report MAIN/FULL best historical CAGR by market as **in-sample descriptive only**, separately from defensible recommendation. If no variant passes, do not promote any. Do not combine market-specific winners into a strategy, and do not tune to 2025 after viewing results.

## Mandatory validation
- Archive SHA256 original OLC19 and OLC56; OLC19 default exact parity to frozen nav/ledger/positions/targets/risk_trace; W1/T0/FAST_LOCK3 parity with OLC56 original scores and W0/T1/FAST_LOCK3 parity with original OLC56 timing scores and where possible daily logR.
- Record all fee .001 and .003, EU and USA, four control arms. No future label used in signal or weights; first trade partial time conventions unchanged. No missing observed-mask represented as true observed data.
- An independent calculation reconstructs CAGR and DD from output daily log returns; annual returns and OLC19 period masks preserved.
- Stop-fill O/H/L/C quote assumptions, currency, dividends, delistings, reconstructed USA observation mask, lookahead/survivorship caveats apply.
- Only these 32 replay paths, NO extra hyperparameter search after outcomes. No new CAGR claim for unexecuted combinations.
