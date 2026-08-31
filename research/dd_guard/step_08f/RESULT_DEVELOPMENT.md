# STEP08F — event-time Titanium score distillation

**Verdict: REJECT_BEFORE_2023_HOLDOUT.** 2023+ remains sealed.

## F0 producer parity

| model   |   mean_spearman_2019_2020 |   median_spearman_2019_2020 |   mean_basket_top3_overlap |
|:--------|--------------------------:|----------------------------:|---------------------------:|
| HGB     |                  0.864606 |                    0.903810 |                   0.536917 |
| ET      |                  0.854210 |                    0.899007 |                   0.517972 |
| RIDGE10 |                  0.845004 |                    0.900772 |                   0.488306 |

Selected producer: **HGB**. Parity gate: **PASS**.

## F1 development replay

| policy                        |      cagr |         dd |       sh |   calmar |        p10 |         p5 |   worstdec |      worst |   delta_cagr_pp |   delta_maxdd_pp |   delta_p10_pp |   delta_p5_pp |   delta_worst_decile_pp |   delta_worst_pp |   delta_sharpe |   delta_calmar |
|:------------------------------|----------:|-----------:|---------:|---------:|-----------:|-----------:|-----------:|-----------:|----------------:|-----------------:|---------------:|--------------:|------------------------:|-----------------:|---------------:|---------------:|
| EVENT_TIME_DISTILLED_TIT_R_V2 | 21.075426 | -26.101554 | 0.765866 | 0.982011 | -36.678833 | -41.242441 | -42.032168 | -52.501469 |        0.632483 |         0.050503 |      -0.865013 |     -1.974486 |               -1.354248 |         0.604807 |       0.016452 |       0.042104 |

## Annual deltas

|        year |   delta_cagr_pp |   delta_maxdd_pp |   delta_p10_pp |   delta_p5_pp |   delta_worst_decile_pp |   delta_worst_pp |   delta_sharpe |   delta_calmar |
|------------:|----------------:|-----------------:|---------------:|--------------:|------------------------:|-----------------:|---------------:|---------------:|
| 2021.000000 |        0.314126 |        -0.219715 |      -0.629317 |     -0.962080 |               -1.171213 |        -5.116730 |       0.006885 |       0.039122 |
| 2022.000000 |        0.987675 |         0.408654 |       0.174218 |     -0.438049 |               -0.261970 |         0.918903 |       0.025440 |       0.061358 |

## Mechanism

- Decisions covered: **1124/1124**.
- BIL fallback: **0.00%**.
- Event utility beats exact FUSION1: **53.74%**.

No 2023+ outcome was opened and no post-result retuning was performed.