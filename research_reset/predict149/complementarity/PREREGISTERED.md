# T149-I F3/H1/H3 complementarity and causal regime mixture — frozen BEFORE first run
2026-10-19 | `research/149-complementarity-regime-meta-20261019` | **EXPLORATORY, repeated original149 dataset; no production trading**.

### Central falsifiable claim
Original frozen F3 / H1 / H3 historical 2021–26 curves have different strong years. Does this complementarity occur at the **same-month realized relative return** or only as a selected set of calendar years, and can it be exploited by rules using **ex-ante observables only**? The answer requires measuring correlations, varying actual ETF overlap, **conditional returns by prior-close market state**, and *actual share-level* mixtures — not algebraically averaging nontradeable backtest wealth paths.

### Exact unchanged historical source / trade accounting
- Exactly 149 fixed US ETFs in `oasis149.canonical.load_149` (retrospective survivor cohort, not PIT or EUR brokerage eligible). Exactly **64 identical full non-overlapping 21-trading-session investment blocks** between February 2021 and June 2026, open fills. 10 basis points per side, fully invested, no leverage, same next OPEN, same dates, no intramonth lookahead. Use archived `FULL_9536_ASOF_FACTOR_AND_RESIDUAL_FORECASTS.csv` as immutable **ticker/month precommitted** forecast scores for F3=`B0_F3_FROZEN`, H1=`H1_FACTOR_ONLY`, H3=`H3_COMBINED_Q`.
- First reconstruct all 3 exact five-ETF portfolio curves from names and next-open shares with `rebalance_exact`; fail if any daily-wealth error vs archived curves exceeds **1e-9** at any date. No model retrain, no feature tuning.
- All blended strategies operate on actual ETF share weights, merging ETF weights across experts at each rebalance, with every buy and sell fee paid. Can't use weighted average of wealth paths as a substitute for rebalance.
- For **causal expert-state decisions at prior signal Close s_b**, latest permitted fully realized P&L is from block **b−2 or earlier**. Block b−1 ends at the exact Open of block b, therefore WOULD BE UNAVAILABLE at s_b; using it creates one-day lookahead. Strict explicit assertions `block_end_open[b−2] < signal_close[b]`. All market/volatility indicators computed on prices up to as-of signal Close, with future-mutation tests.

### Predeclared static mixtures / causal dynamic strategies (NO selection after outcomes)
Exactly these eight named policies and 3 frozen experts:
- `F3`, `H1`, `H3` individually, exact prior replay;
- `STATIC_F3_H1_50`: each month 50% weights of each Top5 F3 and H1;
- `STATIC_F3_H3_50`: 50% F3 and 50% H3;
- `STATIC_3_WAY`: one-third each F3, H1, H3;
- `SWITCH_PAST3`: allocate 100% to F3 if F3−H1 **cumulative log net return on the latest 3 fully matured blocks** is positive, otherwise 100% H1; prior to 3 matured blocks use 50/50. Since only b−2 labels are known, the last 3 matured are `[b−4,b−3,b−2]` (relative to 64-anchor eval sequence); any use of b−1 is forbidden.
- `SWITCH_PAST6`: identical rule, trailing six fully matured blocks `[b−7,...,b−2]`; until six matured, 50/50.
- `ONLINE_RIDGE_GATE`: from completed training examples n where n <= b−2 (strict maturity), fit **only if ≥12 matured anchors**, train-only StandardScaler and Ridge(alpha=25, fit_intercept=True) to predict the *21-session net F3−H1 log return differential* using 8 contemporaneously historical **features as-of each earlier decision**: SPY63 log return, SPY21 log return, realized SPY vol21, realized SPY vol63, HYG−AGG 63 close return, fraction original149 ETF trailing63 logreturn>0, cross-sectional ETF trailing63 logreturn dispersion, and F3/H1 top5 overlap share. Current features observed before current Open only. Map predicted difference to F3 share = `clip(0.5 + prediction/0.10, 0.2, 0.8)`; H1 remainder. Before 12 matured examples 0.5. No refits on current/future outcome; ridge trained each monthly anchor; no CMA/gradient booster/HMM due 64 independent dates.
- `NONCAUSAL_ORACLE_F3_H1` diagnostic ONLY chooses *future* monthly F3 vs H1 based on gross realized 21-session return, with share-level costs, and is **untradeable**. Its apparent CAGR is not alpha or a legitimate target.

### Mechanistic analysis (diagnostic, not switches selected after inspection)
1. Year (calendar overlap only) F3/H1/H3 net monthly growth and sources; fraction of months each beats others; correlation of daily/monthly log returns and relative performance; expert predicted score correlations; top5 ETF overlap (0–5) by anchor and macrocategory exposure differences; number of distinct positions and realized turnover of mixtures.
2. Classify each anchor **only from prior signal Close**:
   - SPY63 log momentum positive vs ≤0,
   - SPY21 realized vol > SPY63 realized vol vs otherwise,
   - HYG63 − AGG63 log trend positive vs ≤0,
   - prior63 ETF breadth > 0.5 vs ≤0.5.
   Report n and F3−H1 future log-return difference per group with 95% anchor-level resampling; these are **EXPLORATORY post-hoc associative tests**, even though as-of features. DO NOT use a favorable hindsight indicator to define a new switching strategy on same history.
3. Upper-limit hindsight expert switch and market regime confusion matrix solely as upper-bound diagnostics, NOT a tradable best-case.

### Economically falsifiable gates
Primary: a Causal mixture must beat **both** static 50/50 and better frozen H1/H3/F3 on **paired month-level net log return** using 3-anchor circular bootstrap 95% lower CI >0 AND daily-open MaxDD no worse than both single F3 and H3 AND expected shortfall daily ES5 no worse than F3. The static 50/50 mixture is judged *robust diversification* only if it improves daily-open MaxDD versus BOTH F3 and H1 **without losing more than 1pp CAGR vs highest-CAGR frozen expert** (H1), and risk/ES does not deteriorate. Both gates are deliberately hard and may fail. Never modify gates after results. All policies (including failed) and source SHA archived.
- Diagnostic alternative: if causal switching fails while static blend improves risk, recommend frozen **simple diversified mixture** instead of falsely inferred "market regime timing alpha"; if both fail STOP and require new, previously unmined data.
- **Not independent:** repeated mining of same 64 anchors 2021–26 means neither bootstrap CI nor 500 matched random simulations proves generalization. The objective net **30% CAGR** is ambitious, cannot be guaranteed or invoked to justify future leakage.

### Mandatory audit
- Replay archived 3 equity curves to <1e-9 entire 1,345 daily Open points.
- Future price mutation as-of meta feature test; last known training P&L strictly ends before signal.
- All portfolio shares self-funded, exposure weights sum 1, per-side nominal 10bp, no leverage.
- Long-run cash 0 after each month rebalance; no equity-curve averaging.
- Save all 64 decision weights, observable states, 1,345 daily wealth paths, per-date expert hypothetical PnL, stats/correlations/indicator conditional analyses, bootstrap, full source hashes with Actions completed, no edits to `etf_trader`.

This is a research decision, **not** investment advice or a production switch. 
