# BASE_SEMIDEV — single frozen feature-representation trial

Registered 2026-10-05 before any BASE_SEMIDEV fit or predictive outcome. This is one new post-V2 development candidate, motivated by the already observed downvol missingness mechanism. It does not amend COMPACT21_PREDICTIVE_V2, reinterpret its failures, or create an untouched historical holdout. No fit or new outcome is performed by this registration.

## Question and fixed intervention

Test whether replacing three downside-feature definitions and their six canonical cross-sectional derivatives improves selected-ticker quality while reducing revision sensitivity. Keep the canonical BASE XGB learner, 125-column order, objective, rounded relevance labels, parameters, rounds and seeds 101/202/303. No additional candidate, target, regularization, feature removal, rounding, allocation or negative-feedback intervention is registered.

For each frozen vintage and h in {21,63,126}, define daily log returns exactly from its existing Close matrix:

    lr[t] = log(Close[t] where Close[t]>0) - log(Close[t-1] where Close[t-1]>0)
    q[t] = min(lr[t],0)^2 for finite lr[t]; otherwise missing
    minimum[h] = max(10,h//2)  # 10,31,63
    downvol_h[t] = sqrt(252) * sqrt(mean(q over the last h sessions))

The rolling mean counts ALL finite log returns toward minimum[h], including positive and zero returns whose q is zero. Missing or infinite observations remain missing and do not become zero. Do not remove nonnegative returns before rolling, center the negative subset, change the window, add an epsilon or retune coverage. A sufficiently covered window with no negative returns yields zero. Preserve the original annualization sqrt(252).

Snapshot at the canonical signal dates, then compute `_pct` using the original average-tie cross-sectional percentile function and `_dev` using the original median/MAD deviation function, including its existing factor1.4826, zero-MAD missingness and clipping[-8,8]. These are unchanged canonical definitions, not newly fitted transformations. Use the same complete 149-ticker candidate universe and its existing finite availability at each date BEFORE selecting native model rows; do not compute derivatives on a training intersection or only the eventual trading selection.

Only these nine Compact21 columns may differ from the original panel:

    downvol21, downvol63, downvol126,
    downvol21_pct, downvol63_pct, downvol126_pct,
    downvol21_dev, downvol63_dev, downvol126_dev

All remaining116 columns, keys, outcome targets and row order must be exactly preserved. Replacing nine columns changes their values and missing masks where the formula implies it; no other field or mask is authorized to change. The intervention is limited to Compact21 inputs. It must not modify the shared kernel's downside function globally, because Compact63/Tail/other components must remain canonical.

## Meaning and limitations of the mechanism

The old feature is annualized population standard deviation of the negative-return subset, with minimum coverage counting only negative observations. The new feature is an annualized lower partial second moment relative to zero over all finite returns. It removes the identified negative-count eligibility boundary, but also changes the economic meaning and weighting of downside risk. Therefore a favorable result would support this registered feature representation, not identify a pure isolated effect of eliminating NaNs.

The squared truncated-return map is continuous at a finite return crossing zero. That does not establish stability of the whole pipeline: price-data missingness and minimum finite-coverage boundaries remain; cross-sectional ranks can change around ties; zero-MAD deviations retain their canonical missingness; fitted tree decisions and downstream strategy paths can amplify small differences. No global numerical or investment robustness guarantee is claimed.

## Immutable evidence, cohorts and time

Use the same three frozen TI_COMPACT panels from run37150436612 and frozen raw snapshots from run37121749852, with actual file hashes checked against their retained contracts. The existing raw reconstruction audit must confirm Close inputs and the ORIGINAL downvol/pct/dev definitions against the original TI fields before producing the replacement. Record raw-file, panel, builder, fit-source, protocol and numerical-runtime fingerprints before fitting. A new execution run/commit ID is not known at registration and must be recorded when it exists.

Use original panels to compute and freeze all canonical native eligibility masks (at least30 nonmissing original canonical features), training keys and inference keys. Reuse those exact masks after replacement; the additional finite semidev values must not admit new rows or remove old rows. Preserve each vintage's native training cohort, without intersecting cohorts for the primary trial. Labels and group ordering remain original.

Annual expanding training years2017-2026 retain only rows whose signal_date AND exit_date_21 are strictly before Jan1 of the fit year and whose original target is valid. Signal inference ends2026-06-30. Quality uses outcomes mature by2026-07-01, on the same declared original native candidate rowsets for candidate and BASE. Feature computation uses only prices at or before each signal; future outcomes do not select inference rows, determine rolling scales or choose any recipe.

Primary stability uses the original fixed Repeat2 COMMON keys but replaces its nine feature columns with Repeat2 semidev values for the candidate. Each candidate model trained on its own vintage predicts that SAME candidate Repeat2 frame. BASE models predict the original Repeat2 frame. This common-input comparison holds candidate inference constant across fitted vintages and measures the registered representation's total sensitivity; it is not a factorial isolation of training changes alone. Secondary native stability uses each vintage's respective registered representation on exactly the original native keys. Retain both frames and every prediction vector, and state this distinction explicitly.

Use the original common AVX2/Haswell numerical profile and package/thread contract. Require BASE controls fitted on ORIGINAL columns to reproduce existing V2 BASE common AND native arrays byte-for-byte for all years/vintages. Do not call a modified-input BASE a control. Independently refit each candidate yearly vintage and require exact common/native prediction arrays. Actual compiled dispatch targets, BLAS architecture/threads and source identities must agree under the established numerical verification. Preserve raw hardware metadata; only documented execution/integrity corrections are allowed, without changing scientific recipes or gates after outcomes.

## Registered prediction endpoints

Primary: date-weighted realized target_rank_21 of the selected Top1; average vintages equally WITHIN each matched mature date, then dates equally. Use existing deterministic descending-score/ascending-ticker tie policy. The partial2026 fold receives weight proportional to its observed mature dates. Preserve V2 equal-year aggregates as labeled secondary diagnostics.

Secondary: Top1 hits in the realized top decile and exact realized Top5; precision@5/Top5 overlap; linear-percentile NDCG@5/@10; rank IC; signed realized top-decile mean return minus selected return and maximum-return regret where the verified raw target is available. Keep the existing outcome/execution definition, fixed-cardinality top sets and boundary-tie reports. Unavailable returns are unavailable, not zero or inferred from percentile labels. These metrics cannot rescue a failed primary endpoint.

## Paired uncertainty and conjunctive development gate

Preserve the V2 paired temporal bootstrap: candidate-minus-BASE Top1 effects per matched date/vintage, averaged within date; noncircular moving blocks of3 calendar months;20,000 resamples; default_rng(seed=20261004); sampled blocks concatenated and truncated under the established V2 procedure. Apply date indices jointly to all vintages. Report ordinary95% intervals and lower bounds; use the same conservative one-sided lower98.75% bound, the1.25% percentile, for qualification. Repeat block lengths1 and6 as registered sensitivity diagnostics, without choosing their favorable bound.

The retained1.25% threshold is conservative for this single newly registered candidate. It does NOT retroactively make this trial part of V2's original four-challenger family, provide familywise control over all prior research attempts, or remove adaptive selection bias from the historical data. Keep the V2 results and this new registry separate. Bootstrap intervals are conditional historical diagnostics, not a claim of IID dates, independent vintages or untouched out-of-sample evidence.

A DEVELOPMENT_CANDIDATE requires ALL of:

1. Valid raw/panel reconstruction, exactly nine authorized changed columns, original rowsets/labels/groups/other116 fields preserved, source/numerical identity, original BASE byte parity, strict maturity and exact independent candidate refits.
2. Positive date-weighted Top1 improvement over original BASE AND a strictly positive lower98.75%3-month-bootstrap bound.
3. Each vintage's own date-weighted Top1 percentile is at least its same-vintage BASE: absolute noninferiority tolerance zero.
4. Date-weighted precision@5/realized Top5 overlap is at least BASE: absolute tolerance zero.
5. Common rank MAD is reduced at least25% AND native Top1 disagreement is reduced at least25%, with dates weighted equally and the three pairs equally. Each individual common pair MAD and native pair Top1 disagreement must be no worse than the matching BASE pair. For a zero BASE denominator require a zero candidate value; no undefined percentage passes.

Use unrounded gate values. Record every failed requirement and all per-date/per-year/per-pair evidence. Missing or invalid evidence is never PASS. Feature smoothness, reduced missingness, NDCG, a favorable sensitivity interval or CAGR cannot substitute for these conjunctive requirements.

## Economics, future confirmation and outcome registry

Do not choose this formula from CAGR or modify the strategy/feedback. Only after prediction/stability evidence is fixed may a complete raw-source replay assess decisions, CAGR, drawdown and turnover using the unchanged strategy, exact same-vintage Compact63/Tail/MA3 preservation and original masks. If no development candidate qualifies, state that outcome; do not bypass the gate because the revised feature definition appears economically sensible.

Historical Original149, the prior V2/factorial work and the downvol diagnostics are explored development evidence. A successful conditional historical test still needs genuinely unconsulted future dates with mature outcomes and fresh-vintage revision checks before any deployment recommendation. Production adoption remains false. Save the full artifact/attempt registry, anomalies, unavailable metrics, source and protocol hashes, matched control evidence and the next recommended experiment. No fit is authorized by this document alone; execution follows the user's separately authorized work handled by the parent task.
