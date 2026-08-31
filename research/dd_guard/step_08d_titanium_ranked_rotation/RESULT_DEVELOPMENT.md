# STEP08D — Titanium-ranked protective rotation

**Verdict: REJECT_BEFORE_2023_HOLDOUT.** 2023+ remains sealed.

## Development 2021–2022

| policy            |      cagr |         dd |       sh |   calmar |        p10 |         p5 |   worstdec |      worst |   delta_cagr_pp |   delta_maxdd_pp |   delta_p10_pp |   delta_p5_pp |   delta_worst_decile_pp |   delta_worst_pp |   delta_sharpe |   delta_calmar |
|:------------------|----------:|-----------:|---------:|---------:|-----------:|-----------:|-----------:|-----------:|----------------:|-----------------:|---------------:|--------------:|------------------------:|-----------------:|---------------:|---------------:|
| TIT_R_TOP1        | 20.781516 | -25.451432 | 0.753886 | 0.960859 | -34.963473 | -39.585027 | -40.550170 | -55.240562 |        0.338573 |         0.700624 |       0.850347 |     -0.317072 |                0.127750 |        -2.134287 |       0.004472 |       0.020952 |
| TIT_R_V2_BALANCED | 20.652335 | -25.473933 | 0.753354 | 0.951617 | -34.650242 | -39.307175 | -40.431100 | -55.161931 |        0.209391 |         0.678123 |       1.163579 |     -0.039220 |                0.246820 |        -2.055655 |       0.003940 |       0.011710 |

## Annual deltas

| policy            |   year |   delta_cagr_pp |   delta_maxdd_pp |   delta_p10_pp |   delta_p5_pp |   delta_worst_decile_pp |   delta_worst_pp |   delta_sharpe |   delta_calmar |
|:------------------|-------:|----------------:|-----------------:|---------------:|--------------:|------------------------:|-----------------:|---------------:|---------------:|
| TIT_R_TOP1        |   2021 |       -2.589899 |        -0.772183 |      -0.716431 |     -0.460006 |               -0.479558 |        -3.750856 |      -0.099630 |      -0.219404 |
| TIT_R_TOP1        |   2022 |        3.062842 |         1.070020 |       1.674434 |      1.492482 |                1.712478 |         6.634598 |       0.081579 |       0.146837 |
| TIT_R_V2_BALANCED |   2021 |       -2.226037 |        -0.685098 |      -0.625523 |     -0.009059 |               -0.358796 |        -4.107842 |      -0.078450 |      -0.190670 |
| TIT_R_V2_BALANCED |   2022 |        2.498097 |         0.984366 |       1.630698 |      1.746953 |                1.851807 |         6.634598 |       0.066384 |       0.114020 |

## Mechanism

- Authentic unrestricted ranking parity: **72/72**.
- Frozen decisions: **1124**.
- Mean / median / max score age: **14.2 / 13.0 / 32 calendar days**.
- V2_BALANCED 100% top-1 concentration rate: **0.00%**.
- Top-1 is BIL: **0.00%**.
- Top-1 exact oracle destination hit: **1.16%**.

No parameter was retuned after observing these results.