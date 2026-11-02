# OLC29 — KAMA alone for best-ticker gap, leadership timing and persistence

Research-only; protocol registered BEFORE candidate outcomes. Frozen parent OLC20 AUTH FUSION and OLC19 risk engine, both markets EU165 / USA149, no other indicators newly introduced. OLC28 was a gross Top5 proxy; OLC29 must run actual V6-consistent OLC19 portfolio accounts.

## Goal (primary is NOT CAGR)
Determine whether KAMA can cause earlier discovery of persistent leaders and more effective exposure to the best buy-and-hold ticker in each universe. Benchmark is best *ex-post* fixed ETF on matched Open-to-Open historical interval: EU QDVE.DE for both 2021–2024/full; USA ARGT for 2021–2024 and SMH for full. Benchmark selections are diagnostic only, never used in decision rules or parameters. Report every year 2020–2025 separately and cost-stressed portfolio risk. All tickers are treated identically by KAMA.

## Causal indicators
Use daily Close and EU observed mask at or before the end-of-month signal date. USA prepared finite-positive Close, original observed mask missing (explicit caveat). KAMA(ER10,fast2,slow30) as in OLC28; KAMA direction KAMA[t]>KAMA[t-5], above KAMA Close[t]>KAMA[t], ER10>=0.25. Persistence requires direction+above at current signal and previous two *monthly signal dates*. Never use future Close or target for signals. Missing support -> no opportunity, no persistence intervention; leave AUTH.

## Two fixed KAMA-only candidate action rules
A) KAMA_PERSIST (one-month TTL): From preceding target pair, if one outgoing ticker still meets persistent KAMA and is otherwise replaced by AUTH Top2, retain it for ONE extra signal only when score FUSION gap versus displaced AUTH second choice <=0.05. No consecutive veto of the same carry unless AUTH itself reselects it. Max one replacement difference from AUTH.

B) KAMA_OPPORTUNITY: From AUTH ranked top 75 (FUSION, sorted deterministic), candidate must have valid persistent KAMA, ER10>=.25, and FUSION score >=.65 and within .25 of AUTH second score. Choose candidate with highest five-day normalized KAMA slope (tie-break FUSION then ticker); require current lower-ranked AUTH Top2 fails KAMA direction+above; if candidate outside Top2, replace only that lower-score ticker. Max one change. Strictly same rule, thresholds, ranking and no ticker-specific tuning EU/USA. This is a deliberately broad diagnostic; not a live recommendation. The candidate pool is fixed before returns are read.

Also AUTH control exactly reproduces OLC20 arrays. No separate EMA/Hull/RSI feature, and no base model fitting; KAMA is a decision feature **inside the existing ranking→portfolio chain**, not a stand-alone KAMA trading system.

## Primary non-CAGR evaluation
1. Pair-level presence of fixed ex-post best ETF per monthly signal and entry date; average notional 50% Top2 allocation opportunities; count months of improvement/deterioration, first month each best ticker is selected; per-year counts.
2. Capture of gross next-month positive Open-to-Open benchmark movements: `sum(positive benchmark monthly log-return * indicator(best in top2) * .5)` relative to the sum of all positive benchmark monthly log-returns; comparison matched exact months. This is an opportunity proxy, NOT portfolio P&L.
3. Persistent-leader capture, defined without benchmark knowledge as membership of ex-post top decile of upcoming 126-trading-day return among *eligible* tickers; same support for candidate and AUTH. Report overlap with actual Top2, lead in first selection, and false-positive entries.
4. Primary visual: fixed best ticker NAV vs strategy NAV from same anchored start, and signed NAV gap. The strategy gap is a full path statistic, not an independent alpha test; benchmark selected with hindsight.

Secondary guardrails: exact portfolio CAGR, MaxDD, turnover, costs .001/.003, years 2021–2024 and full Feb2019–Jul2026, ALARM and FAST_LOCK3, 2020 crash. Distinguish true position exposure after stops from nominal 50% selection. No promotion solely from best-ticker capture.

## Integrity
Rebuild V6 excluding new Top2, identical engine/fee/stop/calendar; eight AUTH accounts exact to OLC20; independent NAV accounting and timestamp checks. No missing data fill; expose 2019/2020 warm-up. Zero-change results explicitly labelled identity, not alpha. No hyperparameter search after observed results; report both adverse and favorable outcomes. This is post-hoc exploratory research, no untouched forward holdout, no real execution or trading.
