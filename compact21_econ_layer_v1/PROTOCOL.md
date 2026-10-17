# COMPACT21_ECONOMIC_LAYER_V1 — preregistered, stacking only out-of-sample BASE

Date: 2026-10-17. Repository AM1975MA/Test, research branch research/compact21-economic-layer-20261017, **NO production adoption**. This is ONE fixed second-stage economic calibration on top of original Compact21 BASE, NOT replacement XGBoost learning, and not a hyperparameter search.

## Controls, sources and time

Original unchanged 125-feature XGBRanker BASE scores, 360 rounds x 3 seeds with native NaN, trained each January on *mature earlier-year* returns, are reused from byte-hash verified `predictive-BASE` action 37229180477; absolutely NO base refit. Training and forecast data are 3 **dependent revisions** of exactly the same frozen Original149 historical raw market, annual 2017–2026, monthly 21-session exit. Three complete source snapshots `TI_COMPACT.parquet` from run 37150436612 and frozen full economic replay data from 37121749852, 38565352286, 37195399755.

For **each January Y**, fit the calibration layer on historical annual **BASE out-of-sample predictions** from 2017 through Y−1, with actual 21-session label exit **strictly before January 1 Y**. Never fit on BASE predictions from its own underlying training period; never fit to currently evaluated forecast labels. Separate fit per Yahoo revision. BASE OOS scores are verified against original source and its exact query keys. Set **min 20 distinct mature OOS signal dates**; without this history, leave BASE unchanged (typically 2017/2018). The fact that backtest 2017–2026 has been repeatedly evaluated means no inference from this research can establish a clean prospective gain.

## Fixed economic calibration recipe

For each ETF/date meta input: (1) BASE XGBoost within-date percentile rank, plus (2–9) these ORIGINAL already computed canonical input features:
`mom21_pct`, `mom63_pct`, `mom126_ex21_pct`, `vol21_pct`, `downvol63_pct`, `drawdown63_pct`, `efficiency63_pct`, `rsi14_pct`.
No new price, OHLCV, labels or macro information introduced; the other 117 Compact21 features remain available to original unchanged BASE XGBoost.

Economic training label is within-date **actual open-to-open 21-session ETF return minus same-date median ETF return** (then `clip[-0.25,+0.25]` in decimal returns). These target values are used **only in historically mature layer training rows**, NEVER during layer inference. Fit training-only per-feature median imputation (all-missing -> fixed zero), training-only standardization (constant-feature scale -> 1), and sklearn `Ridge(alpha=200, fit_intercept=True)`. Ridge output is an estimated relative 21-session economic return (regression, not calibrated probability). For each prediction date, rank this economic prediction across the same ETF cohort.

Final layer score is **0.70 × BASE percentile rank + 0.30 × economic prediction percentile rank**, a predeclared fixed blend, no learned strategy weights, no tuning by test outcomes. Before 20 mature historical OOS dates, output exact BASE score unmodified. Verify the final normalized scores contain finite values; ties use deterministic ascending ticker order for audits. The layer's aim is to preferentially reorder ETFs when supported by learned *economic* value rather than absolute ranking alone.

## Fixed evaluation and blocking gates

10 chronological annual folds, 3 vintage fits per eligible layer year, full original 149-ETF coverage, native and common inference exactly identical to BASE keys. Verify train maximum signal/label exit dates, meta-OOS source provenance, all source SHA hashes, training date count, prediction hashes and rebuild deterministic predictions. Compare with untouched archived BASE native/common predictions:
- **Primary** lower signed top-10%-average regret: top-decile mean 21-session realized return minus selected ETF realized return, date-weighted after averaging revisions. Report exact best-ex-post regret and selected-realized-return, plus hit exact/top5/topdecile, top5 overlap, NDCG@5, RankIC.
- 3/6/12 calendar-month paired moving-block bootstrap, 1,000 iterations seed 20261017, exploratory only. Development gate: primary regret improvement strictly positive (candidate minus BASE strictly negative) AND 3-month bootstrap upper 95% CI <0, exact-best regret no worse, top5 hit no lower than BASE by 1 percentage point, NDCG5 no lower than BASE by .01, three revisions each primary regret noninferior. If missing data or invalid values => fail, not rescued by CAGR.
- Standalone source-disagreement Top1 on common dates; inspect years 2021 and 2023.

Then, **unconditionally** run THREE fully unchanged canonical source-only V2 portfolio replays, retaining original 149 ETFs, 2366 sessions, costs, allocations, all other components, ensemble rules and risk. Verify original BASE parity and source-linkage before replay, independently rederive CAGR, MaxDD, Sharpe from equity paths, report yearly results, source CAGR span, daily Top1 disagreement. Research economics requirements mean CAGR>=95% BASE; mean MaxDD within −2pp of BASE; mean Sharpe>=95% BASE; daily Top1 disagreement<=BASE. These are descriptive development gates, not evidence of live trading success.

Research model remains isolated in draft PR. Retain failures and counterexamples; **no parameter changes after reviewing outcomes**.
