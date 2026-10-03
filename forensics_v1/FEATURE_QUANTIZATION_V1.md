# ETF_TRADER_FEATURE_QUANTIZATION_V1 — preregistration

Purpose: test whether deterministic quantization of the 125 Compact21 F2D input features suppresses ppm-scale data-vintage sensitivity before XGBoost histogram/ranking amplification.

This is a forensic/engineering experiment, not a performance optimization.

Frozen facts motivating the test:
- 125 F2D features feed Compact21.
- Across frozen Yahoo repeats, the mean F2D cell-change fraction is ~53%, while mean per-column absolute difference is ~4e-5.
- Compact21 raw predictions differ by ~0.035 on average and Compact21 ranks differ by ~0.053 on average.
- Tail is nearly invariant and macro bonus is invariant.
- Native CAGR span is 4.9236 pp; execution ablation collapses it to ~0.000022 pp when decisions are frozen.

Variants:
1. BASE: no quantization.
2. Q4: round all final F2D numeric feature values to 4 decimals immediately before Compact21 train/predict.
3. Q3: round all final F2D numeric feature values to 3 decimals immediately before Compact21 train/predict.

No other source/model parameter changes are allowed.

Primary endpoints (stability, not CAGR):
- cross-snapshot Compact21 raw prediction mean absolute difference;
- Compact21 rank mean absolute difference;
- daily Spearman;
- Top1 disagreement fraction.

Secondary:
- fraction of F2D cells that become exactly equal after quantization;
- native Repeat2 parity under BASE;
- later full-pipeline CAGR span only if a quantized variant materially improves Compact21 stability.

Interpretation:
- Q4/Q3 are diagnostic precision levels, not hyperparameter promotion.
- No variant may be selected for production from Original149 performance.
- A candidate may be promoted only for an independent validation after the forensic.
