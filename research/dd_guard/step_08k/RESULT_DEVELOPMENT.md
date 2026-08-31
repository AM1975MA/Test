# STEP08K — Regime-adaptive BIL vs STAY

**Verdict: REJECT_BEFORE_2023_HOLDOUT.** 2023+ remains sealed.

## Development 2021–2022

| policy                         |      cagr |         dd |       sh |   calmar |        p10 |         p5 |   worstdec |      worst |   delta_cagr_pp |   delta_maxdd_pp |   delta_p10_pp |   delta_p5_pp |   delta_worst_decile_pp |   delta_worst_pp |   delta_sharpe |   delta_calmar |
|:-------------------------------|----------:|-----------:|---------:|---------:|-----------:|-----------:|-----------:|-----------:|----------------:|-----------------:|---------------:|--------------:|------------------------:|-----------------:|---------------:|---------------:|
| EXP365_WALKFORWARD_BIL_VS_STAY | 18.772072 | -26.660382 | 0.704720 | 0.863732 | -36.641135 | -39.866992 | -41.569000 | -53.808429 |       -1.643913 |        -0.508326 |      -0.827315 |     -0.599037 |               -0.891079 |        -0.702153 |      -0.044078 |      -0.074830 |

## Annual walk-forward deltas

| year | delta_cagr_pp | delta_maxdd_pp | delta_p10_pp | delta_p5_pp | delta_worst_decile_pp | delta_worst_pp | delta_sharpe | delta_calmar | bil_rate | oracle_bil_rate | oracle_hit_rate | selected_bil_win_rate |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 2021 | -2.051967 | -0.666228 | -1.119773 | -2.415683 | -2.086114 | -2.468357 | -0.062004 | -0.134266 | 0.360215 | 0.293907 | 0.460573 | 0.159204 |
| 2022 | -1.161840 | -0.102238 | -0.034873 | 0.128918 | -0.292014 | 0.000000 | -0.032002 | -0.046177 | 0.279152 | 0.469965 | 0.452297 | 0.360759 |

## Mechanism
- BIL rate overall: **31.94%**
- Oracle BIL rate: **38.26%**
- Exact oracle hit: **45.64%**
- Selected BIL beats STAY locally: **24.79%**

One-year exponential half-life was frozen before replay. No 2023+ outcome was opened and no post-result retuning was performed.
