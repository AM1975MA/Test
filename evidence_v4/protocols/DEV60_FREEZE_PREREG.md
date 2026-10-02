# Evidence V4 — Dev60 universe freeze

Status: **PREREGISTERED BEFORE FREEZE AND BEFORE ANY V4 PERFORMANCE RUN**

## Purpose

Freeze a new 60-ETF development universe for the magnitude-plus-direction architecture derived from the Evidence V3 diagnostic. Dev60 is development data, not a promotion holdout.

## Candidate order

V4 must reuse exactly the candidate categories and order already frozen before V3 performance in `evidence_v3/src/freeze_dev72.py`. The V4 freezer may not add, delete or reorder candidate names.

## Burned/tested exclusions

Exclude the union of:
- Evidence V1 Original149;
- Evidence V1 Holdout70;
- tested EU110 reference names;
- frozen V3 Dev72.

Because Dev72 was itself disjoint from the first three sets, the expected burned/tested union size is 400 unique tickers.

## Universe shape

Exactly **60 ETFs**, 10 per category:
- C01 US broad/style: 10
- C02 US sector/theme: 10
- C03 developed/global: 10
- C04 emerging: 10
- C05 bonds/cash/credit: 10
- C06 real assets: 10

## Selection rule

For each category, iterate through the already-frozen V3 candidate order and choose the first ten names that:
1. are not in the burned/tested union;
2. have valid Yahoo Finance data under the fixed coverage/coherence checks.

No return, CAGR, Sharpe, target, label, model score, winner rank or any other performance statistic may be computed or used.

## Fixed data checks

- requested start: 2004-01-01
- final included date: 2026-07-31
- at least 252 valid adjusted-OHLC rows with date <= 2017-01-31
- data must reach 2026-07-31
- adjusted O/H/L by same-row Adj Close / raw Close factor; Adj Close becomes Close
- positive OHLC, non-negative volume, unique dates, coherent high/low
- exactly one frozen macro category per ticker
- exactly 60 unique selected tickers
- zero overlap with the 400-name burned/tested union

## Failure rule

If any category cannot fill 10 names from the pre-existing V3 candidate order, the freeze fails closed. No candidate-order engineering is permitted after viewing any V4 performance result.

## Post-freeze rule

Only after the Dev60 dataset, manifest, hashes and provenance are committed may the two-stage magnitude-plus-direction test be executed. The entire architecture must be preregistered before that first performance run.