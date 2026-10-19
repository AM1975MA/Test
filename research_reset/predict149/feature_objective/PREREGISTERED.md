# T149-D — predictor-specific feature/source and objective ablations
Date: 2026-10-19. This is POST-SELECTION exploratory research on the **same repeatedly-mined** historical original 149 US ETFs. This file is frozen before the new experiment. Outcome can NEVER be called independent predictive validation or evidence of real 30%-CAGR investability.

## One central research question
Do new as-of representations and **explicit learning-to-rank** losses improve identification of best **future 21-session** ETF tickers beyond archived N4 (HGB future-top15 classifier)? Compare DISTINCT approaches on the identical 64 existing 2021–2026 anchors without retuning after seeing the answers.

## Fixed models before test (six heads including reference)
- B0_ARCHIVED_N4_TOP15: immutable successful previous 149 HGBClassifier predictions from `research_reset/predict149/results/ALL149_FROZEN_PREQUENTIAL_PREDICTIONS.csv`; DO NOT retrain or alter.
- D1_RAW63_LGBM_TOP15: 63 raw daily **log Close/Close returns**, oldest→newest (a real raw-signal-window control, no engineered indicators) + six fixed category one-hots; LightGBM binary classification of next21 Top15.
- D2_ENG25_LGBM_TOP15: original N4's 19 engineered numerical features and six one-hot category indicators, unchanged signals and labels; LightGBM binary classifier.
- D3_CONTEXT_LGBM_TOP15: D2 plus **as-of cross-sectional percentile** ranks for r5,r21,r63,r126,v21,v63,v126,down63,beta126,res21,res63,draw63,volshock,accel,trendrisk; 15 extra ranks, *only* current signal data from 149 past historical closes.
- D4_LAMBDARANK_GRADED: D3 as-of features, LightGBM LambdaRank objective and group size 149 for every matured date. Fixed relevance `3` for top 5 future raw returns, `2` for next 10, `1` next 15, `0` other 119. This **directly optimizes sorted future best ETF names**, unlike regression of future returns. No calibrated probability claim for its rank score.
- D5_SIGNED_TAIL_LGBM: same D3 source/features and binary LightGBM independently trained on future Top15 and future Bottom15, score P(top15)-P(bottom15); tests directional selectivity of predicted extremes rather than glorified high-volatility selection.

Models D1/D2/D3 and both D5 heads: `LGBMClassifier(n_estimators=75, learning_rate=.05, num_leaves=9, max_depth=4, min_child_samples=90, reg_lambda=20, random_state=20261019, n_jobs=1, verbosity=-1)`. D4: `LGBMRanker(objective="lambdarank", n_estimators=75, learning_rate=.05, num_leaves=9, max_depth=4,min_child_samples=90,reg_lambda=20,label_gain=[0,1,3,7],random_state=20261019,n_jobs=1,verbosity=-1)`. **Quarterly refit** (first test anchor + every 3 anchors), train only anchors with full 21-session outcome exit **strictly before previous signal Close**. No early-stopping on evaluation period, tuning of loss, ranks, seeds or horizon; no aggregate normalization through future.

**No leaking even with reused data:** 149 SHA-verified original Yahoo adjusted prices, fixed `oasis149.canonical.load_149`; only past 63 logreturns and as-of ranks. Strict future-data mutation tests. All future outcomes used only as training labels after maturity. Baseline frozen N4 identity/capital equity parity must match previous stored predictor.

## Measures and rejection
Evaluate identical 64 anchors, 149 predictions each = **9,536** ticker-month predictions:
- Mean per-anchor Spearman vs next21 excess over 60/40, 95% circular 3-anchor block CI of *incremental Spearman against B0*; average Precision@10 future Top15, future best absolute winner in chosen top5, precision Top5, graded NDCG@10; Brier and logloss for probability heads (B0, D1, D2, D3, D5 heads) vs fixed uniform 15/149.
- **Primary scientific skill gate:** positive CI lower bound of paired mean Spearman uplift vs archived N4 AND Precision@10 > baseline N4 AND improvement in both 2021–23 and 2024–26. Also require Top5 false-positive bottom15 rate < baseline.
- Secondary shadow economic probe: top5 each anchor equal dollar weights, next Open, exact 10bp per-side self-financing buying/rebalancing, daily open MaxDD, 21d CAGR, ES5, Sharpe, turnover and fee; 60/40 proxy for opportunity cost, *not a performance-optimization objective*.
- Report class concentration/average as-of selected volatility, event Top15 probabilities proper scoring and credit for covariances. Do not overclaim that high best-ticker precision is monetizable if left tail, cost, factor/maturity or liquidity invalid.
- Multiple comparisons: up to five new candidates, data already mined and selected; no 'scientifically proven' alpha even if the primary gate passes. A winning model must be frozen for a **future point-in-time dataset and never retuned there**. 30% CAGR aspiration is not selection cutoff in this run.
- All unsuccessful models archived with code, source roster hash, per-ticker predictions and per-anchor metrics; production `etf_trader` remains untouched.

Risk warning: the dataset is a retrospectively selected US ETF set, may contain leveraged funds, historic adjusted Open prices not broker-executable, no EUR FX, taxes, bid-ask spreads, inception/delisting PIT. Even a high backtest CAGR on this corpus is only exploratory.
