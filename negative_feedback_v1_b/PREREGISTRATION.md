# PREREGISTRATION — NF_V1_B_RANK_RELIABILITY_FEEDBACK

Date frozen: 2026-10-03

## Scientific question

V1_A showed that causal matured residual feedback reduces numerical calibration error but does not improve cross-snapshot Top1 convergence. The next controlled question is narrower:

**Can strictly causal feedback on ranking reliability, rather than ticker-level score level, reduce rank/decision instability across the three frozen Yahoo perturbation snapshots without changing the monthly cross-sectional score distribution?**

## Frozen inputs

- Development universe: Original149 only.
- Same three frozen Yahoo/yfinance 0.2.66 perturbation snapshots from workflow run `37121749852`: `_repeat1`, `_repeat2`, `_repeat3`.
- Same canonical ETF_trader V2 productive source blobs and exact Python/package environment used in NF_V1_A.
- Same canonical full-universe replay and Stage19/risk/execution path.
- Repeat2 untouched baseline parity target: CAGR `0.30843704925646037`, exact deterministic tolerance `<1e-12`.

No Holdout70 and no EU120 are used in this development experiment.

## Controller definition

The controller acts only on the **cross-sectional ordering** of the canonical Stage19 score matrix.

For each signal date `t`:

1. Compute the untouched canonical score vector `S_t` for all Original149 candidates.
2. Convert it to a cross-sectional percentile-rank vector `R_t` (higher = better).
3. Before using any ex-post information, identify prior signal dates `tau` whose 63-day target exit date is **strictly earlier** than `t`.
4. For every matured `tau`, compare the canonical score ranking with the realized `HYBRID_TARGET` ranking and compute pairwise ordering accuracy:

   `A_tau = concordant_pairs / comparable_pairs`

   where random ordering has expected accuracy approximately 0.50 and perfect ordering is 1.00.
5. The causal ranking reliability at `t` is the expanding mean of all matured `A_tau` values available before `t`:

   `Q_t = mean(A_tau for matured tau < t)`

6. Minimum matured dates before feedback is active: **3**. Before then `R'_t = R_t`.
7. Once active, apply reliability-weighted temporal negative feedback:

   `R'_t = Q_t * R_t + (1 - Q_t) * R'_(t-1)`

   Thus a historically unreliable ranker is prevented from making large one-period ordering jumps, while a reliable ranker is allowed to move faster.
8. To isolate ranking from score-level/risk effects, remap `R'_t` back onto the **exact sorted multiset of canonical scores `S_t`**. Therefore each month preserves the same score values, mean, variance, extrema and score distribution as the baseline; only ticker-to-score assignment may change.

There is **no lambda, cap, gain sweep, CAGR optimization, or post-hoc parameter selection** in V1_B.

## Causality rule

Only target/ranking outcomes whose `exit_date_63` is strictly earlier than the current signal date may affect `Q_t`. Current or partially matured targets are forbidden.

## Primary endpoints

Measured on each snapshot and aggregated across the three snapshots:

- cross-sectional rank MAE versus realized `HYBRID_TARGET` rank;
- mean rank IC (Spearman) versus realized target rank;
- mean pairwise ordering accuracy versus realized target ordering;
- pairwise Top1 agreement across `_repeat1/_repeat2/_repeat3`;
- pairwise ordered Top1+Top2 agreement;
- pairwise unordered Top2-set agreement;
- all-three Top1 agreement;
- mean cross-snapshot rank dispersion;
- cross-snapshot CAGR span.

## Secondary economic endpoints

- CAGR;
- MaxDD;
- Sharpe;
- annualized turnover;
- terminal equity.

Higher CAGR alone is not a PASS criterion.

## Directional success rule

V1_B is considered promising only if all of the following hold on the aggregate three-snapshot comparison:

1. direct ranking error improves: aggregate rank MAE decreases **or** aggregate pairwise ordering accuracy increases;
2. cross-snapshot Top1 agreement increases;
3. mean pairwise cross-snapshot rank Spearman does not decrease by more than `0.001`;
4. cross-snapshot CAGR span does not increase.

The full result remains reportable even if the gate fails. No parameter will be changed after seeing the result under the V1_B label.

## Fail conditions

- any use of non-matured target information;
- Repeat2 canonical baseline parity failure;
- source/environment gate failure;
- score-distribution preservation failure beyond floating-point tolerance;
- any post-hoc controller modification before reporting the frozen V1_B result.

## Interpretation boundary

This is a development robustness experiment on heavily burned Original149 data. It tests a control mechanism, not an investable performance claim and not a promotion test.