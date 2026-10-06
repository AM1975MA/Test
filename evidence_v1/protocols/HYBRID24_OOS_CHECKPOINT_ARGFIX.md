# Evidence V1 — Hybrid24 OOS checkpoint Stage19 argparse shadow fix

Status: **TECHNICAL AMENDMENT FROZEN BEFORE RERUN**

## Invalid technical run

Workflow run `37061720360` is **not evidence and did not materialize a checkpoint**.

The frozen MA3 panel rebuild and source-only Titanium rebuild both completed successfully. The canonical Stage19 runner then completed the Hybrid24 fit/simulation work but failed before `RESULT.json` was written because its local variable name `a` was used first for the argparse namespace and later overwritten by `producer.allocations_from_score(...)`. The result-construction line then attempted `a.prospective` on `AllocationResult` and raised:

`AttributeError: 'AllocationResult' object has no attribute 'prospective'`

Downstream checkpoint materialization, provenance, persistence and upload steps were skipped. No LTR checkpoint was read and no cascade metric was calculated.

## Permitted correction

The scientific source tree under `evidence_v1/source/baseline/` remains byte-identical and continues to be checked by the frozen source manifest.

For the rerun only, the workflow must create an isolated executable copy of the canonical runner under the isolated campaign root and apply exactly these textual variable-shadowing corrections:

1. `a=ap.parse_args()` -> `args=ap.parse_args()`
2. `if a.end_year<2017:` -> `if args.end_year<2017:`
3. `n_jobs=a.n_jobs,end_year=a.end_year` -> `n_jobs=args.n_jobs,end_year=args.end_year`
4. `if a.prospective else` -> `if args.prospective else`

The later line assigning:

`a=producer.allocations_from_score(...)`

must remain unchanged; all subsequent allocation/simulation references to `a.d1`, `a.d2`, `a.weight1`, `a.margin` remain unchanged.

The patched runner must be written beneath `ETF_TRAINER_V2_CAMPAIGN_ROOT/scripts/` so its existing `Path(__file__).resolve().relative_to(ROOT)` source-hash logic remains valid.

The workflow must fail if any of the four expected source fragments is absent before replacement or if their replacement counts are not exactly one each.

## What does NOT change

No change is permitted to:
- Original149 frozen data;
- MA3 panel builder;
- Titanium builder, seeds, horizons or models;
- Hybrid24 target, features, ExtraTrees/XGB configuration, annual maturity gates;
- ET/XGB rank conversion;
- tail blend `0.60/0.40`;
- lag smoothing `0.40/0.30/0.30`;
- tail power `1.10`;
- BASE/TAIL blend `0.475/0.525`;
- basket generator or basket seed;
- DDFirst/V6/HighCAGR24 simulation;
- transaction-cost assumptions;
- canonical 31.60% parity requirement;
- checkpoint materializer;
- anti-contamination rule forbidding any LTR/cascade input in Phase A.

## Scientific status

This amendment is an engineering/runtime correction only. It must not be interpreted as a new model configuration or a second research attempt. The first run produced no durable result and exposed no cascade performance.
