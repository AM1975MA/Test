# OASIS V2 G2 — risk-first scientific ablation / preregistered 18 October 2026

**Important sequencing:** G1 proper-score gate **FAILED** on 64 matured anchor forecasts (Action 39136487959). Thus the new relative forecaster is **not** permitted to drive a trading portfolio. G2 is an **independent survival experiment** on exactly the same weak original frozen OASIS price rank used in P0, to identify the impact of holding-specific portfolio tail risk, class diversity and exposure. It is NOT a repaired alpha forecast nor an independent return holdout. On research branch research/oasis-v2-paired-forecast-g1-20261018.

## Frozen question
Does spreading exposures across *economically distinct asset classes*, rather than blindly concentrating in the two highest trailing-return ETF scores, materially reduce daily wealth tail drawdowns at tolerable return cost? Separately, can a *portfolio-conditional* Student-t CVaR budget improve survival compared with a dumb **fixed exposure** control, or does it just reduce participation and miss recoveries?

## Source and strategy are deliberately held fixed
- Current 150 ETF frozen historical completeness roster, raw same-vintage adjusted O/H/L/C/V, portfolio dates/previous-close signals from the existing daily ledger \`oasis150/results/frozen/P0_MONTHLY_GREEDY.csv\`.
- All candidate names chosen with the ORIGINAL identical OASIS \`oasis.observers.prepare(C)["score"]\`, **no new ML signals or H2's G1 failed predictions**.
- Monthly first opening selects candidate names using **previous observed close**, all intervening days only risk controls may adjust exposure. New market open or missing adjusted quote is never used to decide at the prior close.
- Six macro classes as original manifest: US broad/style, sector/theme, developed global, emerging, bonds/cash/credit, real assets. These are approximate categories, not an actual calibrated hedge.
- 10bp nominal one-way trade fee on actual shares bought and sold at subsequent Open. Actual OHLC time series carry full-period adjusted Yahoo semantics; no verified bid/ask, EUR FX, venue/fund IDs or delisted funds.

## Seven fixed policies, all tested on identical continuous 2366-day opening-path
- R0 \`TWO_CONCENTRATED_REFERENCE\`: old P0 top2 monthly equally weighted (must reproduce frozen old P0 portfolio CAGR, MaxDD and wealth to floating accuracy; fail otherwise).
- R1 \`SIX_TOP_SCORE_EQUAL\`: top6 monthly raw rank equal-weight, no risk gate. Isolate reducing concentration without class control.
- R2 \`SIX_ONE_PER_CLASS_EQUAL\`: monthly top1 by identical rank *within each* of six macro groups, equal weight. Isolate economic diversification.
- R3 \`SIX_ONE_PER_CLASS_INV_VOL\`: same R2 membership, weights proportional to inverse lagged 63-day daily volatility with 25% single-ETF max, normalized. No future market covariance or mean included.
- R4 \`SIX_CLASS_INV_VOL_FIXED75\`: exact same R3 names and proportions but fixed equity exposure 75%; remaining 25% **zero-yield hypothetical** cash (exposure placebo).
- R5 \`SIX_CLASS_INV_VOL_T5_ES\`: same R3 relative risky weights, exposure target limited by as-of heavy-tailed 21-session projected 10%-tail conditional log loss <= 8%, cap exposure [0.20,1.00], applied daily with as-of trailing 126 daily returns; no market or ETF future values. Covariance 65% sample +35% diagonal, mean shrunk to zero, 384 seeded correlated Student-t(5) draws. This 8% limit is *not guaranteed* and not an approved regulatory risk control.
- R6 \`TWO_TOP_T5_ES\`: same R0 holdings, with exact identical R5 tail risk scaling. Isolate risk-sizing effect from diversification.

## Why these are not tailored
- Number six predetermined by available asset-category taxonomy (one per macro category), not by historical performance.
- 25% cap is structural risk governance.
- 75% static equity placebo probes the trivial "cash helps DD" explanation.
- Student-t(5), 65/35 covariance shrinkage, 126-day lag, horizon 21d, 8% ES tail cap, minimum exposure 20%, 384 scenarios and one-way fee 0.10% are **all fixed before G2 results**. They are model assumptions not financial laws.
- A daily risk-sizing action can trade, but risks being very costly. Portfolio controller must enforce >=3% absolute exposure-change threshold for non-monthly signal dates to avoid churn from Monte Carlo sampling, with exception for portfolio scenario one-month ES risk > 12%. This threshold derives from a cost-reduction design, not 2017–26 profitability.
- Same actual share, cash, buy/sell first accounting for all seven arms. Do not use adjusted close for entry/exit fills; daily value as-of opening quotes only.

## Risk decomposition and acceptance gate
Measure terminal wealth, annual CAGR, daily MaxDD, daily ES5, monthly ES5, Sharpe, number of names/correlated holdings, macro exposures, average invested amount, turnover/fee drag, worst daily loss and crisis continuation/recovery contributions.
**G2 improvement defined as R5 (i) reducing worst daily MaxDD versus R3, (ii) reducing at least one of daily ES5 or worst day, (iii) avoiding a *disproportionate* return sacrifice compared with the simple fixed-75% R4**. No subjective "more alpha" based on single CAGR; not a conclusive forward test.
Prohibit adding a new screen, fitting thresholds after seeing G2, or promoting G1 failed ranker. If R2–R6 fail versus controls, preserve failure and report that data/signal quality remains primary blocker.

## Scientific caveats and hazard controls
- Retrospective 150 cohort was selected with full 2017–26 information (survivorship bias); the new G2 is **after seeing P0/P3 failures**. No untouched holdout.
- Six groups may be strongly correlated in panics, and bond funds, metals and commodity futures ETFs are not guaranteed defensive. Group membership is from research CSV and should be confirmed by underlying index/asset characteristics before deployment.
- Adjusted Yahoo Open/Close are not executable broker quotes; false "safety" can be an artifact of optimistic next-open fills.
- For G1 paired forecast failure and G2 risk result, no live capital permitted. A portfolio risk overlay without predictive alpha cannot create an unbounded expectation of outperformance.
- Full daily ledgers + model exposure diagnostics to be saved with SHA256; GitHub Actions and signed source provenance retained.

Freeze strategy parameters and source digests now; run Actions after code/tests are committed. Comparators must all have equal day count and exposure-matched comparisons; R0 full economic parity is mandatory.
