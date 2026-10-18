# EUROPE60_STOCHASTIC_STATE_V1 — preregistered research experiment (18 Oct 2026)

## Question
Can a small physically interpretable probabilistic ETF return process beat the frozen 60-European-ETF Return-NDCG+MA3 Hybrid selector under **identical simple monthly top-2/50:50/open-open execution**? Production ETF_TRADER and Original149 untouched. Model created before seeing EUR60 results; do not tune after outputs.

## Inputs / causal contract
- Use only frozen EU120 daily OHLCV CSV committed under `data/eu120/raw_ticker_csv`; Europe-only60 roster and 2017–2026 monthly entry/exits copied from frozen audited EU60 oracle run 39084898663, calendar dates only. Reference EU60 scores come from run 39071370480; no raw data download, no reuse of their model predictions in NEW scores.
- Signals at historical last observed close on `signal_date`; invest at **next common open** and exit at following common open.
- No labels, realized return, future price, ex-post winner or validation performance may enter selection. Running research inherits hindsight-curated 2026-07-01 roster and lacks point-in-time tradability/verified quotation currencies, so it cannot certify a live trading advantage.
- 113 monthly periods, 60 tickers, common eligible top-two candidates; same 10bp *one-way* turnover cost as the historical simple comparator. Both existing model and new model are evaluated under that policy.
- No parameter search, metric-conditional routing or after-the-fact learner choosing. Three fixed candidate arms plus reference ranker and no-skill controls.

## Independent strategies (no XGB, no MA3 or Titanium)
1. `MOM_12_6_SKIP1`: equally weighted annual and 6-month momentum excluding newest 21 trading sessions; divided by ex-ante 126-day realized volatility. No supervised fit. Uses 252/126 session lookbacks.
2. `ROBUST_KALMAN`: robust latent local-monthly-drift state, Student-t(5) observation influence, Gaussian process transition. Two prespecified state-noise-to-observation variance ratios `1/36` and `1/9`, Bayesian model averaging by sequential Student-t predictive evidence. Monthly returns of the last 60 available observations, minimum 36; posterior uncertainty and realized monthly volatility enter risk-adjusted expected return score. No information after `signal_date`.
3. `HALF_RANK`: simple 50:50 cross-sectional percentile blend of the two independently computed score arms. Not fit to outcome.
4. `R_H_REFERENCE`: existing EUR60 annual refitted Return-NDCG + 42-feature Hybrid Tail predictions (the **score only**), same fixed Top2/economic path, no V2-specific risk weights.
5. Controls: equal-weight monthly 60 names where prices actually available, plus 1000 seeded random unconditioned monthly Top2 draws from the same tradable set.

## Outcome / integrity gates
- Commit the source code, preregistration, unit tests and Actions recipe to this research branch; do not merge/promote; preserve every old input.
- Synthetic lookahead test: modifying future Close must leave past signals identical. Stale signal date/entry-open order forbidden. Simpler momentum must not use forward labels.
- Independently replicate frozen R_H top2 CAGR `9.9780%` from original source predictions to numerical tolerance `1e-10` before publishing.
- Output every monthly position, gross realized returns, turnover, costs, cross-sectional quality and stability; no front-running month end. Report per arm annualized CAGR, monthly MaxDD, monthly Sharpe, turnover, median month return, chosen Top1 forward return, mean gap to ex-post leader, random-null percentile and a 12-month-block bootstrap paired log-return difference vs R_H. Report differences rather than p-hacking.
- Stochastic computations may require an ordinary finite-precision repair only if code tests fail; never optimize against test-period payoff.
- Rule for scientific conclusion: retrospective exploratory, *no independent prospective holdout exists*; no statement of statistically validated deployable alpha.

## Model limitation
Student-t posterior predictive weights are an explicitly robust **approximate** Bayesian filter, not an exact joint stochastic-volatility state-space posterior. Multiple lookback frequencies and ETF category overlap mean neither arms nor source vintages are independent tests. Random selection is a diagnostic baseline, not a substitute for broad market/index comparators.