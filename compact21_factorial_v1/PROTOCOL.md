# COMPACT21: factorial diagnosis before new fits

This is a diagnosis protocol, not a parameter search or an adoption decision.
Created after the predictive V2 recipes were frozen and before inspecting any
new candidate outcome. Preparation reads mature training data only and never
fits a predictor or calculates new predictive/economic outcomes.

## Immutable scope

Use frozen TI_COMPACT panels from run 37150436612, repeats 1/2/3. Record file
SHA256 and source/runtime identities. Preserve all annual cutoffs 2017â€“2026,
strict signal_date < Jan1 and exit_date_21 < Jan1, native canonical eligibility
(>=30 nonmissing canonical features), sorting and unique signal_date,ticker.
No future rows enter drift scales, label comparisons or transform fitting.
Use the already frozen BASE, RIDGE, LGBM_LAMBDARANK and ADDITIVE_RIDGE recipes.
No new objective, regularization, seed, spline or ensemble weights are proposed.
Feedback, Compact63/Tail, inference keys and the strategy remain unchanged.

## Identified training interventions

For each year and pair A/B, align native mature training by exact keys. On their
intersection C build four fits, with identical ordered keys and a fixed Repeat2
inference frame:

| Cell | Feature matrix | Target | Cohort |
| --- | --- | --- | --- |
| AA | A | A | C |
| BA | B | A | C |
| AB | A | B | C |
| BB | B | B | C |

Integer relevance is canonical round(percentile*100) for BASE/LightGBM;
continuous percentile remains the frozen Ridge/additive target. Feature and
label transfers align by keys, never by incidental row position. Every donor
row passes the annual maturity gate independently. Fit each transform within
its cell; a change in fitted imputation/scaling/spline knots is part of the
feature-training intervention, not an inference change.

Also compare each native fit to its same-vintage intersection fit. This measures
the effect of removing that vintage's exclusive rows, conditional on its own X/y.
If native keysets equal C, membership has no intervention and this effect is
exactly zero. A complete 2x2x2 design is NOT identified when exclusive rows lack
counterfactual X/y in another vintage. Do not invent those values or claim a
pure additive cohort attribution. Report unsupported cells as unavailable.

Common Repeat2 inference is itself aligned across all three vintages within each
annual fold, sorted by keys. It is passed without labels to the predictor.
This distinguishes training effects from inference effects. Native inference
can be evaluated subsequently as the already frozen secondary diagnostic.

## Preparation evidence

Save input hashes, sorted training/common/inference identities and source-row
indices, continuous and canonical integer training labels, missing/inf masks,
matrix hashes, cohort exclusives, label changes and relation/tie transitions.
Check duplicate keys, identical feature rows within each query, constant and
allmissing features, identical feature columns and high pairwise correlations.
Report feature drift per feature in native units and normalized by the mature
reference-A IQR; zero IQR is unavailable, never replaced with a future scale.
The >=.95 correlation threshold is descriptive and does not select features.
These are drift diagnostics, not new predictions or estimates of a vendor's
noise distribution. Keep all outcomes of later fits, including failures.

The script stores source-row indices and identities rather than duplicating
every full matrix. A future executor must verify source SHA256, reconstruct
matrices from those indices and check saved hashes BEFORE fitting. No executor
or financial fit is run by the preparation script.

## Later attribution, after authorized execution

Retain prediction arrays for all cells and independent same-cell exact refits.
Compare date-normalized ranking vectors, common Top1 changes, Top5 Jaccard and
rank MAD. For ranking vectors r, signed feature contribution is
0.5*((rBA-rAA)+(rBB-rAB)); signed label contribution is
0.5*((rAB-rAA)+(rBB-rBA)). Their sum equals rBB-rAA exactly. Also retain interaction
rBB-rBA-rAB+rAA. These identify algorithm responses to the constructed frozen
training interventions, not economic causal effects or future generalization.

Do not add nonnegative MAD values as if they were signed contributions, assign
percent shares when effects cancel, or attribute a Top1 switch to a single
factor merely because its individual intervention also switches Top1. Inspect
margins and interaction cases. Report both directions and each fold/pair, not
only means. Realized outcomes must use the already frozen evaluation protocol.

Interpretation and next correction remain conditional: dominant feature effects
support smoother/regularized sensitivity or representation work; dominant label
effects support a separately preregistered mature-target robustness experiment;
membership effects support auditing eligibility boundaries. Large interactions
require joint diagnosis. No new target, clipping, feature removal or feedback
change is authorized by this protocol. No attribution result is available until
the prescribed fits have actually been executed.

## Execution registry, frozen 2026-10-05

Evaluate 480 model/year/pair/cell observations through all nine unique X/y vintage combinations per model/year (360 distinct fits). Each distinct fit has a second independent exact refit (720 fit calls). Identical diagonal cells reused across pairs retain the same prediction vector; they are not counted as independent evidence. Three diagonal controls per model/year must match original run37229180477 common prediction arrays byte-for-byte. The 40 model/year jobs use the original pinned numerical profile and compare actual compiled dispatch targets. All yearly cohorts are expected equal as proved by preparation; any new mismatch fails rather than inventing counterfactual data.

Quality is conditional on frozen Repeat2 outcomes for every cell, with the V2 maturity/metric protocol; comparisons here diagnose training perturbations and do not requalify failed recipes for adoption. Summaries weight tickers within dates, then dates within each year, then all dates equally across years and the three snapshot pairs equally. Retain signed X/y effects, interaction, every contrast and cancellation measures; no nonnegative-MAD percentage decomposition. No deployment or negative-feedback change.
