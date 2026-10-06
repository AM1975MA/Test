# ETF_TRADER_NEGATIVE_FEEDBACK_V1

**Status:** ACTIVE — NEW RESEARCH LINE  
**Created:** 2026-10-03  
**Branch:** `research/etf-trader-negative-feedback-v1`

## Purpose

Turn canonical ETF_trader V2 from a purely open-loop predictor into a strictly causal closed-loop walk-forward system in which **matured ex-post prediction error becomes an input for future decisions**.

This line is deliberately separate from:

- `gap_analysis` / Original149 vs EU120 causal decomposition;
- Trader_selector / P45 routing research;
- pure numerical-stability controls.

## Core hypothesis

If ETF_trader has a persistent, regime-dependent prediction/ranking bias, then a slowly updated negative-feedback state derived only from **already matured historical errors** can reduce future error and decision instability without using future information.

At signal date `t`, the feedback state may contain only errors from predictions whose target horizon has fully matured before `t`.

## Closed-loop form

Base model:

`score_t = f(X_t)`

Matured error state:

`E_t = update(E_{t-1}, error_{<=t-maturity})`

Closed-loop score:

`score_corr_t = score_t + g(E_t)`

The correction must be negative feedback: persistent over-estimation must reduce future score/confidence; persistent under-estimation may increase it within preregistered bounds.

## V1 scientific objective

Primary objective is **error convergence / robustness**, not CAGR maximization.

Primary measurements:

1. causal prediction/rank error before vs after feedback;
2. variance and persistence of error;
3. Top1/Top2 stability;
4. sensitivity of decisions to the three repeated Yahoo snapshots;
5. only then CAGR / MaxDD / Sharpe as secondary economic outcomes.

## Non-negotiable rules

- strict walk-forward causality;
- no use of an error before its target is fully observable;
- no Holdout70 promotion use;
- no ex-post parameter sweep to select the best CAGR;
- Original149 remains development/burned diagnostic data;
- source/data hashes and environment are frozen for every test;
- failed technical runs are not model evidence;
- all V1 controller parameters are preregistered before the result is observed.

## First experiment

`NF_V1_A_CAUSAL_RESIDUAL_FEEDBACK`

A minimal feedback overlay is applied to canonical V2 using only matured errors. It is compared against the untouched canonical baseline on the same frozen raw snapshot and then across the three repeated Yahoo snapshots.

The first experiment is intentionally simple. It is designed to answer whether closed-loop error feedback moves the system toward convergence before introducing a learned residual model or adaptive expert weighting.
