# STEP06R development freeze — before one-shot holdout

The development-only run qualified `QPROXY_A + R1_EXPANDING_ECDF` under the pre-registered gate. The 2021–2022 exact replay versus STEP06K was **+0.00358 pp CAGR, +0.00000 pp mean MaxDD, +0.000049 Sharpe**, with 86.7% date-weighted aggressive rate. The edge is deliberately treated as weak: qualification authorizes exactly one diagnostic holdout opening, not promotion.

The original STEP06Q estimator was not persisted. STEP06R therefore freezes the explicit low-dimensional reconstruction and does **not refit** it on 2021–2022. The selected model remains trained on 2019–2020 only. The R1 expanding ECDF is seeded with all 2019–2022 raw scores and then updates only from scores, never labels, after each holdout date.

All engine mechanics and q30 semantics are frozen. No 2023+ outcome has been used to change the model, threshold, feature family, or calibration rule.
