# OASIS V1 — preregistration / 18 October 2026 (before empirical run)

The previously saved `oasis/SCIENTIFIC_ARCHITECTURE_V0_1.md` remains the scientific roadmap. This milestone is a **prototype, not implementation of the complete eleven-step proposal**. No use of prior ML/Return-Rank scores in signals, and no tuning after results. Run on isolated `research/opportunity-crisis-switching-20261018`, preserve old experiments, do not alter production.

## Core scientific decision
Can a **daily opportunity scanner plus economic no-trade region** produce a better *net, matched-execution* outcome than an otherwise-identical naive daily greedy selector or monthly portfolio? Does recognizing ongoing systemic risk and recovery add value beyond the same switcher without regime control?

## As-of data
Use only frozen `data/eu120/raw_ticker_csv` for 60 retrospective EUR60 tickers. As-of Close only up to prior completed session; execute at next trading Open. Common study endpoints come from frozen oracle 39084898663; **no oracle winner labels, no baseline ML prediction input**. Gap-limited imputation is not used for signals. A held name with no next Open is marked using last observed Open for valuation only and is flagged as stale; a NEW buy with no next Open does not execute. Trading dates require at least 30 simultaneous observed Open, and daily gap policy must be explicit in output. Any unfilled/partially filled exchange order should be counted; no knowledge of future Open may influence the *decision signal*, only its subsequent actual fill.

## Observable structure
- Return features: 21/63/126-session observed prices, rolling 63-day conditional vol, 126-day rolling as-of beta to an equally weighted broad cohort return. Proxy contains hindsight roster, not real independent Europe index.
- Relative efficiency: factor-adjusted 21/63/126 trailing expected 21-session log return, normalized conditional volatility and magnitude of persistence. Predetermined weights; no fitting to evaluation label.
- Breathing: conditional Student-t(5) innovation surprise using trailing rolling volatility and robust volatility adaptation. Normal variation threshold abs(z) <= 2.5, beyond may signal jump but not trend-break proof.
- Changepoint: causal approximate BOCPD **daily market standardized return mean** with Gaussian-conjugate run-length hypotheses length <=90, hazard 1/80 and fixed N(0, 2) mean prior. Predictive density of state change vs continuation; outputs posterior change probability and most recent five-session change probability. This is an approximation, not Student-t BOCPD and not a trained market forecast.
- Crisis: separate shock/systemic continuation/recovery/breathing based on down breadth, rolling realized vol state (two-speed Bayesian HMM), changepoint posterior and 21/10-day market momentum. A recovery must have recent stress AND 10-session positive market growth + positive breadth; no lookahead.
- Candidate posterior **relative expected advantage** = excess predicted 21-session log gain from factor-adjusted multiscale momentum vs currently held name. SE from 63-session paired daily-return volatility times sqrt(21/63) with 1.5 epistemic inflation. Bonferroni one-sided 95% hurdle applied to number of eligible alternatives, fixed cost 0.003 log units (conservative round-trip spread+fee proxy, not a measured spread). Select only if lower bound > cost and confirm 21-session relative strength positive. If no suitable alternative, retain previous positions. One ETF replacement per session and >=5-session holding-time in normal mode; crisis high-conviction risk signals may bypass cooldown when explicitly logged.
- Risk: in SHOCK or systemic continuation, 50% ETF exposure and 50% **hypothetical zero-yield cash**; recovery and breathing 100%. Always 2 holdings target, equal risky allocations; changes executed at next Open, costs charged. This is not a verified EUR defensive instrument.

## Fixed standalone arms on same 2017–2026 daily-open path
- `P0_MONTHLY_GREEDY`: same score, choose Top2 only at the first opening of a new month; otherwise hold; always 100%.
- `P1_DAILY_GREEDY`: same score, choose Top2 daily; always 100%; exposes overtrading.
- `P2_DAILY_ECONOMIC_HYSTERESIS`: two ETF incumbents, daily opportunity scanner, one-sided multiplicity-corrected relative-net improvement hurdle; always 100%.
- `P3_OASIS_CRISIS_ACTIVE`: **same P2 selectors**, crisis/recovery informed daily exposure + severe loss override; if currently stressed, first protective risk controls, then assess opportunity. This isolates crisis control under same switching logic.
- `P4_MONTHLY_GREEDY_CRISIS`: **same P0 selections**, daily crisis/recovery exposure; isolates regime benefit without opportunity switching.
- `P5_DAILY_TOP5_HYSTERESIS`: same raw price score, keep previous ETF if still ranked Top5; otherwise replace. Daily scanner, always 100%; a transparent simpler baseline (not old ML Top5).
- `P6_DAILY_ECONOMIC_HYSTERESIS_ONLY_CHANGEP`: same P2 with change-point posterior as veto against switches on isolated large innovations but no persistent regime change; controls value of rupture detector separately.

Each arm's daily positions must be independently replayed at next Open with no leverage. All arms get identical signal dates and day-open prices, consistent fees (10 bp one-way on full absolute risky trades + cash balance changes for 100%-funded rebalances), no free same-day closing execution. Measure real trade count, annualized turnover, split years, monthly and daily sampled maxDD and tail ES, shadow missed-opportunity gap, crisis onset/recovery performance, CIs on paired month returns.

## Out-of-sample and data limitations
Historical cohort selected with knowledge of future survivors: not PIT; 0 Volume source observations exist (cannot claim executable liquidity); source Yahoo price fields may be corporate-action adjusted and may not represent exact contemporaneously executable opens; no bid-ask or market impact; EUR underlying/venue uniqueness unverified. Same 2017–2026 observations already heavily mined. Parameter selection from this run forbidden. If all new arms lose money, admit it and preserve evidence; do not mine thresholds. Next critical validation is independent authentic PIT + daily adjusted price vintages with real venue spreads, at which point use split/embargo forward labels.

## Acceptance gates
- synthetic no-lookahead test: changing all prices after signal date cannot change current feature/decision.
- all policy positions finite and total risky not greater than one; new orders that lack actual opening price must not fill.
- same path start/end and fee schedules across policies; baseline prior period scores never read.
- all monthly and daily ledgers persisted with full signal diagnostics and source hash.
- detect and report any material data-quality issue; baseline failures stop reporting rather than silently ignore.
