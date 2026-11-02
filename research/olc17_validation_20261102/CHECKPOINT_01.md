# OLC17 checkpoint 01 — frozen candidate, timing-factorial executed

2 November2026. Parent candidate not refitted or tuned. Exact restored source-tree0a58a1bb375db1615f390d04f9e4a65e5c7047e4. Initial archiveSHA256ddc79c174afdbacc4060c1dd94b874f745eda3406fbabe6d0b475784322d3df7; recovered-models archiveSHA256e3f0e8db8bfbf9ed68a17fb5e9082b03692b0ce26f2b98574e8b3dfe88252839.19parent tests and9new timing tests pass. A synthetic test initially had Low95 above its94.5 barrier; corrected fixture Low94, no historical input or engine changed to satisfy it.

Completed80 paths:4frozen formulations x2markets x2legacy costs x5timing/ablation scenarios.32paths exactly equal the original engine under its corresponding FULL/LAG1 contract;16also match archived parent arrays exactly.150360intervals reconstructed from actual post-trade units/cash/next Open. Maximum NAV error1.78e-15, independent metric error1.43e-13.

Main2021-2024,IMMEDIATE,fee.001. Values CAGR%; four portfolios ORIGINAL,CUM_FIT,STATIC_REVALUE,CONTEXT_REVALUE:
- LEGACY EU20.031,22.753,21.961,24.000; USA39.922,39.008,38.833,44.153.
- Exposure trigger prior-session, stop arming current: EU19.874,21.443,20.940,22.806; USA39.164,39.201,39.041,44.670.
- Exposure current, stop arming prior-session: EU20.374,23.325,22.568,22.759; USA45.431,42.377,41.874,51.040.
- Both prior-session (exact parentLAG1): EU21.737,20.773,20.341,20.372; USA45.718,44.380,43.509,52.301.
- Gap-systemic and conditional stops disabled, prior-close gross/V6 retained: EU24.345,25.056,23.894,25.743; USA44.360,44.763,42.689,51.429.

The new finding is localization: candidate-minus-matched-static EU CAGR gain shrinks from2.039pp to0.191pp when only conditional-stop arming is moved to prior-session information; moving only exposure timing retains1.866pp. Both prior-session gives+0.031ppEU/+8.792ppUSA. This is a controlled dependency test, not proof that the candidate's economic insight is false or that LAG1 simulates the exact first available intraday fill. The stop/exposure mechanisms interact through cooldown and positions. NO_GAP is an ablation, NOT a recommendation to remove protection.

At stressed fee.003 candidate vs same-static: LEGACY21.492/40.347 vs19.341/35.179(EU/USA); BOTH_PREOPEN17.916/48.657 vs17.849/40.109. Candidate vs CUM_FIT in BOTH_PREOPEN remains slightly worseEU and betterUSA.

Remaining in this block: source-data/time consistency audit, per-decision attribution, risk-stream consistency and clean restore/final archive. Larger nulls, parameter perturbation/refitting and truly prospective verification are NOT completed. main unchanged. Full binary persistence of this new block not yet claimed; this checkpoint records actual completed calculations.
