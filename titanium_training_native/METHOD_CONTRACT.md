# Titanium Training-Native Canonical Contract

## Runtime dependency principle
No historical trained model, pickle, joblib or NPZ is required for signal generation.
All annual models are fitted from point-in-time OHLCV-derived panels. Model caches are optional outputs only.

## Calendar and labels
- signal_date: final trading session of each calendar month.
- entry_date: first trading session after signal_date, using adjusted Open.
- Compact exit_date: first trading session after the next month's signal_date.
- Compact label: cross-sectional percentile rank of open-to-open return entry_date -> exit_date.
- Compact fit row is eligible iff signal_date < Jan-1 cutoff AND exit_date < cutoff.
- 21/42/63-session forward labels are separate labels and must never replace the Compact monthly label.
- TailMix y_tailmix = 0.60*rank21^4 + 0.25*rank42^4 + 0.15*rank63^4.
- TailMix fit row eligible iff exit_date_63 < cutoff.
- Opportunity fit row eligible iff label_exit_date_21 < cutoff.

## Compact
XGBRanker objective=rank:pairwise, eval_metric=ndcg@3,
n_estimators=360,max_depth=4,learning_rate=.035,subsample=.85,
colsample_bytree=.80,min_child_weight=8,reg_lambda=8,reg_alpha=.1,
tree_method=hist. Seeds 101,202,303.
Group = signal_date.
Relevance = round(target_rank_pct * 100).
For prediction: percentile rank each seed within signal_date, then arithmetic mean of the three ranks.
Never average raw seed predictions before ranking.

## TailMix
Median imputer -> StandardScaler -> Ridge(alpha=30).
Output percentile-ranked cross-sectionally within signal_date.

## Titanium score
pre_macro = .70*compact_rank + .30*tail_rank.
Macro: 27 BASE_FEATS aggregated by macro category; median imputer -> scaler -> Ridge(alpha=50).
The canonical implementation must preserve an explicit maturity date for the 63-session macro label.
Live parity branch tests the July-27 code gate: bonus +.15 iff category==top_macro, macro_gap_z>=.75 and pre_macro>=.80.
Research archaeology branch may test tail_rank>=.80 separately but may not silently replace live parity.
TIT_R = percentile rank of final score within signal_date.

## Concentration
Within each basket, top1/top2 by TIT_R.
margin = TIT_R(top1)-TIT_R(top2).
margin >= .12 -> 100% top1; else 75% top1 / 25% top2.

## S3B
C05 defensive is fixed cluster 0. Remaining eligible risk tickers form 7 balanced dynamic clusters.
Use trailing 252-session returns only as of signal_date, PCA factor-loadings embedding,
balanced assignment and causal alignment to the immediately previous month by Hungarian overlap matching.
No future membership and no global/full-history label alignment.
Eligibility is point-in-time.

## Opportunity 3.0
Annual expanding fit, strict 21-session label maturity.
Models: target_top2 ExtraTrees D4 leaf30; target_spread Ridge100;
target_excess_max Ridge100; target_explosive RandomForest D3 leaf30.
Deployment parity uses predicted target_excess_max to rank clusters and z-score the cluster opportunity.
Direct candidate only if Titanium margin<.12, top1 belongs to best opportunity cluster and opportunity z-gap>=.50.
Router activates direct candidate only from trailing matured shadow excess, with no contemporaneous/future target leakage.

## Execution
D+1 adjusted open. One-way cost=.001. Turnover=.5*sum_ticker(abs(new_notional_weight-old_notional_weight)).
Systemic governor and stops are evaluated with the recovered exact daily simulator; tickers are matched by identity, never rank slot.

## Validation periods
D1: 2017-2019. D2: 2020-2022. DEV: 2017-2022. HOLD: 2023+. FULL: 2017+.

## Hard validation gates
1. No leakage audit passes for every annual model.
2. Compact target test proves monthly open-to-open semantics.
3. Seed aggregation test proves rank-each-then-mean.
4. S3B causality and point-in-time eligibility tests pass.
5. 2026-06-30 checkpoint should recover USO/PALL before calling historical parity.
6. 500-basket D1/D2/DEV/HOLD/FULL scorecards are compared to frozen references.
7. Unrestricted 150-ETF result is reported separately and never substituted for the 500-basket frozen baseline.
