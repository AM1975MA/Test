# Compact21 MAD fallback continuity — measured results and decision

## Verified evidence

Run [38093812635](https://github.com/AM1975MA/Test/actions/runs/38093812635) **SUCCESS** after repairing JSON encoding for empty transitions. All 33 Compact21 `_dev` features, three Original149 independently reconstructed frozen source panels, no learning and no input modification. Diagnostics files `NEAR_ZERO_MAD.csv`, `ZERO_TO_POSITIVE_TRANSITIONS.csv`, `RESULT.json` are in the workflow artifact.

- Using the ratio `(1.4826*MAD)/population_STD` as a scale benchmark, **0** positive-MAD eligible feature observations per vintage fall at or below 0.01, while **1878** fall at or below 0.1; of those 1878, **494** exceed absolute robust deviation 8 before the original ±8 clipping. Counts the same across all 3 vintages.
- **0** exact MAD-zero ↔ MAD-positive state transitions between any of the 3 snapshot pairs. Thus no *observed* discontinuity across the three source download revisions can be demonstrated.
- All **1761** MAD-zero source-valid cells in each vintage remain MAD-zero across the other vintages, with no pairwise absolute deviation >0.1 from STD fallback, as separately shown by run [38093523739](https://github.com/AM1975MA/Test/actions/runs/38093523739).
- This is a **source-pair observational test**, not a proof of mathematical continuity. An exact-zero conditional replacement `scale = MAD>0 ? 1.4826*MAD : STD` has a potential jump when MAD changes from zero to arbitrarily small positive; changing the scale from positive STD to tiny MAD can push nonmedian observations immediately to ±8. No input repair or baseline model change approved.

## Decision

**The exact-zero-only STD fallback is NOT YET CERTIFIED as continuous**. It fixes all observed zero-MAD NaNs but can fail under synthetic infinitesimal perturbations of previously tied raw features. Further preregistered alternatives: use a smooth denominator lower bounded by a robust fraction of standard deviation, or use a single globally defined STD at all cross-sections. Both would change feature semantics and require a full three-vintage numerical audit, unit tests for near-zero perturbations, causal input-contract testing, and subsequent model-quality gates. Do not change canonical V2 or zero-fill 732 off-median cells. Original 252-bar warmup NaNs still need an explicit eligibility mask rather than fabricated values.

No retraining, CAGR calculation or productive source edit in this stage.
