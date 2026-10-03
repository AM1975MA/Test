# PREREGISTRATION — NF_V1_A_CAUSAL_RESIDUAL_FEEDBACK

Date frozen: 2026-10-03

## Question

Can a strictly causal negative-feedback controller, driven only by matured ex-post model error, reduce ETF_trader V2 prediction/ranking error and decision instability in walk-forward evaluation?

## Data contract

Development universe: Original149.  
Canonical perturbation set: the three consecutive frozen Yahoo/yfinance 0.2.66 snapshots from workflow run `37121749852` (`_repeat1`, `_repeat2`, `_repeat3`).

The controller must be evaluated on identical source/environment contracts for all snapshots.

## Baseline

Canonical ETF_trader V2 Annual path, unchanged.

## Feedback state

V1 uses a deliberately low-complexity residual state. For each ticker, a signed matured residual is maintained using an exponentially weighted moving average.

A residual becomes eligible only after the forward target used for that prediction has fully matured. No partial or future return may enter the state.

Preregistered controller:

`bias_i,t = (1-alpha) * bias_i,t-1 + alpha * residual_i,matured`

`score_corr_i,t = score_i,t - lambda * clip(bias_i,t, -cap, +cap)`

The sign convention is chosen so persistent over-estimation is penalized and persistent under-estimation is relieved.

## Frozen V1 parameters

- `alpha = 0.20`
- `lambda = 0.50`
- `cap = 0.20`
- minimum matured observations before correction: `3`
- no parameter sweep in V1
- no parameter chosen using CAGR

These values are engineering-scale defaults selected before observing NF_V1_A results. They are not claimed optimal.

## Evaluation order

1. Verify untouched baseline parity on `_repeat2`.
2. Run feedback controller on `_repeat2`.
3. Measure pre/post error metrics.
4. Run exactly the same controller on `_repeat1` and `_repeat3` without modification.
5. Measure whether cross-snapshot decision/CAGR dispersion decreases.

## Primary endpoints

The experiment is a robustness/error-convergence test. Primary endpoints are:

- mean absolute matured residual: corrected vs baseline;
- rank error / rank correlation: corrected vs baseline;
- temporal residual autocorrelation / persistence;
- Top1 agreement across `_repeat1/_repeat2/_repeat3`;
- Top1/Top2 turnover across perturbation snapshots;
- dispersion of corrected scores/ranks across snapshots.

## Secondary endpoints

- CAGR;
- MaxDD;
- Sharpe;
- turnover.

A higher CAGR alone is **not** a PASS criterion.

## Directional success rule

V1 is considered promising only if the closed-loop controller reduces at least one direct error metric **and** improves cross-snapshot decision stability without materially worsening the other direct error metrics. Economic metrics are reported but do not override a robustness failure.

## Fail conditions

- leakage / use of non-matured error;
- inability to reproduce canonical baseline on the frozen input;
- correction increases instability across all three snapshots;
- result depends on post-hoc parameter choice.

## Next steps only if V1 is promising

Potential V2 controllers, not authorized in this preregistration:

- cluster-level residual feedback;
- dynamic ET/XGB expert weighting from matured loss;
- learned residual model;
- confidence/exposure feedback driven by prediction instability.
