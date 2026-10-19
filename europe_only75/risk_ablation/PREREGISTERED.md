# E60-R - Frozen EU risk ablations
19 October 2026 - freeze protocol BEFORE trial outcomes.

## Source
Use precisely 60 EUR candidate lines with European underlying exposure in europe_only75/UNIVERSE_EUR_LISTED_60.csv, nested within the 75 geography-pure ETF lines. The historical universe EXCLUDES 45 non-Europe geography/US non-UCITS and 15 Europe-exposure but non-EUR trading lines.

Frozen 2017-2026 annual walk-forward European retraining of 60 XGBoost Compact rankers and 20 HybridTail models was already completed successfully by Action 39071370480, artifact europe-only-eur60-full-refit. Reuse the precomputed annual OOF European scores, NEVER models trained on 149 US ETFs. Baseline B0 is existing Europe R_H predicted top TWO ETF each 50%, where R_H score is 47.5% return-aware percentile rank plus 52.5% HybridTail score. All dates and scores frozen; the European test is not a literal F3/H1 refit.

Prices: original data/eu120/raw_ticker_csv 60 EUR candidate OHLC histories. Rebuild EXACT source common monthly next-Open calendar using 60 candidate and five US-market reference price series (SPY/HYG/IEF/BIL/SHV), never buying those reference instruments. Use only genuine preceding completed Close for state. Reconstruct archived European R_H FIXED_5050 terminal wealth under its own approximate one-way 0.5 portfolio turnover fee convention; then use a newly verified consistent true share-level fee (10bps per gross ETF buy/sale) and cash ledger for ALL five comparison arms. Do not equate these differing simulations.

## Four standalone interventions with frozen parameters
E1 EU category concentration: if the original R_H Top2 both belong to same European macro-category, hold 40% per selected ETF +20% idle 0%-return EUR cash, otherwise 50% each. Categories are the frozen geography-audited EU_BROAD/SECTOR/COUNTRY/FACTOR/SOVEREIGN/PROPERTY. This is imperfect factor proxy, not estimated detailed beta.
E2 volatility20: 63 completed synchronized Close returns covariance, 50% sample covariance +50% diagonal, annualized baseline volatility; position exposure clip(0.20/vol,0.40,1.0), remainder cash. All ETFs retain original Top2 and equal relative capital.
E3 trend126: if as-of 126-trading-session weighted two-ETF log Close momentum negative then invest total 50% in the same Top2 and 50% cash until next monthly rebalance, otherwise fully invest.
E4 ranking buffer: two positions; allow a previously held European ETF to persist when currently among top4 of R_H ranking and within 0.15 current cross-sectional standard deviations below current rank2 score. Retain eligible prior positions first, fill missing from current R_H ranking. This is the only intervention allowed to change original picked names, but all candidates are 60 European whitelist members.

All costs charged on actual traded ETF notional 0.1% each side, idle cash zero interest/fees, exactly next-common-Open shares, fully self-financing, no leverage, no extra intramonth trades. Each arm independent, no combinations or parameter sweeps, original R_H model never retrained in this experiment.

## Scoring and preregistered gate
Costed daily-common-Open CAGR, MaxDD, worst5% daily arithmetic ES, annualized log Sharpe, volatility, cash fraction, turnover, underwater duration, 3-month circular-block bootstrap on date-level monthly paired net log return vs frozen score baseline; compare early 2017-2020, middle 2021-2023, recent 2024-2026.
For any arm scientific GO requires all:
(1) mean monthly paired net log gain >0 with Bonferroni-corrected 98.75% two-sided confidence lower bound >0 (4 policies);
(2) maxDD improves by 1.5 percentage points or more;
(3) daily ES5 does not deteriorate;
(4) monthly net log gain positive in each three fixed eras.
Anything else FAIL; no parameter changes based on outcome. This is a repeatedly explored, hindsight-membered EU set, NOT point-in-time validated. EUR currency and same-ISIN duplicates need live provider verification, spreads and taxes not tested. No etf_trader production changes.
