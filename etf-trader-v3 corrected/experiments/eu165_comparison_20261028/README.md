# EU165 six-cluster model-reconstruction and robustness study — 2026-10-28

**Exploratory only. No production changes; original B0, USA149, V2 and V3 untouched.**

Source panel: EU165 corrected archived research ZIP, 165 ISIN, 101 historically screened and equal-count six-cluster cohorts (24–42 ETFs), 3,024 ETF-month candidate records. Backtest common 2021-02-01 through 2026-07-01 with monthly next-open execution on frozen B0 calendar and 10bp one-way transaction cost. Source zip SHA256 EU165: recorded in `MANIFEST.json` within the separate attached artifact. Dataset EU165 panel originally created from EU155+10 global UCITS. No future prices enter signal features, 21-session targets enter expanding annual fits only after maturity.

**Important**: Neither exact ETF Trader V2 nor ETF Trader V3 was executed end-to-end on EU165. The `V2_CORE_PROXY` is a 15-feature ExtraTrees120/XGB160 approximation; the `V3_RANKER_PROXY` is a 15-feature LightGBM LambdaRank63 approximation, **not** the original XGBRanker127x3seed + Tail/Risk/500 baskets. Do not interpret proxy underperformance as a result for the actual production models. Native source-faithful replay is PENDING, not completed.

Results EUR CAGR / max DD / Sharpe rf0:
- B0 original frozen EU155 (2021-26 only): **17.18% / -28.34% / 0.892**.
- SXR8 passive S&P 500 UCITS: 16.28% / -25.01% / 1.009.
- MOM252 global-minimum-one/European-four, capped by ex ante vol15: 15.23% / -18.91% / 0.934.
- MOM252 global-minimum-one/European-four: 15.15% / -19.85% / 0.925.
- MOM252 Top5 with trailing correlation guard: 14.00% / -20.02% / 0.876.
- MOM252 Europe-only Top5: 12.84% / -22.48% / 0.837.
- MOM252 free Top5 in EU165 six-cluster cohort: 12.27% / -20.18% / 0.769.
- Equal-weight 24 instruments (4 per cluster): 8.71% / -23.67% / 0.735.
- V2_CORE_PROXY 1 per cluster: 8.67% / -28.51% / 0.636.
- V3_RANKER_PROXY 1 per cluster: 6.32% / -29.63% / 0.504.
- Ridge21 1 per cluster: 9.13% / -23.29% / 0.689.
- Low-vol 1 per cluster: 6.43% / -16.99% / 0.667.
- Downside-risk 1 per cluster: 6.54% / -18.54% / 0.666.
- Reversal21 1 per cluster: 2.65% / -24.30% / 0.256.

Paired circular six-month time-block bootstrap: global-minimum-one vs Europe-only, annualized log improvement +2.09 percentage points, nominal 95% CI [-0.93,+4.79] pp; corrguard vs ordinary Top5 +1.55pp, CI [-0.56,+3.88] pp. No improvement demonstrated with confidence, especially after research multiple testing. B0 retains superior historical CAGR. One ETF per cluster **in the invested portfolio** can materially impair returns; equal counts are better interpreted as a **candidate-universe coverage gate**, not capital-allocation constraint.

Data risk: 2026 survivor cohort (not all delisted ETFs), total return/distributions not independently reconciled, historical spreads/market maker executions not certified, global price coverage stops 2026-07-01; all candidate outputs are non-virgin research. Without point-in-time ETF holdings and fundamental exposure, the European value/quality/profitability-revisions papers from Deep Research cannot be honestly backtested here.

**Full Python source, complete daily NAV series, monthly holdings, annual fit audits, cost ledger, block bootstrap and validation logs** are bundled in conversation file `EU165_CONFRONTO_V2_V3_PROXY_DEEPSEARCH_20261028.zip`, SHA256 `1038d5a99fd6cb1f30c98daa3fa298ce1120688634ad6825202c29502385171f`. This GitHub branch is provenance/scorecard only, it is **not** a full source upload.

Next gate: port original V2 500-basket 24-ETF six-cluster Hybrid24 fullstack and exact corrected V3 full DAG from `fullstack_legacy`/corrected source into EU165, freeze distinct *new* basket hash, reconcile original engine, then run exact same costed setup and 2026+ untouched holdout. Preserve original V2/V3 and USA149.
