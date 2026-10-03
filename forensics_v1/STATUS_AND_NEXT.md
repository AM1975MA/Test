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
