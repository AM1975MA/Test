# Compact21 Signal-Lockin: supervised feature extraction (preregistered exploratory test)

**Scope**: AM1975MA/Test only. Branch `research/compact21-signal-lockin-20261016`. No production edits, no Yahoo requests or replacement prices. 149 fixed ETFs; 3 correlated frozen Original149 sources; 2017–2026 annual expanding walk-forward. Raw OHLCV, official 125 features, eligibility, labels, 10% chronological validation (and purge), standardized subtrain-only preprocessing, ListNet decile objective, L2=0.001 relative-curvature convergence and solver unchanged. All other modules unchanged. Reuse hashes/model contract from run 38580178650. No Opportunity.

## Hypothesis and fixed arms

H0: Compressing 125 input features into supervised low-dimensional scores does not preserve out-of-sample Compact21 ranking quality or source stability versus archived annual LINEAR125.

1. `SIGNAL_PLS12`: exactly 12 PLSRegression components, learned on date-demeaned mature subtraining feature rows and the corresponding *within-date centered* decile labels; each date contributes equal total squared weight via 1/sqrt(n ETFs). No target leakage from validation/test. No tuning of component number.
2. `SIGNAL_PLS12_COHERENCE`: identical PLS and solver, before PLS scale each feature using training-only six-calendar-month-block signed Pearson IC. For each feature compute mean block IC mu and standard error se across historic six-month blocks; weight=clip(0.25 + 0.75*max(0,abs(mu)-2*se)/max(abs(mu),1e-12),0.25,1). No learned feature sign reversal. The fixed 0.25 floor prevents arbitrary hard feature deletion. Date IC and block weights are diagnostics, not tests of formal significance.

PLS rotations after weighting are QR-orthonormalized back into the original 125-dimensional feature geometry; ListNet learns in 12 coordinates with the same L2 on coordinate coefficients as PCA95. Inference uses the original 125-feature inputs and final w125; orthonormality/inference equivalence and independent projected gradient must pass.

## Evaluation and decision

Step 1: diagnostic IC table from 2026 *historically mature subtraining only*, one row per feature/source; no use of 2026 labels for feature weight determination.
Step 2: 60 complete fits (two fixed candidates × 10 annual folds × 3 sources), immutable feature panels and archived BASE/LINEAR. Save per-year subtrain key fingerprints, hash of preprocess/model/score, PLS bases, IC diagnostics and source quality outputs. Evaluate only mature future labels: percentile Top1, NDCG5, rankIC, per-date/annual, vintage disagreement Top1/Top2, especially years 2021 and 2023. Compare paired quality after averaging vintages within each date; no treating vintages as independent markets.
Step 3 (conditional): perform canonical portfolio replay on **both arms only if** they preserve at least 95% of LINEAR125 Top1 percentile and NDCG5, and exhibit <=LINEAR125 source Top1 disagreement. This fixed screening conserves replay resources, but is not a statistical proof. Save full paired CAGR/MaxDD/Sharpe/turnover on same execution and risk recipe, including per-download/year metrics, without promotion.

No choosing among arms by historical 2017–2026 CAGR. PCA95 negative control remains completed, not retrained; BASE and LINEAR reference results remain frozen. The 2017–2026 period is heavily reused for research; even if gates pass, results are *exploratory* and require prospective/unseen temporal validation before deployment. Low-variance, small-IC or coherent features are not proven causal; note multiple-comparison, correlated horizons/regimes and source revision limitations. Any failure must remain visible (do not silently switch to Ridge/alternate k). No automatic merge.
