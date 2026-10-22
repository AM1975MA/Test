# L10.D — Independent analytical mathematics for ETF winner/loser discrimination

**Status: RESEARCH PLAN ONLY; NO TEST EXECUTED OR MODEL PROMOTED.**
Recorded on 2026-10-22 following L10 and L10.C. Scope: original 149 ETFs,
500 canonical 24-name baskets, frozen 125 corrected features and 101 mature OOS
calendar months, plus truly new never-used chronological vintages when available.
V2 production, L00-L10 frozen references, existing experiments remain unchanged.

## Non-negotiable principle

Analytical mathematics / economophysics is an **independent evidence channel**,
not merely input features for machine learning. The existing CORRECTED Pairwise127
provides the general rank, while L10_TOP5_PAIR127 is a *candidate retriever*, not
an automatic buy signal. A separate causally computed analytical discriminator
should independently estimate whether a candidate is a relatively strong
continuation/opportunity, an unstable apparent winner, or an extreme-loss risk.
Do not force these into a single blended score before validating each role.

## Mathematical families already discussed in the research lineage

1. **Relative alpha / factor residual:** estimate trailing, regularized beta and
   residual relative momentum (not absolute market drift). Example exploratory
   statistic: residual return at horizon h through t,
   A_{i,t,h} = R_{i,t-h:t} - beta_hat_{i,t,h} * R_{benchmark,t-h:t}.
   Beta/benchmark/covariance estimators must use only times <=t.
   Explicitly compare 21/63/126-day causal horizons without retrospective
   picking the best horizon from the evaluated 2018–2026 years.
2. **Persistence / opportunity / efficiency:** quantify rank stability, trend
   persistence versus volatility and downside, robust normalized residual
   positioning and economically interpretable opportunity signals. Recover prior
   A0/A4 Opportunity+Persistence tests and provenance before porting formulas.
3. **Analytical downside and crisis resilience:** drawdown, down-volatility,
   left-tail conditional losses, skew, conditional beta/correlation shock and
   recovery behavior from trailing observed data; evaluate versus future
   absolute next-21-trading-day loss <= -10% and future worst-three basket ETFs.
   No future returns or hindsight risk tiers inside signal features.
4. **Econophysics / distributional state:** rolling correlation eigen-spectrum,
   RMT effective rank/eigenvalue concentration, multiscale volatility and
   change-point methods (e.g., CUSUM/BOCPD), with causal delays; these can
   describe state and confidence without necessarily selecting an ML expert.
   **Caveat:** L03 already rejected the *specific* 63-day market+RMT logistic
   expert-switching gate (run 39674680942); do NOT silently promote or
   repackage that rejected test. RMT as a state descriptor is a distinct
   hypothesis requiring separate tests.
5. **Rank confidence / stability:** quantify uncertainty of adjacent places and
   robust comparisons using score-margin, perturbation of past-only windows,
   bootstrap through time, cross-sectional robust z-scores and ranks. Do not
   assume a raw ML score margin is calibrated probability of winning.

These are **research families and conceptual formulas**, not claims of
current out-of-sample predictive accuracy. Audit source availability, exact
implementations, calendar alignment and missingness before declaring any
analytical indicator operational. Maintain the analytical lineage as an
independent model/source with own version and tests, not silently append all
terms to the 125-feature frozen base.

## Ordered one-change research gates

**D0 — Source audit, NO score fusion.** Inventory original analytic A0/A4,
OASIS, F3/H1/H3, RMT/other work and provenance. Identify genuinely
train-free analytical rules versus fitted statistical estimators; ensure
point-in-time inputs. Do not recreate a variant when an authenticated
implementation is already present.

**D1 — Pure analytical discrimination, prediction-only.** Freeze the L10.C
CORRECTED Top3, Top5 added candidates, and capacity-matched CORRECTED rank4+
controls. Evaluate one predeclared analytical signal **on precisely the same
names and dates**, first for the candidates who are *not* common to both models.
Primary metrics: separate best-ETF candidate detection, severe 10% future loss
discrimination, bottom-three rank discrimination, calibrated rank/conditional
regret; monthly aggregates, six-calendar-month paired block bootstrap. Compare
to unmodified reference and a constant/prior-only score. Do not select signal
or coefficients based on 2018–2026 outcomes.

**D2 — Conditional reranking, ONE rule at a time.** If D1 establishes an
independent useful signal, test one pre-registered *causal* analytical reranking
or risk-aware confirmation rule, with any thresholds estimated on **past
maturity-complete** training labels only. Explicitly preserve/general-rank the
original CORRECTED names, and determine whether novel Top5 winners can
replace weak original selections without giving excessive budget to losers.
Do not introduce ML retraining, risk override, new features and allocation
changes simultaneously.

**D3 — Independent complementarity to ML.** Only after D1/D2, separately
compare analytical-only, frozen CORRECTED-only, ML two-stage-only, and
analytical+ML (single extra intervention) under exactly matched Top2/Top3
policies. Require improved realized invested rank / winner weight without
material increase in severe-loss weight or 21D regret. Then run same 10bp
one-way next-open executable replay as L07–L10, with no CAGR-based tuning.

## Governance

149 frozen ETFs; canonical 500 baskets are overlapping, not independent
statistical draws. Labels mature before every annual/walk-forward cutoff.
Missing and malformed mathematical features are fail-closed; warmup NaN
must be distinguished from errors. Data from 2018–2026 is heavily reused
and **NOT** a virgin holdout. No launch or production/V3 reference promotion
without an independently precommitted newer vintage and explicit approval.
Keep rejected analytical methods and all intermediate results in the V3
experiment registry, alongside ML results.

**Status as of this note:** no L10.D results, no measured improvement, no
new estimator trained and no economic simulation performed. This document
reserves the analytical channel as a first-class independent line of research.
