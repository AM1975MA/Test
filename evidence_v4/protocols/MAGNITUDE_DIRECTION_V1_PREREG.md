# Evidence V4 — Magnitude retriever + 21d direction head v1

Status: **PREREGISTERED BEFORE DEV60 CONSTITUENTS OR PERFORMANCE ARE OBSERVED**

## Hypothesis

Evidence V3 showed that the frozen LTR architecture behaves primarily as a tail/magnitude detector: high scores strongly enrich both future winners and future losers, and correlate with absolute 21-day return but not reliably with return sign.

V4 therefore separates the tasks:

1. **Stage 1 — magnitude/tail retrieval:** exact frozen Evidence V1 LTR architecture.
2. **Stage 2 — direction:** a distinct causal binary classifier trained to predict whether the candidate's future 21-day return is positive.

No V4 result is used to select this architecture.

## New development data

The test will run only on the frozen Evidence V4 Dev60 universe after Phase A completes. Dev60 is constructed without performance criteria and is disjoint from Original149, Holdout70, tested EU110/EU120 and Dev72.

No network access is permitted during the model test.

## Canonical source panel

Rebuild the frozen MA3 source-only panel from Dev60 using the same canonical Evidence V1 builder/producer. Required columns include `FEATURES_42`, `target_relevance`, `fwd_ret_21`, `exit_date_21`, `exit_date_63`.

## Stage 1 — exact magnitude LTR

Identical Evidence V1 Retriever LTR v1:
- XGBRanker objective `rank:ndcg`
- n_estimators 400
- max_depth 2
- learning_rate 0.02
- subsample 0.90
- colsample_bytree 0.90
- min_child_weight 12
- reg_lambda 12.0
- reg_alpha 0.2
- tree_method `hist`
- random_state 101
- n_jobs 2
- lambdarank_pair_method `topk`
- lambdarank_num_pair_per_sample 10

Annual expanding fit. Training requires `signal_date < cutoff` and `exit_date_63 < cutoff`.

Generate OOS Stage-1 predictions beginning in 2011 whenever a maturity-safe training set exists. On each signal date, rank all available candidates by Stage-1 score descending, ticker ascending. Define `LTR_POSITION = 1 - (rank-1)/(n-1)`.

The **Stage-1 shortlist K is fixed at 10**. This is not swept. K=10 is inherited from the previously frozen LTR retrieval architecture and the V3 tail diagnosis.

## Stage 2 — causal direction head

Training data for year Y consists only of **historical Stage-1 OOS Top10 candidates** satisfying:
- `signal_date < Y-01-01`;
- `exit_date_21 < Y-01-01`;
- non-missing `fwd_ret_21`.

Thus the direction head never trains on in-sample Stage-1 shortlist membership.

Binary target:
- `SIGN21 = 1` iff `fwd_ret_21 > 0`;
- `SIGN21 = 0` iff `fwd_ret_21 <= 0`.

Direction features are exactly:
- frozen `FEATURES_42`;
- `LTR_POSITION` from the historical OOS Stage-1 prediction.

No macro, category, calendar, realized-volatility target engineering, future-return magnitude, alternate horizon or additional feature is permitted.

Direction classifier: XGBClassifier
- objective `binary:logistic`
- n_estimators 300
- max_depth 2
- learning_rate 0.02
- subsample 0.85
- colsample_bytree 0.75
- min_child_weight 20
- reg_lambda 20.0
- reg_alpha 1.0
- tree_method `hist`
- random_state 211
- n_jobs 2
- scale_pos_weight 1.0
- eval_metric `logloss`

These capacity/regularization choices inherit the frozen V1 classifier family where applicable; class weighting is neutral because the sign target is not structurally 1:9 imbalanced.

For each 2017-2026 signal date, apply the year-specific direction model to the current Stage-1 OOS Top10 candidates. **Select exactly one ETF: the candidate with highest predicted `P(SIGN21=1)`, ticker ascending as tie-break.** There is no probability threshold, cash rule, score blend or fallback.

## Evaluation window

Every signal date >= 2017-01-01 with:
- at least ten Stage-1 OOS candidates;
- valid `fwd_ret_21` for evaluation;
- a fitted direction head from historical mature OOS shortlist rows.

## Comparators

On exactly the same dates:
- Stage-1 global LTR Top1;
- Stage-1 Top10 equal-weight;
- Dev60 Universe-EW.

Also report the oracle best return inside Stage-1 Top10 as opportunity-set diagnostic only.

## Diagnostics

Report:
- Stage-1 Top10 global-winner capture and exact random expectation/enrichment;
- Stage-1 Top10 global-loser capture and enrichment;
- direction-head Top1 CAGR, vol, Sharpe-rf0, max drawdown, positive-period rate;
- direction Top1 exact global-winner count;
- direction-selected future positive-return rate;
- historical direction-head training class balance by year;
- full period and fixed subperiods 2017-2022 / 2023-2026.

No metric other than the primary gate may trigger a new Dev60 variant.

## Primary advancement gate

All four conditions must hold:
1. Stage-1 Top10 winner enrichment versus exact random expectation >= **2.0x**;
2. two-stage Direction Top1 full-window CAGR proxy > Dev60 Universe-EW full-window CAGR proxy;
3. two-stage Direction Top1 CAGR proxy > Universe-EW in **2017-2022**;
4. two-stage Direction Top1 CAGR proxy > Universe-EW in **2023-2026**.

The gate is intentionally economic and regime-robust. It does not require matching Original149/V3 hit counts.

## Decision rule

- **PASS:** freeze the exact two-stage architecture. Dev60 becomes burned. No V4 tuning is allowed. Next step is a newly frozen, disjoint Holdout-B and a one-shot transfer/promotion test.
- **FAIL:** reject this magnitude-plus-sign architecture on Dev60. Do not vary K, sign threshold, direction target, class weight, classifier hyperparameters, feature subset, blending, cash rule or horizon on Dev60.

This development test cannot itself support a promotion claim.