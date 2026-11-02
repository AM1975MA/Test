# OLC16 checkpoint 02 — first native results

2 November 2026. Main fitting complete:24 annual models,24 training-context permutation controls,66 inner-validation fits,342 deterministic optimization starts. No new ETF base model trained. Input/reference checkpoint07f... remains separate. An execution ceiling interrupted two whole-loop attempts; the same frozen fits were completed by annual batches. The counts here refer to distinct final models, not attempts.

Native CURRENT metric: Top2 excess discounted incremental log utility U42. Primary signals2021–2024 with all63-day outcomes mature before2025,44EU/45USA. Values below multiplied by100 (log percentage points), NOT CAGR.

| Variant | EU | USA |
|---|---:|---:|
| ORIGINAL | .559949 | .734196 |
| CUM_FIXED | .307434 | .202144 |
| CUM_FIT | .383220 | -.123714 |
| PAIR_STATIC | .307900 | .028997 |
| PAIR_CONTEXT | .334225 | .347077 |
| TOP2_STATIC | .248790 | -.121650 |
| TOP2_CONTEXT | .288840 | -.086478 |
| PAIR_NULL1601 | .175985 | .305164 |
| PAIR_NULL1602 | .333349 | -.082581 |
| TOP2_NULL1601 | .219511 | -.091209 |
| TOP2_NULL1602 | .280158 | -.090335 |

Context improves each new model relative to its matched static control in both markets in this primary native window. Effects are not all large. Neither dominates ORIGINAL; pair context improves US relative to CUM_FIT but not EU. Two null controls are too few for a calibrated significance claim.

Across66 forecast dates2021–June2026, PAIR_CONTEXT vs PAIR_STATIC changes native Top2 in7EU/6USA and final Top2 in6EU/5USA. TOP2_CONTEXT vs TOP2_STATIC changes native15EU/11USA and final14EU/13USA. This is unlike OLC15's zero final differences.

After unchanged memory/fusion, PAIR_STATIC U excess is1.096EU/1.130USA versus PAIR_CONTEXT .981/.949. TOP2_STATIC is.826/1.023 versus TOP2_CONTEXT1.100/.998. Thus a native gain is not yet a shared final benefit. No new portfolio result has been inspected at this checkpoint.

## Post-observation extension registered before its outputs
Test whether retaining old horizon forecasts under old contextual weights suppresses the new information. Four additional score-only variants: PAIR_STATIC_REVALUE, PAIR_CONTEXT_REVALUE, TOP2_STATIC_REVALUE, TOP2_CONTEXT_REVALUE. No refit, new hyperparameter, timing, risk or cost choice.

At each current decision, apply its current trained beta to each of the current and preceding two stored horizon-forecast vectors. Map each resulting historical cross-section monotonically to that date's fixed-anchor distribution, align to current candidates, then use unchanged40/30/30 availability-aware memory, power1.1 and47.5/52.5 fusion. The current model and context may revalue past forecasts at the CURRENT decision only; historical orders are not revised. Historical forecast values remain as originally known. Inputs missing at an old date stay missing; never use future labels to fill them. Current selection support stays unchanged.

Identical operation applied to static controls. Constant beta across dates must reproduce legacy memory. These controls distinguish revaluing yearly coefficients and nonlinear scale mapping from genuine regime value. The original current scores must remain identical. Add4x2x8=64replays to the original144, total208distinct configurations incl48references. Native metrics for all variants retained. This is an explicitly exploratory extension motivated by the first outputs, NOT independent confirmation and NOT part of the original preregistration. No new date-shifting or scenario is selected after its results.
