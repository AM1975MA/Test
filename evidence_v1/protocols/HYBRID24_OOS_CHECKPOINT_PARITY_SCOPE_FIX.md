# Evidence V1 — Hybrid24 OOS checkpoint parity-scope correction

Status: **TECHNICAL / PROVENANCE AMENDMENT FROZEN BEFORE RERUN**

## Why this amendment exists

The original Phase-A preregistration required the canonical basket runner to reproduce a **31.60% CAGR** before the Hybrid24 OOS checkpoint could be persisted.

A provenance audit performed before any LTR→Hybrid24 cascade result was observed showed that this comparison mixed two different statistics and two different allocation rules:

1. the canonical Hybrid24/HighCAGR24 runner builds **500 canonical baskets of 24 ETFs** and reports the **mean CAGR across those baskets**;
2. the separately certified **31.603994562922105% CAGR** is from the controlled V2 **full-universe replay**, where `BM` contains one basket with all 149 candidates and the allocation uses Stage19 `current_plus_models_riskoff` confidence weighting.

The controlled full-universe replay is valid evidence for its own experiment, but it is not a homogeneous parity target for the 500x24 canonical basket runner used to materialize the Hybrid24 OOS score.

## Corrected engineering gate

The Phase-A checkpoint may pass only if all of the following remain true:

- Original149 frozen data and source manifests pass byte/hash verification;
- MA3 feature/cluster rebuild completes from frozen source and data;
- Titanium source-only rebuild completes and maturity checks pass;
- Hybrid24 annual fit audit is entirely maturity-safe;
- no historical score/path/cluster/basket artifacts are consumed productively;
- canonical baskets are generated from source with seed `20260721`;
- generated canonical basket SHA256 is exactly `36a45916b5d8191f3ccd206f39bf3fd3f1ed4bcaffd474e352b69c598f2b6a5e`;
- the canonical basket runner produces a finite full-window HighCAGR24 mean-basket CAGR;
- the materialized OOS score has exactly 114 signal dates from `2017-01-31` through `2026-06-30`, unique `(signal_date,ticker)` keys, and no non-finite final Hybrid24 score rows;
- the workflow does not read the LTR checkpoint or calculate any cascade metric.

The 31.6039946% full-universe V2 CAGR is recorded only as a provenance reference and **must not be used as a gate for the basket-runner metric**.

## What does not change

This amendment does not change:

- the Hybrid24 target;
- ExtraTrees/XGB model configuration;
- annual expanding fit schedule or maturity rule;
- ET/XGB blend;
- 40/30/30 lag smoothing;
- tail power 1.10;
- BASE/TAIL 0.475/0.525 blend;
- canonical basket generator;
- DDFirst/V6/HighCAGR24 logic;
- transaction costs;
- LTR checkpoint;
- cascade K (Top5 remains the only permitted shortlist for Phase B);
- any Phase-B decision rule.

## Scientific status

This is a scope/provenance correction made **before Phase B is executed**. It does not expose or use cascade performance and therefore does not constitute an additional model attempt or ex-post tuning.
