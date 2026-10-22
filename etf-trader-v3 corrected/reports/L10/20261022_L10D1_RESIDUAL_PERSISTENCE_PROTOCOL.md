# ETF Trader V3 Corrected — L10.D1 independent mathematical discriminator

**Frozen before test**, 22 October 2026, branch `research-v3-l10d-analytic-signal-20261022`.
No ML refit, no weight optimization, no CAGR-based design, no V2 modification.
Predictive/factual diagnostic only; historical 2018–2026 is not a virgin holdout.

## Audit of recovered earlier mathematics

Original private repository `AM1975MA/Etf_trader` currently contains authentic
source-only `src/etf_trader/source_only/a4_persistence_opportunity.py`,
`a4_phase.py`, `a4_hazard.py`, `a4_rankers.py` and
`results/A4_SOURCE_ONLY_CANONICAL_RESULT_20260921.json`.
The A4 source-only paired study found mean CAGR A0 14.3887%, A4 14.7263%,
versus prior V2 Golden 21.6541%; **do not present A4 as validated/production ready**.
A4 opportunity ranker is supervised, and persistence bonus depends on incumbent
and fitted survival/momentum scores. It is not a clean analytic-only alternative.
The L03 63-day RMT expert switch was rejected (run 39674680942).
We therefore predeclare one truly deterministic analytic-only diagnostic,
inspired by A4's causal persistence/resilience remit but independent of A4 ML.

## D1 isolated signal (ONE FORMULA; NO parameter sweep)

From the canonical adjusted daily Close series, let
`r_i,s = log(C_i,s / C_i,s-1)` and `r_M,s = 0.5*r_SPY,s+0.5*r_VTI,s` be the fixed market-composite return.
Beta on each day is estimated from the *preceding*, shifted 126-session
rolling covariance of asset returns with SPY divided by trailing composite-return variance;
at least 100 points are required. Define residual
`e_i,s = r_i,s - beta_i,s * r_M,s`.
For a signal date t compute **residual persistence / downside**
`AP_i,t = sum_{s=t-62}^t e_i,s / sqrt(sum_{s=t-62}^t min(e_i,s,0)^2)`.
A complete 63-session residual window is required. Nonfinite or zero
denominators => missing (fail closed); no retrospective repair.
All inputs end on the signal close, before a next-open trade.
No fitted ML, forward label, cost, future return, or cross-validation choice
is used to construct the signal. We do not presume this ratio predicts alpha.

## Matched frozen controls

- Original 149 ETFs, canonical 500x24 basket SHA
  `36a45916b5d8191f3ccd206f39bf3fd3f1ed4bcaffd474e352b69c598f2b6a5e`.
- Source raw adjusted OHLCV 39482809691 (`v2-deep-leaf-frozen-raw`),
  source frozen OOS `OOS_SCORES.csv` run 39700865721,
  101 fully 21D-matured signal dates with identical ticker keys and outcomes.
- `BASE`: first three by frozen CORRECTED.
- `UNION`: BASE + distinct L10_TOP5_PAIR127 Top-3 candidates.
- `MATCHED`: BASE + equal count of rank4+ CORRECTED candidates (as L10.C).
- `UNION_ANALYTIC` and `MATCHED_ANALYTIC`: same independent analytic score
  sorts the same-budget pools and picks three, without changing weights
  from 50/30/20. This is a diagnostic selection rule, not deployment.

## Predeclared acceptance metrics and safeguards

First verify as-of-date invariance by perturbing later closes; no future prices
can change an earlier signal, no missing value silently turned into 'safe'.
Measure eligible analytical coverage per month. Compare *the exact same
eligible basket/date samples* across BASE and both analytical pools; report all
months, number eligible and incomplete cases. If coverage <90%, report limited
comparability and do not promote.

Primary mathematical signal assessment: conditional within-UNION basket
Spearman between analytic score and realized next21D return, versus frozen
CORRECTED score on the *same candidates*, paired by calendar month.
Also report universe-wide Spearman IC and unique ETF-month within-UNION
discrimination of future absolute loss <= -10% (ROC-AUC, only when both
classes are present). Infer nothing from months without actual loss events.

Functional diagnostic (same Top3 50/30/20) compares UN- and MATCHED-analytic
to BASE on winner weight, severe-loss weight, weighted future rank, 21D
weighted regret, and bottom-three weight; never choose rule based on CAGR.
Compute 101 monthly means first, six-calendar-month paired circular bootstrap
6000 draws; multiple endpoints exploratory; sensitivity by year. Never
treat 500 overlapping baskets as 500 independent monthly trials.

No economic test and NO decision to promote solely from this stage;
if and only if independent analytical discrimination demonstrates utility,
a separately defined one-intervention D2 conditional-reranking experiment may
be considered. Current period repeatedly researched, no virgin holdout.

## Engineering preregistration amendment before examining any D1 outcome

Initial Actions run **39738202561** FAILED before loading target predictions into the evaluation function. The synthetic point-in-time assertion caught a deterministic formula defect: original self-benchmark SPY-on-SPY beta makes its residual identically zero, with zero downside denominator. No D1 outcome/metric was produced. Corrected benchmark once, **prior to any outcome read**, to the fixed equal-weight daily SPY/VTI return composite for every ETF, including SPY and VTI. Keeps the 126-session shifted beta, 63-session residual/downside score, cutoff and all acceptance metrics unchanged. No hyperparameter search or data-dependent formula decision. Retain failed run ID as provenance.
