# COMPACT21_CLEAN_DOWNVOL_TRAINING_V1 — frozen model diagnostic (2026-10-09)

## Provenance and sequence
The user requests source data quality correction **before** comparison of three consecutive Yahoo acquisitions. First-stage read-only source audit of original acquisition 1 was completed independently in GitHub Actions 37936052825, QA PASS, 114 dates, 16986 rows: `downvol21` 8195 legacy NaNs, `downvol63` 10807 and `downvol126` 12692, all attributable to an artificial minimum-negative-days threshold despite complete price histories, all zero after full-window semideviation, no change in original >=30 valid-feature eligibility. All six unit tests and canonical source gate passed. This preregistration predates **any** three-vintage training of cleaned features.

## Frozen input and sole source treatment
Use exactly frozen ORIGINAL149 three sequential raw acquisition folders from GitHub run 37121749852 and original TI_COMPACT panels from run 37150436612, with authoritative `FROZEN_TI` SHA256 values per acquisition. No new Yahoo downloads. For each acquisition independently:
- Validate raw original universe/uniqueness, positive coherent OHLCV and source raw CSV checksums; match original TI panel `downvol{21,63,126}` raw values/missing masks to direct original-feature reconstruction, fail closed.
- Replace the NINE `downvol21/63/126` raw, `_pct`, `_dev` features for **all** native data rows, using zero-target, full-window causal downside RMS of original log returns: `sqrt(252 * mean(min(r_i,0)^2, i=t-h+1...t))` for h in {21,63,126}. Require all h historical returns valid; zero negative returns yields exact 0, missing original prices/returns remain NaN; no forward fill, no use of any future bar.
- Recalculate `_pct` and `_dev` on the date's own 149-instrument cross-section; no cross-vintage data mixing, no cross-year learned imputation. Do NOT merely `fillna` because original and cleaned feature definitions are semantically different.
- Preserve all other 116/125 Compact21 feature values **exactly**, and all labels, ticker/date keys, raw files, maturity dates, original eligibility support, Compact63, Tail, MA3, macro and Stage19 rules. Preserve original 30-valid-feature training and inference **cohorts** even if the cleaned available-count would change; report any eligibility drift and stop (the original first snapshot showed no drift).

Frozen model: canonical Compact21 125 features, three XGB rank:pairwise seeds 101/202/303, 360 rounds, original labels `round(100*target_rank_21)`, year-by-year expanding causal fit with exit_date_21 strictly before fit year January 1, all unaltered model/hyperparameters and execution profile (Python3.13.15, XGBoost3.1.3, NumPy2.3.5, Haswell/AVX2, single thread).

## Repeated-data benchmark and audit
Validate exact original BASE reference prediction vectors (run 37229180477), original cohort/yearly input/labels, and original BASE source hashes. Prepare each new cleaned panel once with raw source parity proof and sha256; do not leak source vintage 2 into train of vintages 1 or 3.

For every 2017–2026 annual model fit, train on each vintage's own cleaned eligible mature rows; test natively on own cleaned inference and for common-input sensitivity against a fixed cleaned Repeat2 inference cohort. Independently refit each year/vintage and require prediction byte-exactness and training-input group/label fingerprint equality. Retain annual output vectors, complete panel sha256, numeric contracts, exact key cohorts, model audits, 2017–2026 coverage and all three pair comparisons.

Compare **same strategy model family** original BASE versus cleaned-data BASE on original corresponding native keys and original target/outcome vectors; on fixed source-specific support and all 114 month dates, compute pairwise common-input rank MAD, native Top1 disagreement, Top5 overlap, stability Spearman. Quality measured on 113 mature monthly dates: mean realized selected Top1 percentile (primary), Precision@5, NDCG@5, by vintage/date and per-year paired differences; uncertainty via exactly original `compact21_predictive_v2.metrics.paired_compare`, calendar 3-month blocks, 20000 resamples, seed 20261004.

## Fixed stage gates, NO post-hoc tuning
Use earlier BLOCKBAG 25%-reduction pilot stability and 95%-quality preservation criteria without tuning:
- **STABILITY_PILOT_PASS**: common Rank-MAD at least 25% smaller and native Top1 disagreement at least 25% smaller, neither metric worse for any acquisition pair, and unchanged original strict validation.
- **QUALITY_CONSERVATION_PASS**: mean Top1 realized percentile >=95% original BASE, individually >=95% for each acquisition; overall Precision@5 >=95% BASE; one-sided 95% three-calendar-month bootstrap lower bound of selected Top1 difference > minus 5% original BASE.
- Near repeatability: each native pair Top1 disagreement <=5%, common pair Rank-MAD <=10% of BASE.
No marginal or mixed gate passes. Report all failures and no premature promotion.

**Only if pilot stability AND predictive preservation both pass** shall a later frozen **full raw portfolio replay** be authorized with the exact same features and all original downstream stages/risk/transaction costs; compare three download CAGR/MaxDD/Sharpe/turnover and daily Top1 disagreement to identical environment BASE. Economic gates preregistered: mean CAGR >=95% BASE; CAGR span <=75% original; daily Top1 disagreement no worse, MaxDD no >2 percentage points worse, turnover <=110% original; semantic MA3 and source parity mandatory. No trading CAGR is claimed from monthly rank diagnostics.

Research-only Test branch and draft PR; no production adoption, no mutation to Etf_trader. Even passing original149 history cannot substitute for genuinely independent prospective holdout.
