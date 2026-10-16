# Preregistered research: frozen PLS feature extraction -> canonical XGBRanker

Scope: AM1975MA/Test branch research/compact21-pls-xgbranker-20261017 only. No production changes or new Yahoo downloads. Existing Original149 three correlated source revisions, annual expanding fits 2017–2026, source-only kernel unchanged, 125 feature columns unchanged.

## Fixed hypotheses
The prior supervised PLS12 and coherence-PLS12 showed mixed results with a linear ListNet head. Test whether the original nonlinear XGBRanker can exploit these representations better than a matched 125-feature XGBRanker. Three fixed arms:
- `XGB125_MATCHED`: all 125 canonical columns, median-imputed and standardized on the same frozen LINEAR125 subtrain, not the full-history BASE recipe. Matched input support, data split and preprocessing control.
- `XGB_PLS12`: training-only (12-feature) PLS projected standardized inputs; target for the projection = mature decile ranking; no feature-coherence shrink.
- `XGB_PLS12_COHERENCE`: identical 12-component PLS projection after the frozen six-calendar-month-block feature-coherence shrinkage method from PR81. Do not fit feature projection or scalers on held-out validation or inference.

Common XGBRanker is exact kernel COMPACT_PARAMS rank:pairwise, 360 boosting rounds, max_depth4, eta0.035, seeds [101,202,303], original worker, no hyperparameter optimization or early stopping. Labels for XGB are round(100*target_rank_21), as in BASE. Subtraining dates, label maturity/purge and median/scaling state must match immutable LINEAR125 checkpoints from run38580178650, including intentionally excluding 10% validation; consequently BASE full-mature XGB and matched XGB differ in training support/preprocessing, and both must be displayed, never conflated.

This means two stages both see **only subtraining matured labels**; it is not a new independent test cohort. Same (year,source) basis is used for training and forecasting future dates. All subsequent risk, Tail, Macro, MA3 and execution rules unchanged. No opportunity router.

## Deterministic procedure and audit
- 10 annual years x 3 frozen sources x 3 arms x 3 seeds = 270 newly trained ranker models. Record exact subtraining / validation fingerprints, preprocessing state hashes, PLS basis and weights, per-seed score hashes, native and common coverage; repeat seeds under frozen numerical environment.
- Compare each candidate to XGB125_MATCHED on exactly the same native and common keys. Separate reference metrics for archived full-history BASE and annual LINEAR125.
- Primary standalone endpoints: future matured 21-session Top1 percentile, NDCG5, RankIC (averaged by date after source averaging). Stability endpoints: Top1/Top2 disagreement on common dates; paired 6- and 12-calendar-month exploratory bootstrap, 1000 samples, no overclaim of significance.
- **Always replay all three arms** with canonical cached full V2, identical input/execution/calendar and baseline parity. Report each 2017–2026 year incl.2021/2023, 3-source CAGR/MaxDD/Sharpe and turnover, daily final leader disagreement, and explicit economic tradeoffs.
- Immutable sources require hash-match; any missing/ambiguous file, leakage, score alignment problem, or replay parity failure stops the run. No automatic adoption, branch merge, or choice of best new model by repeatedly inspecting outer period.
- Frozen three acquisitions are correlated histories, 2017–2026 repeatedly used to develop models; all empirical inference is exploratory and must face prospective unseen data before production.

A future 125+12 concatenated nonlinear model is outside the present experiment: it would alter input dimensionality and be a separately registered test.
