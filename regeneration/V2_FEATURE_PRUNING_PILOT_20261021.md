# ETF Trader V2 — frozen 127-leaf feature selection: first OOS audit

Date: 2026-10-21. Status: **pilot completed; second channel/family experiment in progress**.

## Provenance
- Github Actions [pilot run 39507259783](https://github.com/AM1975MA/Test/actions/runs/39507259783), completed **success**.
- Raw input: [2026-10-20 frozen 149-ETF snapshot, run 39482809691](https://github.com/AM1975MA/Test/actions/runs/39482809691), raw artifact `12292840548`.
- Input gate: SOURCE_ONLY_INPUT_GATE_PASS; 149 ETFs and canonical 500 baskets of 24; basket SHA256 `36a45916b5d8191f3ccd206f39bf3fd3f1ed4bcaffd474e352b69c598f2b6a5e`.
- 36 monthly OOS decisions: 2018, 2022, 2025; original 125-feature source-only compact XGBRanker, `rank:pairwise`, `max_leaves=127`, `max_depth=0`, 360 boosting rounds, seeds 101/202/303; annually refitted, matured 21-day labels only.
- Original 125-feature set never changed its training-eligibility mask. Tail, macro, risk, portfolio allocation deliberately **disabled**.
- Frozen K16/K32/K46 feature ladders from [feature-only artifact 11441633998](https://github.com/AM1975MA/Test/actions/runs/37525303057) (pre-2017 supervised feature discovery). Feature selection artifact status FEATURE_SELECTION_COMPLETE_NO_FINAL_RANKER_FIT.

## Matched predictive results
| Model | Features | Universe IC | Universe Top1 | Universe Top3 | Basket Top1 | Basket Top3 | Basket 21D regret |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| BASE125 | 125 | 0.076193 | 11.11% | 19.44% | 18.08% | **37.84%** | 0.09597 |
| K16 | 16 | 0.059294 | 5.56% | 8.33% | 13.16% | 30.76% | 0.10811 |
| K32 | 32 | 0.054655 | 8.33% | 22.22% | 13.13% | 31.94% | 0.10740 |
| K46 | 46 | 0.060078 | 5.56% | 16.67% | 12.56% | 31.89% | 0.10828 |

Original paired 6-month circular block bootstrap on 36 compressed OOS months (sample consists of **nonconsecutive years**):
- K16 minus baseline basket Top3: -7.08 pp, 95% exploratory CI [-10.86, -3.63] pp;
- K32 minus baseline basket Top3: -5.89 pp, CI [-8.82, -2.32] pp;
- K46 minus baseline basket Top3: -5.94 pp, CI [-8.88, -3.09] pp.
**Caution:** the six-month circular bootstrap originally treated 2018, 2022 and 2025 as a concatenated sequence, thereby wrapping around nonadjacent calendar segments. Use the above CIs as exploratory screening only, not strict population intervals. Also the three years were already explored in prior research.

## Per-year basket Top3
| Year | BASE125 | K16 | K32 | K46 |
| --- | ---: | ---: | ---: | ---: |
| 2018 | 30.55% | 21.30% | 20.98% | 22.75% |
| 2022 | 45.03% | 39.30% | 42.47% | 40.30% |
| 2025 | 37.93% | 31.68% | 32.38% | 32.63% |

## Input-quality caution
The pilot's **same frozen snapshot**, pre-2017 diagnostic gives missing fractions:
- `downvol21` 45.99%;
- `downvol63` 62.58%;
- `downvol126` 72.39%.
Each missing fraction propagates to its pct/dev derived features. The code uses `ret.where(ret<0).rolling(h, min_periods=max(10,h//2))`; missingness is **structural and potentially informative** about the number of negative observations, not missing at random. Audit before editing the formula.

## Interpretation and decision
- The preregistered **single representative per feature family** compression does not preserve predictive performance in this matched pilot.
- A per-month raw feature, percentile and robust deviation are monotonic cross-sectionally but not equivalent across different market environments for globally fitted tree thresholds.
- Do **not** promote a reduced set or edit production based on this pilot.
- Next stage: [representation/family drop-one workflow](https://github.com/AM1975MA/Test/actions/workflows/v2-feature-channel-ablation.yml) comparing NO_DEV/NO_PCT/NO_RAW and NO_MARKET/NO_MOMENTUM/NO_VOLRISK/NO_LIQUIDITY on the same frozen input.
- Follow with temporally nested feature selection and a larger, explicitly defined walk-forward confirmation; do not optimize feature count on CAGR.

All numeric claims here refer to the archived pilot artifact `12303808328`, not to the later in-progress experiment.
