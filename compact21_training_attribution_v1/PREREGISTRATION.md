# COMPACT21_TRAINING_SOURCE_ATTRIBUTION_V1 — preregistration (2026-10-09)

## Decision and scope
Diagnose the cause of model disagreement among three sequential Yahoo Original149 acquisitions. Extend the four-year input/label perturbation forensic to all original annual 2017–2026 Compact21 folds, without changing trading logic or promoting a new model. This is a **diagnostic**, not a deployable single-vintage predictor; never use this test to claim improvement in CAGR.

## Frozen data and controls
Exactly the original three TI_COMPACT parquet panels from GitHub Actions run 37150436612 (raw acquisition 37121749852); original BASE vectors from run 37229180477. Use unchanged canonical BASE XGB (125 features, 360 rounds, three seeds, 1 thread), strict signal/exit maturity, 2017–2026 annual fits, signal <= 2026-06-30 and actual outcome maturity <= 2026-07-01. Freeze numeric profile from COMPACT21_PREDICTIVE_V2. Do not change feature eligibility, tickers, target construction, score averaging, portfolio rules or negative feedback.

For each fit year and each vintage v in {1,2,3}, require an exact (signal_date,ticker) match of original eligible mature TRAINING cohort to vintage 2. Never silently inner-join, forward-fill or drop nonmatching training rows. If any cohort, feature-column identity, training exit-maturity or numerical profile differs, mark **INVALID** and stop before fitting treatment. BASE controls must exactly reproduce retained common/native prediction bytes and original fit audits.

## Fixed 2×2 training-source factorial
Feature-source axis X∈{native_v, repeat2}; label-source axis Y∈{native_v, repeat2}. All predictions use the **same Repeat2 inference feature matrix** (plus unchanged native frames for BASE parity only).

- BASE_NATIVE_X_NATIVE_Y: frozen original BASE predictions; verified original controls, no new candidate fit
- OWN_X_R2_Y: original features from v, target_rank_21 and exit_date_21 from repeat2, refit same BASE XGB
- R2_X_OWN_Y: features from repeat2, original target_rank_21/exit_date_21 from v, refit same BASE XGB
- R2_X_R2_Y: exactly the validated repeat2 BASE prediction duplicated as an identity negative control, no new fit

The sample/target cohort must be common across vintages. Use only mature labels for each annual fit; same-date future labels are never input features. Copy label-side fwd_ret_21 when present strictly for self-consistent metadata (it is never used for fitting). Preserve all non-swapped fields and original query group sizes/order. Identical-source treatment for vintage2 must predict byte-exact to BASE repeat2. Refit each nontrivial treatment independently twice; require byte-exact predictions and training audit. The common-vintage arm is not live deployable; it exists to isolate variance pathways.

## Readouts, not candidate selection
Across all 114 scheduled monthly dates and each pair 1–2,1–3,2–3, report:
- common-input Rank-MAD, common-input Top1 disagreement and Spearman for BASE and each fixed treatment
- per-pair metrics and count, pooled year/date metrics, the relative change against BASE
- descriptive Repeat2-outcome NDCG@5 and realized Top1 percentiles (mature dates only), explicitly not an OOS model-quality proof
- training labels numerical mismatch counts, feature missing-mask mismatch counts and feature value mismatches by pair, on the exact matched annual input cohort
- source SHA, frozen input SHA, runtime profile, original BASE exact-byte parity, independent refit and maturity status

All three acquisitions are dependent re-downloads of one historical universe: do not treat them as independent temporal observations; do not sum factor contributions as if additive. Any treatment showing greater disagreement than BASE on any pair must be reported; no post-hoc exclusions.

## Interpretation and stopping rule
No configuration tuning, winner selection, soft thresholds, P&L, CAGR, Sharpe, MaxDD, turnover optimization or production modification. This diagnostic can only classify the training sensitivity mechanism:
- dominant label-associated variation, feature-associated variation, or nonseparable interaction / inconclusive
- with per-pair evidence and any asymmetry explicitly surfaced.
A subsequent **separate preregistered** robustness candidate may be devised only after this attribution audit; it must pass both predictive-quality and repeat-acquisition stability gates, then unchanged economic replay and independent holdout/future validation. Research is limited to GitHub repo Test, an isolated branch/PR; Etf_trader and production remain unchanged.
