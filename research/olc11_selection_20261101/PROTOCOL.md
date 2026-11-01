# OLC11 — task-native selection objectives

2026-11-01. Continue from OLC10 commit707fd7f4b09e7b71d5140b4143c6dd0cf9e0477a. Research branch only, no main/live changes. The user requires every improvement in USA149 and EU165 and layer-native evaluation, not CAGR as the learning criterion. Existing RSI/schema/alias/checkpoint contracts stay integrated.

## Question
With identical Hybrid42 inputs, do learning objectives targeted at the upper opportunity set select better than estimating the mean native target? Native Y=.45*rank21^1.5+.35*rank42^1.5+.20*rank63^1.5. This is relative future strength, not a probability or a direct return forecast.

## Immutable controls and sample
Use authenticated OLC09 annual REF42 matrices and OLC10 raw forecast/label CSVs. No new downloads/features/portfolio changes. Reproduce original ET/XGB predictions for2022 in both markets before interventions. Original annual training dates, rows and input values are reconstructed from labels and must match saved key and array hashes.

Top-quintile labels require a fully observed monthly comparison set. For all NEW arms, retain only entire native monthly cohorts whose TARGET and exit63 are complete and whose maximum exit63 is strictly before January1 of fit year. This may remove partially matured or incomplete months: fit a MATCHED_REG control on exactly the same rows, rather than crediting this sample change to a new loss. Keep the archived original regression as a distinct control. No future label availability alters prediction eligibility. Months with missing evaluation outcomes remain present in inference and are explicitly excluded only from complete-cohort diagnostics.

## Fixed model interventions
Train yearly2019..2026, both markets. Seeds101,211,307 fixed in advance; report each and average raw forecasts, never select a seed. Same original42 ordered columns, imputer fitted only on the annual training set. Same architecture/regularization/round counts as saved parent.
- MATCHED_REG: original ExtraTrees120 depth8 leaf20 max_features.4 plus XGB400 depth2 lr.02 min_child_weight12 lambda12 alpha.2 subsample.9 colsample.9 squared-error, with only the common cohort restriction changed.
- CLASS_TOP20: ExtraTreesClassifier with corresponding tree budget and default Gini, XGB binary:logistic; label=1 when average percentile rank of Y in the complete monthly cohort exceeds.8. No class weighting/oversampling, no threshold optimization. Both predict a model probability of the relative event, NOT an investment success probability; check Brier/log-loss/reliability against prior training prevalence.
- RANK_TOP: XGB rank:ndcg, linear gains, relevance=round(15*Y), topk pair construction with truncation4, eval ndcg@2; remaining parameter budget unchanged. Groups are monthly cohorts. Scores are rankings, NOT probabilities or E[Y].
These interventions change the learning objective/criterion and thus gradient/Hessian scales; unchanged regularization coefficients do not prove equal effective complexity.

Run each learner separately and blends: original .6ET percentile+.4XGB percentile; replace ET only, XGB only, both with classifiers, or XGB only with ranker. Primary multi-seed comparison averages each learner's raw scores then ranks, as predeclared; report seed dispersion. No new blend weight or search over target definitions.

## Evaluation and interpretation
Primary2021–2024 with all target63 outcomes matured before2025; show2025 and2026partial separately, plus all active. Pair each comparison on identical complete monthly support in both markets. Primary diagnostics: native-target NDCG@2 and Top2 precision in its upper quintile. Safeguards: native-target regret, bottom-quintile selection, Top5 capture, static actual forward excess payoff and regret at21/42/63 sessions. Ties use uniform expected membership, not a favorable ticker. Report native regression error separately; never compare a class probability to Y as if both estimated the same quantity.

Evaluate current Hybrid, original smoothing and frozen .475Return+.525Hybrid composition separately. Return125RSI forecasts stay fixed. This is layer/integration diagnostic, no new CAGR or portfolio simulation. Show loss of short-horizon opportunities even if persistence-target accuracy improves.

Equal month weight in reported metrics. Training retains original per-row weight for regression/classification; ranker operates on query groups, disclose distinction. Paired calendar-month circular bootstrap6000 draws, blocks3/6, seed20261101, same paired month indices for USA/EU. Report individual and within-family simultaneous intervals; zero inclusion is not rejection and positive bootstrap fraction is not a posterior probability. Three seeds are not independent markets. Reused history/model selection remain limitations.

## Tests and persistence
Verify parent digests before reading serialized arrays. Write tests for whole-cohort maturity, no future labels, tie-aware targets/metrics, alias order, query grouping, probability domain, schema mismatch and incomplete checkpoint rejection. Persist input subset, each annual batch and completed both-market family with hash before reporting it done. Independently recompute metrics and reopen models. Run future-perturbation tests for selection of training cohorts and inference. Original reference outputs unchanged. Sources/tests/compact outputs go to this research branch; full binary checkpoints to the authorized Library with SHA256 recorded. Library is not a GitHub release. No background work or full-market-data certification implied.

Expected upper bound:240 new matched objective models (5learners*3seeds*8years*2markets), plus4 original2022 parity refits. Counts reported only after actual verification. No time-event, group sampler or new economic data claimed.
