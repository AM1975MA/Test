# G2 transfer test, 69 ETFs excluded from the original completeness-ranked Top150

Frozen post-G2-result on 18 Oct 2026, BEFORE any 69-ETF transfer backtest.

Objective: Determine if the *unmodified* G2 structural reduction of 2-ETF concentration by one ETF per six macro asset classes transfers to 69 other US-listed ETF histories from the SAME 219-ticker frozen Yahoo vintage. Selected exactly by set difference FULL_219_QUALITY_CENSUS minus OASIS_TOP150: 69 names (all six groups represented; US-sector/theme only 2). Must NOT cherry-pick particular tickers, ignore extreme-return funds or fill missing future prices.

Research status **out-of-roster stress transfer, NOT genuine independent PIT holdout**. These 69 names were previously accessible in ETF research (original archive named holdout70), and 2017-26 cohort exists only if surviving to the contemporary snapshot. It is never a prospective forecast.

Use:
- Existing unchanged `oasis.observers.prepare` for same price-only as-of scores; never use failed G1 paired forecasts or ML rank.
- Existing frozen G2 algorithm for R0...R6, identical macro-category selection, capped inverse 63d vol, Student-t tail budget, 0.1% one-way fees, dates, and next-OPEN share accounting.
- Modify **only** the minimum-data input assertion `len(ordered)<100` to a schema-valid requirement of ≥12 eligible tickers (sample N=69); all 150 original sessions have 150 names and are unaffected. No economic model changes.
- Build 69 roster deterministically from source Full219 census and top150 membership; verify each raw CSV SHA256. No performance-based filtering. Do NOT add or remove a class because of realized returns.
- Compute G2 R0 two-ticker name and economic path independently, then match its full daily wealth against `oasis.daily_backtest.simulate(P0_MONTHLY_GREEDY)` on exactly the 69 universe and identical timeline to ≤1e−8 absolute wealth. No claim of trade economics without parity.
- Reporting: all seven 69-ETF arm CAGR/daily DD/Sharpe/ES5/exposure/fees/turnover; 2017-20/2021-23/2024-26 annualized returns; comparison with original 150 results and same-source SPY/60-40 context. Pair monthly circular 12-month block bootstrap interval vs local R0.
- **Hypothesis of reproducible structural diversification**: R2 and/or R3 should outperform local R0 in at least daily MaxDD and empirical daily ES5, and not lose more than 3 percentage points CAGR. Also report versus local R1 Top6 equal to check whether asset-class mixing adds beyond just using six holdings. No thresholds may change after the results.
- Stop if any group not represented, insufficient quote history, source hash mismatch, economic parity failure or any future-price observation enters as-of decision.
- Negative results will be reported as definitive development failures, not tuned. No live deployment from this panel.
