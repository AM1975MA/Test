# ETF_trader perturbation forensics V1 — status marker

## Negative-feedback line frozen state

Source branch at fork: `research/etf-trader-negative-feedback-v1` @ `84851b1aeb661a7e2fb70861fb671076261f3873`.

Completed tests:
- `NF_V1_A_CAUSAL_RESIDUAL_FEEDBACK`: REJECT. Calibration error improved, but cross-snapshot economic dispersion worsened.
- `NF_V1_B_RANK_RELIABILITY_FEEDBACK`: REJECT. Ranking became modestly more similar across snapshots, but target ranking quality and CAGR dispersion worsened.
- `NF_V1_C_CONFIDENCE_FEEDBACK`: REJECT current controller. Decision identity was exact and risk-only feedback was technically clean; CAGR span fell only from 4.9236 pp to 4.8469 pp (~1.56%), far below the preregistered 25% gate.

## Deferred next suggestion — DO NOT LOSE

After the perturbation forensic is complete, resume with a distinct preregistered line for a **causal state-dependent residual learner**.

Concept:
- Keep canonical ETF_trader as the base predictor.
- Train a second causal model only on fully matured past errors.
- Predict expected model error conditional on current market/model state and past matured error state.
- Candidate form: `score_final = score_ETF_trader - predicted_error`.
- No ex-post parameter sweep; evaluate convergence/stability before CAGR.

This suggestion is intentionally deferred until we understand the current perturbation amplification mechanism and complete a lookahead audit.

## Current priority

Line: `ETF_TRADER_PERTURBATION_FORENSICS_V1`

Questions to answer:
1. Where is the first material amplification of ppm-scale raw perturbations?
2. Is it deterministic code/preprocessing, clustering/ranking transforms, ML fit (ExtraTrees/XGBoost), execution, or another layer?
3. Which model/component contributes most to Top1/Top2 divergence and CAGR dispersion?
4. Is there any lookahead/data leakage in feature generation, target construction, fitting, clustering, ranking, allocation, or execution?
5. Can the 29.75% / 30.84% / 34.68% dispersion be decomposed quantitatively by stage?


## Forensic progress marker — 2026-10-03

Confirmed findings:
- Same raw bytes -> bit-identical model/replay outputs across runners and repeated runs. Runtime/code nondeterminism is not the source of the 4.9236 pp CAGR spread.
- Frozen Repeat2 decisions executed on Repeat1/2/3 raw collapse CAGR span from 4.9236 pp to ~0.000022 pp. Execution prices, risk gross, stops and downstream execution mechanics are not material causes.
- Raw/target perturbations are tiny; MA3 corrected target changes only ~0.19-0.20% of cells across repeats.
- Titanium internal ablation reconstructs canonical TIT_R exactly. Primary instability is Compact21 XGBRanker: Compact21 raw outputs differ on 100% of common cells, mean abs ~0.035-0.036; Compact21 ranks differ on ~92-93.5% of cells. Tail is highly stable (rank changes ~5.8-6.5%, tiny mean raw difference ~5.7e-5 to 6.7e-5). Macro boost is inactive in the evaluated panel and contributes zero cross-repeat divergence.
- Therefore the first dominant perturbation amplifier is the Compact21 / XGBRanker branch inside Titanium; final percentile ranking mainly propagates rather than originates the instability.
- Process-isolated future-mutation/truncation audit still fails for MA3 ensemble predictions while TIT_R remains exactly invariant. This is now a genuine causal-invariance issue to localize, not an OpenMP/XGBoost process-state artifact. Maturity gates still pass. Do not certify lookahead absence yet.

Immediate next forensic tasks:
1. Compact21 XGB attribution: separate sensitivity to continuous/dev features, labels, quantile binning and tree split topology. The first attribution run failed at source gate and is INVALID TECHNICAL.
2. Localize the MA3 future-invariance failure to feature construction vs ET/XGB fit/post-processing and determine whether it is operational lookahead or a boundary/normalization artifact.
3. Only after (1)-(2), close forensic verdict and return to the deferred causal residual learner line.
