# OLC27 checkpoint01 — verification before economic outcomes

2 November 2026. Protocol previously frozen at commit b50e756831cd7b237083fabe0fe2c901ddf8597d. Before inspecting any candidate result:

- Reused EU/USA OLC26 predictor frames and OLC20 AUTH scores. Differences in FUSION due to separately serialized CSVs reached only 1.11e-16; the test intentionally failed first and was repaired by asserting absolute tolerance <=2e-16, then using **canonical AUTH score values** in model fit and decision. No empirical outcome influenced this fix.
- Four local tests passed: mature-label strict cutoff and 50/50 pooled-market weighting; deterministic Top5-only insertion/fallback; exact 2021 fallback and finite-score support; fixed-seed negative control repeatability.
- The genuine OLC27 procedures are AUTH_ONLY, LONG_POOL and LONG_STRAT, plus AUTH reference. Three target-shuffle controls LONG_POOL_NULL27001..27003 are *not* strategy candidates.
- The same alpha/C, features, score-gap and probability-gap thresholds apply in both markets. No trailing results have yet been inspected.
- Replays must verify eight AUTH reference accounts before any candidate conclusion. No main modification or live trading.
