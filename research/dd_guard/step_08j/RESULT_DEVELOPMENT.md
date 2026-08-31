# STEP08J — Direct BIL vs STAY value selector

**Verdict: REJECT_BEFORE_2023_HOLDOUT.** 2023+ remains sealed.

## Development 2021–2022

| policy                 |      cagr |         dd |       sh |   calmar |        p10 |         p5 |   worstdec |      worst |   delta_cagr_pp |   delta_maxdd_pp |   delta_p10_pp |   delta_p5_pp |   delta_worst_decile_pp |   delta_worst_pp |   delta_sharpe |   delta_calmar |
|:-----------------------|----------:|-----------:|---------:|---------:|-----------:|-----------:|-----------:|-----------:|----------------:|-----------------:|---------------:|--------------:|------------------------:|-----------------:|---------------:|---------------:|
| DIRECT_BIL_VS_STAY_HGB | 17.757120 | -26.908469 | 0.677373 | 0.809544 | -36.416496 | -40.132000 | -41.827988 | -57.507111 |       -2.658865 |        -0.756412 |      -0.602675 |     -0.864045 |               -1.150067 |        -4.400835 |      -0.071426 |      -0.129019 |

## Annual deltas

|        year |   delta_cagr_pp |   delta_maxdd_pp |   delta_p10_pp |   delta_p5_pp |   delta_worst_decile_pp |   delta_worst_pp |   delta_sharpe |   delta_calmar |
|------------:|----------------:|-----------------:|---------------:|--------------:|------------------------:|-----------------:|---------------:|---------------:|
| 2021.000000 |       -3.929958 |        -1.072146 |      -2.093565 |     -2.647298 |               -2.325188 |        -2.468357 |      -0.120111 |      -0.270230 |
| 2022.000000 |       -1.307441 |        -0.172538 |       0.121290 |     -0.203164 |               -0.201506 |         0.000000 |      -0.034431 |      -0.054787 |

## Mechanism

- Decisions: **1124**
- BIL rate: **39.06%**
- STAY rate: **60.94%**
- Exact BIL/STAY oracle hit: **37.81%**
- Selected BIL beats STAY locally: **19.36%**

## BIL/STAY oracle ceiling (diagnostic only)

| policy                        |      cagr |         dd |       sh |   calmar |        p10 |         p5 |   worstdec |      worst |   delta_cagr_pp |   delta_maxdd_pp |   delta_p10_pp |   delta_p5_pp |   delta_worst_decile_pp |   delta_worst_pp |   delta_sharpe |   delta_calmar |
|:------------------------------|----------:|-----------:|---------:|---------:|-----------:|-----------:|-----------:|-----------:|----------------:|-----------------:|---------------:|--------------:|------------------------:|-----------------:|---------------:|---------------:|
| ORACLE_BIL_VS_STAY_DIAGNOSTIC | 21.733176 | -24.979337 | 0.791407 | 1.023408 | -33.701111 | -37.846282 | -39.281330 | -51.763305 |        1.317191 |         1.172719 |       2.112710 |      1.421673 |                1.396590 |         1.342971 |       0.042609 |       0.084846 |

No 2023+ outcomes were opened. No post-result tuning was performed.