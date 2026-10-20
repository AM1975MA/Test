# Preregistration — 5-session risk-relative outcome distribution, Original149, 2026-10-20

**Purpose**: attempt to falsify the hypothesis that TCN trained on a relative *risk-normalized* realized future outcome distribution selects better weekly ETF portfolios than the 2026-10-20 matched historical Pointwise / Listwise models and simple volatility or momentum controls.

**Repository containment**: standalone research branch research/original149-tcn-riskrelative-20261020. Original149 OHLCV and manifest SHA untouched. The previous Pointwise and Listwise branches and etf_trader production are not modified.

## Strictly frozen inputs, model and splits
Exactly the prior 149 US/global ETFs and exact daily 125 Compact21 features; frozen TinyTCN(30×125) with 24 channels, dropout 0.35, AdamW lr 0.001 weight_decay .003, 5 epochs maximum, 2-epoch early stop using only prior annual validation, deterministic seed 20261020. At date t signal close, earliest tradable entry Open(t+1), five-session exit Open(t+6). Fixed 5-session anchors. Training labels must mature before Jan 1 (Y−1), validation labels before Jan 1 (Y); training with grouped cross-sectional date ListNet softmax targets, groups of 4 dates per gradient step. Each fold's scaler uses only features strictly before Jan 1 (Y−1). OOS years 2017–2026, last signal ≤2026-06-30, last realized exit ≤2026-07-01. Per week Top5 long equally-weighted with 10bp each entry and exit, no change in trading policy. Sample of 476 weeks if complete, 100 in diagnostic pilot 2024–2025.

## Risk and forward relative-return targets
Forward market proxy is the **same-five-trading-session adjusted SPY return**, r_SPY(t)=Open_SPY(t+6)/Open_SPY(t+1)-1, a maturity-gated outcome, NEVER a live feature. ETF future return r_i defined identically. At close t, annualized vol63_i(t) and beta_mkt63_i(t) are native canonical features (from prices known ≤t), sigma5=max(0.01, vol63_i(t)×sqrt(5/252)), beta clipped [-1.5,3]. If volatility missing, replace using median available t across ETFs or 20% annualized if none; beta missing becomes 1.0. Missingness counts audited.

*RAW_EXCESS_DIST*: future excess r_i−r_SPY; controls for choosing a distribution objective rather than rank alone; subtracting a constant alone leaves cross-sectional ranking invariant.
*VOL_EXCESS_DIST*: (r_i−r_SPY)/sigma5_i; tests risk-normalization without beta adjustment.
*BETA_VOL_RESID_DIST*: (r_i−beta_i(t)·r_SPY)/sigma5_i; tests beta-neutral risk-normalization. This is a forward benchmark-relative beta residual **target**; it is NOT market-neutral portfolio construction.

For each matured training/validation signal date, use only as-of-eligible ETFs with observed matured labels, center values by the date's median and divide by max(q90−q10, 0.01 for raw, 0.1 for scaled), clip result to [−3,3]. Convert to probability distribution p_i=softmax(3.5 z_i); train TCN cross-sectional scores with −Σ p_i log_softmax(score_i) over all eligible names. No future normalization is used as an inference feature. No ex-post random parameter search or CAGR-guided weight tuning.

## Frozen negative controls, same weekly anchors and eligible roster
1. As-of raw 21d momentum (MOM21).
2. As-of beta-unadjusted risk-scaled relative past21d momentum (mom21_i−mom21_SPY)/(vol63_i×sqrt(21/252)).
3. As-of beta-adjusted risk-scaled past21d momentum (mom21_i−beta_i·mom21_SPY)/(vol63_i×sqrt(21/252)).
4. As-of highest vol63.
5. As-of lowest vol63.
Prior frozen TCN Pointwise, RIDGE125, ListNet, ListMLE@5, ListNet hybrid, and risk-only VOL21 / VOL63 are external anchor comparators; do not retrain those models to choose a winner.

## Primary decision metrics and causal negatives
Net CAGR, MaxDD, Sharpe, daily equity curve, year/regime breakdowns, mean date-equal Spearman RankIC on **raw future returns**, actual top5 raw-return overlap, mean top5 nominal forward returns, actual top5 **risk-relative oracle** overlap, average selected beta and volatility, average nominal return above SPY and beta-relative excess above SPY (training targets not fed at inference), support matched weekly decision dates. Full 2017–2026 economic results, and no worse MaxDD, matter more than the diagnostic 2024–2025 pilot. Positive hit-rate to risk-adjusted oracle ALONE never establishes realized tradable alpha.

Known limitations: no independent dataset, ETF survivorship and selection biases, shorting/hedging absent, approximate historical trading costs, Yahoo adjusted open availability, one-period realized beta proxy imperfect, high multiplicity risk.
