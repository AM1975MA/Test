# Evidence V3 — Dev72 universe freeze

Status: **PREREGISTERED BEFORE DATA FREEZE AND BEFORE ANY V3 PERFORMANCE TEST**

## Purpose

Create a new development universe that is independent of the burned Evidence V1/V2 development/diagnostic sets. The universe is for Evidence V3 development only; it is not a promotion holdout.

## Burned sets excluded

The freeze must exclude every ticker present in:
- frozen Evidence V1 `Original149`;
- frozen Evidence V1 `Holdout70`;
- the explicitly enumerated tested EU110/EU120 European-transfer ticker set relevant to the candidate pools.

The old deterministic `holdout100` specification is used only as historical design precedent; its ticker pool is not accepted blindly because it overlaps Holdout70.

## Universe shape

Exactly **72 ETFs**, split into six fixed macro categories with 12 names each:
- C01 US broad/style: 12
- C02 US sector/theme: 12
- C03 developed/global: 12
- C04 emerging: 12
- C05 bonds/cash/credit: 12
- C06 real assets: 12

## Selection rule

For each category, iterate through the preregistered ordered candidate list in `evidence_v3/src/freeze_dev72.py` and select the first 12 names that pass all engineering/coverage checks. Selection may use only ticker identity, category, price-data existence, coverage and OHLC coherence. **No return, CAGR, Sharpe, rank, label, target, model score or other performance statistic may be computed or used.**

## Data window and checks

- provider: Yahoo Finance via pinned `yfinance` in the workflow;
- requested start: 2004-01-01;
- last included date: 2026-07-31;
- at least 252 valid rows with date <= 2017-01-31;
- last available date must reach 2026-07-31;
- adjusted-OHLC convention: same-row Adj Close / raw Close factor applied to O/H/L, Adj Close used as Close;
- positive OHLC, non-negative volume, coherent high/low;
- unique dates and unique selected tickers;
- exactly one category per selected ticker.

## Failure rule

If any category cannot fill 12 names from the frozen candidate order, the freeze fails closed. The candidate pools must not be edited after inspecting any V3 model/performance result. An engineering-only expansion is permitted only before any V3 performance test and must be documented and frozen first.

## Post-freeze rule

Only after Dev72 is successfully frozen, committed and hashed may an Evidence V3 baseline/architecture test be preregistered. No performance test is allowed in the freeze workflow.