# P45 — Continuous Posterior Cadence Router

Date: 2026-09-28
Status: **PREREGISTERED BEFORE P45 RESULT INSPECTION**
Parent: `research/p44-bocpd-local-skill-router-20260928` at `a4d1f68e7ad32149fd16fa2f7c03e257eba0f57c`
Target repository: `AM1975MA/Trader_selector` only. `AM1975MA/Etf_trader` remains strictly read-only.

## 1. Research question

P44 showed that the frozen BOCPD relative-skill detector can leave the neutral state and that local Monthly routing was positive in aggregate, but hard projection to `{Annual, 50-50, Monthly}` was sensitive to a small number of wrong calls.

P45 tests one new hypothesis only:

> Keep the P44 detector completely frozen, but replace hard state quantization with a continuous posterior weight.

No detector parameter, feature, maturity rule, producer component or downstream portfolio rule changes.

## 2. Frozen inputs and producers

Exactly the same objects validated by the P43/P44 parity gates are reused:

- canonical Annual V2 producer;
- P41 full Monthly expanding walk-forward producer;
- exact same 149 ETF universe and source vintage;
- exact same Stage19 architecture, score construction, ET/XGB agreement logic, allocation logic, risk controls, BIL/SHV cash sleeve, stop logic, slippage and 10 bp traded-notional transaction cost;
- exact same monthly shadow outcomes and relative-skill observations used by P43/P44.

P45 does not refit or change Annual or Monthly.

## 3. Causal shadow-skill stream

Use the same frozen P43/P44 skill definition for every fully matured Annual/Monthly shadow interval `k`:

`g_A,k = log1p(R_A,k)`

`g_M,k = log1p(R_M,k)`

`skill_k = (g_M,k - g_A,k) / (abs(g_M,k) + abs(g_A,k) + 1e-12)`

with `skill_k in [-1,+1]`, positive favoring Monthly.

At signal date `t`, only intervals satisfying strictly:

`outcome_end_k < signal_date_t`

may update the router.

## 4. BOCPD detector — frozen from P44

P45 uses the P44 BOCPD implementation unchanged.

Fixed constants:

- observation variance: `sigma2 = 1/3`;
- prior regime mean: `0`;
- prior regime-mean variance: `1/3`;
- constant hazard: `1/12` per matured monthly observation;
- exact P44 Gaussian conjugate update and run-length posterior recursion.

For each possible current run length `r`, P44 maintains posterior regime-mean parameters `(mu_r, var_r)` and run probability `q_r`.

The frozen posterior probability that Monthly has positive local relative skill is:

`p_monthly = sum_r q_r * Phi(mu_r / sqrt(var_r))`

where `Phi` is the standard Normal CDF.

Before any matured observation, `p_monthly = 0.5`.

No P44 BOCPD constant may be changed in P45.

## 5. P45 decision rule — continuous posterior weighting

This is the only substantive P45 change.

At each signal date:

`w_monthly,t = p_monthly,t`

`w_annual,t = 1 - p_monthly,t`

The weight is used continuously with no thresholding or discretization.

The exact same weight pair is applied to both objects previously blended in P42/P44:

1. final Annual vs Monthly producer score;
2. Annual vs Monthly Stage19 ET/XGB model-agreement rank inputs.

Everything downstream remains frozen.

### Explicitly forbidden in P45

No:

- probability clipping;
- probability floor/ceiling;
- temperature scaling;
- exponentiation;
- logistic remapping;
- shrinkage toward 0.5;
- minimum-observation override;
- hysteresis;
- persistence rule;
- transaction-cost-aware threshold;
- volatility scaling;
- different weights for score and agreement ranks;
- detector retuning.

The raw P44 posterior probability is the portfolio blend weight.

## 6. Cold start

Before the first matured shadow outcome, BOCPD prior probability is exactly `0.5`, so P45 is exactly P42 50/50.

After each matured observation, P45 immediately uses the updated posterior probability at the first causally eligible signal. There is no special five-observation cold-start rule because P45 explicitly tests posterior-confidence weighting rather than state classification.

## 7. Evaluation and parity gate

Primary replay period and execution calendar are unchanged from P43/P44.

Before P45 performance is opened, the local reconstruction must again reproduce the frozen references:

- Annual CAGR `0.4314595242029944`, MaxDD `-0.2503576476357465`, Sharpe `1.3635086089607882`, turnover `12.807083509113824`;
- P41 Monthly CAGR `0.37063594291857493`, MaxDD `-0.3516524326917191`, Sharpe `1.2717391106878997`, turnover `13.745053103725073`;
- P42 50/50 CAGR `0.4475354991771064`, MaxDD `-0.27063751068647446`, Sharpe `1.4291508593820934`, turnover `13.104831222285583`.

If parity fails, P45 performance remains unopened.

## 8. Preregistered support gate

P45 is supported only if all conditions hold in the single frozen run:

1. strict causal audit passes;
2. full-period CAGR > P42 static 50/50;
3. full-period Sharpe >= P42 static 50/50;
4. MaxDD is not worse than Annual by more than 2.0 percentage points;
5. CAGR delta vs P42 is positive in both `2017–2022` and `2023–2026-07-01`.

Posterior-weight distribution, turnover, calendar-year deltas, selection agreement and attribution are diagnostics only.

## 9. Anti-rescue rule

P45 is one test. After its result is visible, do not rescue it by changing the BOCPD hazard, prior, observation variance, transforming `p_monthly`, clipping the weights, adding inertia or tuning any threshold.

Any different mapping must be a separately numbered experiment with a new preregistration.

## 10. Required artifacts

Save at minimum:

- `PROTOCOL.md`;
- P45 runner/source;
- `ROUTER_TRACE.csv` including `p_monthly`, `w_annual`, `w_monthly` and BOCPD diagnostics;
- `SHADOW_SKILL.csv`;
- `PARITY_AUDIT.json`;
- `CAUSAL_AUDIT.json`;
- `ANNUAL_COMPARISON.csv`;
- `RESULT.json`;
- `FINAL_DECISION.md`.

No write is permitted to `AM1975MA/Etf_trader`.
