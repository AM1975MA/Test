# NF_V1_A — Decision

**Status: REJECT_V1_A_CURRENT_CONTROLLER**

The preregistered ticker-level causal residual controller improves numerical calibration but does not achieve the primary convergence objective.

## What improved

Across the three frozen Yahoo perturbation snapshots:

- MAE: 0.300004 -> 0.281261 (**-6.25%**)
- RMSE: 0.373320 -> 0.351600 (**-5.82%**)
- absolute mean bias: 0.099994 -> 0.066281 (**-33.71%**)
- exact ordered Top1+Top2 pair agreement across snapshots: 38.35% -> 43.43%
- unordered two-leader-set agreement: 49.44% -> 55.07%

## What failed

- pairwise exact Top1 agreement: 68.62% -> 66.89%
- all-three exact Top1 agreement: 54.18% -> 51.35%
- mean rank dispersion increased
- mean pairwise rank Spearman declined slightly
- residual lag-1 autocorrelation increased slightly
- CAGR span across the same three perturbation snapshots: **4.92 pp -> 9.19 pp**

Economic results are not used to select the controller, but the larger CAGR dispersion confirms that V1_A does not stabilize the full decision pipeline.

## Scientific interpretation

The experiment demonstrates that matured ex-post error contains useful calibration information: the controller reduces level error consistently on all three snapshots. However, applying that feedback independently to each ticker's score is not the right control variable for convergence. It changes relative ordering and can move the identity of Top1 even while absolute prediction error improves.

The separate bifurcation diagnostic shows that microscopic raw perturbations are already amplified strongly in the cross-sectional source-only/Titanium ranking layer before final ensemble selection. Therefore any next feedback experiment should target **relative rank stability / confidence / decision margin**, or a higher-level cluster/rank error state, rather than simply subtracting a per-ticker level bias.

No V1 parameter has been retuned after observing the result.

## Technical note

All three scientific replay jobs completed successfully and Repeat2 reproduced the canonical 30.8437049% baseline. The workflow aggregation job failed only because pandas was absent in that summary job. The frozen result above was reconstructed from the three successful artifacts; this technical failure does not invalidate the experiment.
