# Evidence V1 — Hybrid24 canonical OOS checkpoint

Status: **PREREGISTERED ENGINEERING GATE BEFORE EXECUTION**

## Purpose

Materialize the canonical Hybrid24 OOS cross-sectional signal before any LTR→Hybrid24 cascade test.

This run is **not a cascade performance test**. It must not read the LTR checkpoint, compute shortlist intersections, or report LTR/Hybrid cascade returns.

## Frozen source-only chain

Inputs are limited to:
- frozen Original149 raw ticker CSV data under `evidence_v1/data/original149/`;
- frozen baseline source under `evidence_v1/source/baseline/etf_trader_v2/`;
- locked Evidence V1 numerical environment.

The workflow must rebuild from source:
1. MA3 source-only raw feature panel and cluster audit;
2. source-only Titanium `TIT_R` and annual-model audits;
3. canonical Hybrid24 ensemble using `fit_ensemble_producer` / `fit_hybrid_producer`;
4. the canonical Stage19/HighCAGR24 baseline runner, solely as a parity/causality engineering gate.

Historical score/path/cluster/basket artifacts are forbidden as productive inputs.

## Canonical Hybrid24 score

The materialized signal must preserve the promoted source implementation:
- corrected target `0.45*r21^1.5 + 0.35*r42^1.5 + 0.20*r63^1.5`;
- ExtraTrees and XGB annual expanding maturity-safe models;
- cross-sectional component ranks;
- tail blend `0.60*ET + 0.40*XGB`;
- lag smoothing `0.40/0.30/0.30`;
- tail power `1.10`;
- final score `0.475*BASE + 0.525*smoothed_tail^1.10`.

## Checkpoint output

Durable path after a passing run:

`evidence_v1/checkpoints/hybrid24_oos_v1/`

Required files:
- `OOS_SCORES.csv`
- `FIT_AUDIT.csv`
- `CALENDAR.csv`
- `BASELINE_PARITY.json`
- `CHECKPOINT_MANIFEST.json`
- `PROVENANCE.json`

`OOS_SCORES.csv` must be keyed uniquely by `(signal_date, ticker)` and contain at least:
- `BASE`
- `ET_RANK`
- `XGB_RANK`
- `TAIL_HYBRID`
- `HYBRID24_SCORE`
- `HYBRID24_RANK`
- `HYBRID24_POSITION`

Expected OOS calendar: exactly 114 monthly signal dates from `2017-01-31` through `2026-06-30`.

## Fail-closed causality/parity gate

Before the checkpoint is persisted:
- every Hybrid24 annual fit audit row must be maturity-safe;
- Titanium and cluster causality gates in the canonical runner must pass;
- the canonical source-only runner must report no consumption of historical scores, paths, cluster membership, or basket membership;
- baskets must be generated from source;
- canonical full Original149 HighCAGR24 CAGR must reproduce the Evidence V1 baseline at **31.60% when rounded to four decimal places as a fraction (`0.3160`)**.

This is an engineering parity gate only. It does not create a new performance hypothesis.

## Anti-contamination rule

The materialization workflow must not read any file under:
- `evidence_v1/checkpoints/retriever_ltr_v1/`
- `evidence_v1/results/retriever_ltr_v1/`

and must not calculate any LTR/Hybrid24 intersection or cascade metric.

Only after this checkpoint is durable and its manifest/hash registered may a separate cascade protocol be preregistered.

## Frozen materializer

Path:
`evidence_v1/src/materialize_hybrid24_oos_checkpoint.py`

Git blob:
`e34ef851dde41540ca55c572565a770c9b5c8137`
