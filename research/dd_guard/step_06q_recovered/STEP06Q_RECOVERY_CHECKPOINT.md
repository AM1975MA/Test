# STEP06Q recovery checkpoint — 2026-08-31

## Frozen scientific result
`dgs10_chg63` is the only USD/Treasury feature from the 37-feature frozen family that passed discovery and replicated incrementally in 2021–2022.

- Discovery 2019–2020 residual Spearman: pooled **+0.15623**, 2019 **+0.49414**, 2020 **+0.01532**.
- Discovery forward RMSE improvement: **+2.2867%**.
- Development 2021–2022: RMSE control **0.0319027**, with `dgs10_chg63` **0.0312409**, improvement **+2.0745%**.
- 2021 improvement **+0.4577%**; 2022 **+10.601%** on only 3 crossing dates.
- Incremental development Spearman **+0.12442**.
- Frozen q30 translation classified **100%** of 2021–2022 crossings as AGGRESSIVE, so STEP06Q was rejected before 2023 holdout.

## Persistence / reconstruction status
The original STEP06Q output bundle was not committed before the prior execution ended. The upstream STEP06K/06L and STEP06O reproducibility packages are preserved. This recovery checkpoint records the already-computed STEP06Q metrics without inventing missing parity details. Any locally reconstructed model is explicitly labelled as reconstruction unless it reproduces the reported metrics.

## Next frozen task
STEP06R tests calibration only: keep `dgs10_chg63`, q30 semantics, FUSION1/STEP06K mechanics and 2023+ seal unchanged; replace the drifting absolute action-value scale with causal historical calibration.
