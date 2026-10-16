# Preregistered 2x2 factorial — 125-feature XGBRanker preparation versus training support

Research-only branch `research/xgb125-factorial-20261017` at `AM1975MA/Test`. No changes to production. Frozen Original149 (three dependent Yahoo revisions), 2017–2026 expanding annual folds. No download of new prices and no rerun of archived BASE or XGB125_MATCHED, other than replay parity controls.

## Question
Why did archived XGB125_MATCHED show mean CAGR 34.46% compared to BASE 31.76% when both used 125 features and the original fixed XGBRanker? Which difference matters: dropping the last 10% mature historical dates with a purge (full vs subtrain), or imputing/scaling the input (native missing vs median-imputed standardized)?

## Four fixed cells
- **A BASE**: full mature annual cohort; canonical raw 125 inputs with missing NaNs; original archive `predictive-BASE`, full V2 unchanged.
- **B XGB_FULL_PREP**: full mature annual cohort, median imputation and standard scaler learned from that cohort (never from future test), canonical original XGB worker.
- **C XGB_REDUCED_NATIVE**: exactly the mature subtrain of the archived annual LINEAR125 (final 10% of historical signals excluded and earlier labels purged); canonical raw 125 inputs with NaN, original XGB worker.
- **D XGB125_MATCHED**: exactly the same mature subtrain as C, median imputation plus standard scaler learned on that subtrain; immutable artifact from PR83 and run `38974661195`.

Fixed XGB params directly from unchanged kernel `COMPACT_PARAMS`: `rank:pairwise`, 360 rounds, max_depth4, eta.035, subsample.85, colsample.8, min_child_weight8, L1 .1, L2 8, hist, seeds [101,202,303], 1 thread per worker. Exactly same annual native eligibility >=30/125 originally present features, target `round(100*target_rank_21)`, query/group by signal_date, and month dates. No newer data, predictor, or portfolio-risk modifications. No PLS or feature changes in any cell. B and C are the only newly fitted candidates (2*10*3*3 = 180 seed fits).

Normalization of non-missing continuous data is theoretically immaterial for strictly monotonic splits, but `hist` numerical behavior might differ. This factorial explicitly treats imputation+scaling as **one preprocessing bundle**, and cannot isolate their individual causal effects; a later scaling-only/median-only experiment would be required to do so.

## Tests
- SHA identities of original TI parquets, trained subtrain split, baseline and previous matched, package numerical environment, trained states and all output predictions.
- Archived A and D exact native/common coverage; all B and C must have identical keys.
- Within each annual fold, full and subtrain both contain exclusively *mature* labels before the cutoff; all preprocessing estimated only on the applicable training portion; no observation is used in its own forecasting model before label maturity.
- Main standalone outcome: date-weighted realized percentile of rank-1 ETF; NDCG5; RankIC; consistency of Top1 across 3 correlated revisions; compare matched pairwise with exploratory 6- and 12-month moving-block bootstrap (not independent historical validation).
- Four-cell factorial contrasts: B−A preprocessing when full; D−C preprocessing when reduced; C−A reduction with native; D−B reduction with prepared; interaction (D−C)−(B−A).
- Execute exactly six new canonical portfolio V2 replays (B,C for 3 revisions) retaining BASE parity. Reuse D's 3 archived replays and the identical replay BASE control for A. Independently recalculate CAGR/MaxDD/Sharpe on original paths; also report annual returns including 2021 and 2023 and source Top1 disagreement. No tuning to improve these measurements.

All years have been repeatedly viewed during research; correlated Yahoo data are **not independent future evidence**. Retain unfavorable results; no automatically promoted model, no merge.
