# Stabilized Compact21 robust deviation denominator grid — 2026-10-11

Successful source experiment: [GitHub Actions 38093992533](https://github.com/AM1975MA/Test/actions/runs/38093992533). Frozen Original149 three raw acquisition derived feature panels; **no model training, source OHLCV replacement, production changes or CAGR**. Evaluated each of 33 _dev features on all 40,230 ticker-date rows per vintage with formula clip((x - cross-sectional median) / max(1.4826*MAD, alpha*STD_pop), -8, 8), for alpha={0.05, 0.1, 0.25, 0.5, 1.0}, and STD-only. If completely tied (STD=0 and all sources equal median) defined centered deviation zero only after proving numerator zero; preserve any missing input.

## Completeness results, identical all 3 vintages
- Existing independent clean-downvol source: 34,876 eligible under >=30-feature gate; 31,827 fully 125-feature-complete.
- Every tested denominator policy: **33,211** fully complete, +1,384 vs original experimental clean-downvol baseline, **1,665** still currently eligible but missing other features.
- This is a **data-only availability** increase, not an improvement in predicted ETF rankings.

## Cross-source feature numerical drift and semantic cost
Per vintage:
| policy | modified previously-finite _dev cells | clipped _dev cells | max absolute value difference across source pairs |
|---|---:|---:|---:|
| max_0.05 | 461 | 6,073 (repeat3: 6074) | .111044550013 |
| max_0.10 | 1,511 | 5,835 (repeat3: 5836) | .111044550013 |
| max_0.25 | 12,195 | 5,122 (repeat3: 5123) | .111044550013 |
| max_0.50 | 113,890 | 2,657 | .111044550013 |
| max_1.00 | 1,007,355 | 150 | .059943631796 |
| STD-only | 1,129,301 | 150 | .059943631796 |

Pairwise p99 abs difference repeat1–repeat2: max_0.05 .000740908675; max_0.10 .000733126715; max_0.25 .000722576471; max_0.50 .000684664080; max_1.00 .000418257379; STD-only .000391207502. Larger floors significantly re-encode the existing normalized features, even though the high-level finite coverage is identical. None of these thresholds was picked based on economic model fit.

## Continuity sanity test
The prescribed synthetic 10-point cross-section with 8 tied median values, 2 off-median points and epsilon perturbations 1e-12, 1e-9, 1e-6 retained all finite outputs. Maximum output change compared to zero-perturbation: 1.9518e-5 (alpha=.05), 9.7590e-6 (.10), 3.9036e-6 (.25), 1.9518e-6 (.50), 9.7590e-7 (1.0 and STD-only). This is a **specific stress test**, not a universal mathematical continuity proof nor a systematic tail/outlier analysis.

## Decision

A floor based on STD is mathematically better behaved around exact MAD=0 than the prior exactly-zero-only fallback. **No alpha selected or correction adopted.** alpha=.05 modifies the fewest existing finite values but retains larger worst-case Yahoo revision drift; alpha=1 and STD-only reduce worst-case drift but change nearly all _dev cells. The remaining 1,665 otherwise-eligible incomplete rows need classification (cold start or legitimate mathematical conditions), and the entire ETF Trader V2 including Tail, MA3, macro inputs is not certified.

Next: preregister a single minimal-change candidate (consider alpha=.05 if wanting near-parity) and an independent stronger-regularization reference, generate *read-only candidate panels* and verify exact preservation of all non-_dev columns, 3-source key sets, all-feature completeness and time causality. Only after comparing predictive stability and CAGR through separately frozen tests should any candidate be adopted. Keep all frozen source data immutable.

Artifacts: POLICY_COVERAGE.csv, POLICY_THREE_SOURCE_DRIFT.csv, SYNTHETIC_CONTINUITY.csv, RESULT.json from workflow.
