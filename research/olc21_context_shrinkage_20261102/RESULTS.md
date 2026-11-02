# OLC21 — context shrinkage / blend results

2 November 2026. Exploratory post-OLC20 block. No new ETF learner, feature, target or risk parameter was fitted.

## Coverage
- 27 fixed FUSION blends: AUTH with STATIC, CONTEXT_LAG or PENALTY_HALF, AUTH weights 0.1..0.9.
- One causal annual selector plus exact AUTH control.
- 29 score procedures, two markets, ALARM/FAST_LOCK3 and fees .001/.003: 232 economic accounts.
- Candidate-specific V6 rebuilt for every pair.
- 3 local tests pass; CSV re-serialization tolerance is explicitly 2e-16 after an observed maximum 1.11e-16 round-trip difference.

## Result
No fixed blend and no META_CAUSAL candidate improves CAGR over AUTH in BOTH EU165 and USA149 on the 2021–2024 primary window under any of the four contract/cost combinations.

Closest non-identical candidate:
- BLEND_HALF_A90 = 90% AUTH + 10% PENALTY_HALF.
- ALARM fee .001: EU +1.187 pp CAGR, USA -0.365 pp versus AUTH.
- FAST_LOCK3 fee .001: EU +1.198 pp, USA -0.578 pp.
- Fee .003 keeps the same sign: EU +1.159 pp / USA -0.592 pp under FAST_LOCK3.

BLEND_STATIC_A90 produces the same discrete Top2 decisions as AUTH in the primary account and therefore identical economics; identical curves are not new alpha.

## Causal selector
Annual selection from mature prior outcomes chose:
- 2021 AUTH
- 2022–2024 BLEND_STATIC_A80
- 2025–2026 BLEND_HALF_A80

META_CAUSAL does not improve the common result. FAST_LOCK3 fee .001 2021–2024:
- AUTH: EU 23.200%, USA 50.772%
- META_CAUSAL: EU 22.671%, USA 50.772%

The unchanged USA curve reflects unchanged discrete selections, not extra alpha.

## Interpretation
The OLC20 trade-off is not repaired by simple linear score shrinkage. Small score perturbations are thresholded by Top2 selection: useful European changes are accompanied by adverse US changes, while some blends leave the selected pair unchanged.

Next research direction should therefore act on the decision transition itself rather than merely rescaling the ranking. The pre-existing roadmap's fixed change-margin / residual-value control is the natural next test. This OLC21 block remains exploratory historical evidence, not prospective validation.
