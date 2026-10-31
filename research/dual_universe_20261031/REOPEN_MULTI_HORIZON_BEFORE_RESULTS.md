# Reopening multi-horizon evidence before new economic results

31 October 2026. This protocol addition was recorded after reading the archived TARGET_REDESIGN_REPORT.md (blob 4eee7a34c404b6c498ddfb3d15871aa518ea65e2) and TARGET_ROBUSTNESS_REPORT.md (blob e74c2fef790397a80a6a0716942cc31145f9ab42), while common first-stage annual fits were running, BEFORE any DUAL-01 portfolio scorecard was produced or inspected.

Those original reports provide a favorable but uncertain consensus-target hypothesis with adverse regimes; zero-containing intervals alone do not justify excluding it. No old CAGR is transferred to the new version.

Add three annual models in BOTH USA149 and EU165, with the identical corrected features, fixed XGB parameters and seeds of BASE_D4:
- BASE_MATURE63: original 21-session rank target, but the exact same training-row mask as the multi-horizon treatments, including fully matured 21/42/63 labels strictly before Jan1 of the fit year. This is essential to separate the target effect from the training purge/sample change.
- MULTI_453520: .45*rank21 + .35*rank42 + .20*rank63.
- CONSENSUS_MULTI: .35*rank21 + .30*rank42 + .20*rank63 + .15*min(rank21,rank42,rank63).

The ranks are cross-sectional eligible-universe ranks at the same signal date. Training all three treatments uses identical rows with all three future returns observed and exit63 strictly before cutoff. Scores are predicted for the same current eligible rows without requiring future test returns. Rank pairwise labels are rounded 0..100 as for BASE_D4. No target weights are optimized now.

Add each standalone score and its .475 first-stage/.525 native Hybrid counterpart. This expands 15 to 21 selectors, preserving the 40 portfolio configurations and two cost levels in both markets: 840 policies per market per fee, 3,360 complete paths in total. The baseline comparator, development choice rule, market symmetry, causal execution and posterior specification are unchanged. The extra experiments increase post-selection risk and will be disclosed, not hidden as a new independent holdout. Existing CONSENSUS benefits do not exempt it from European verification.
