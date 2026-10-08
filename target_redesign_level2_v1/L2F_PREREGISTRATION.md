# L2-F — prospective-in-method, retrospective exploratory portfolio overlay

Date 2026-10-08. **Registered after L2-E dual-ranker outcomes were inspected**, therefore this is a *new exploratory design*, NOT an untouched confirmation. Scope unchanged: only AM1975MA/Test; no write to Etf_trader.

## Rationale (known before this rule is evaluated)

Score fusion improved some cross-sectional prediction metrics but two frozen dual-ranker candidates failed their preregistered simultaneous stability/skill gates. An allocation overlay can cap the effect of an unstable XGB top1 *without pretending its ranking itself becomes stable*.

## Single frozen allocation candidate

`CORE75_SATELLITE25`:
- At each monthly next-session OPEN, target **75% current marked-to-market equity in the ETF selected by stable Ridge** and **25% in XGB's chosen ETF**. If both select same ETF hold 100% that ETF; aggregate positions by ticker.
- In each Yahoo acquisition, only models from that same vintage are used, each forecast available on the preceding month-end signal, no future outcomes, no lookahead across vintage.
- Only **one** mix evaluated: .75/.25, no trial of other ratios or dynamic confidence thresholds. This ratio was previously used in L2-E's *score fusion*, but it has a distinct meaning here as a **capital allocation** fraction; outcomes cannot be treated as confirmatory.
- Buy first signal at next open, monthly rebalance at next-month next-open using current drifted position values, sell all at final next-open after the last signal. Charge **0.1% of actual traded dollar notional for every buy and every sell**; solve self-financing transaction constraint exactly, no negative cash/leverage or free rebalance assumption.
- Universe and raw acquisition remain pinned from artifact 11272972639. 112 monthly returns 2017-03 to 2026-07, 149-ticker Original149 universe; no BIL cash benchmark; BIL can be a normal traded ETF in frozen source.

## Compare against

- Reconstruct self-financing 100% Ridge Top1 and 100% XGB Top1 with *the same exact cost engine and time boundaries*; match prior L2-D published single-name CAGR and wealth to high precision or fail.
- Compare L2-E single-selected rank fusion as **external diagnostic** only; not an alternative optimized mix.
- Aggregate 3-vintage results for portfolio-level CAGR, monthly-sampled peak-to-trough drawdown, monthly return dispersion, total traded notional, effective round-trip costs, initial/final costs and number of distinct positions per month.
- Pairwise vintage **weight total variation** `0.5*sum_tickers abs(weight_v1-weight_v2)` at signal time: 0 means identical targets; 1 disjoint allocations. Also report exact ETF Top1 disagreement for XGB vs Ridge to avoid conflating decision stability with capital robustness.
- One-month vintage differences in realised portfolio monthly return and mean absolute vintage return difference. The 3 downloaded versions refer to the **same time history** and only diagnose sensitivity.
- Paired 3-month moving-block bootstrap of **calendar-date means**, 10k replicates, selected difference CORE75 minus 100% Ridge and CORE75 minus 100% XGB. Descriptive CI, no multiplicity-corrected causal financial edge.
- Note that static 75/25 target is not automatically ex-ante volatility/risk balanced. No stop/governor, basket portfolio, backfilled index reconstruction or actual live execution. Monthly-sampled drawdown is lower bound on possible intramonth max DD.

## Non-negotiable QA

- Use fixed prior predictions, audit 113*3 matched monthly decisions from both models.
- On each asset closing/entry next-open date, use **same benchmark SPY trading calendar** as L2-D, ensure price present for all selected tickers; no fabricated opens.
- Every transaction cost is nonnegative; posttrade holdings nonnegative and sum of holdings = postcost wealth; exact dollar conservation with turnover fee; no portfolio value negative, no erroneous dividend charging because adjusted OHLC is used.
- One-ETF baseline reproduces frozen L2-D wealth/CAGR across all six vintages/models.
- Prohibit results-based modification of ratio, costing, evaluation windows or rules.
- All computations saved as source and audit; **no promotion**, even if retrospective proxy appears favorable.
