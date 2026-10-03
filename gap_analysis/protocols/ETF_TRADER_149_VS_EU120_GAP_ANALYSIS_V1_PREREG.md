# ETF_TRADER_149_VS_EU120_GAP_ANALYSIS_V1 — PREREGISTRATION

Date: 2026-10-03
Status: FROZEN BEFORE EXECUTION

## Objective

Explain the performance gap observed when replaying the canonical ETF_trader logic on the frozen Original149 universe versus the deterministic EU120 universe. Before attributing any difference to universe composition, establish whether the current ~31.604 pp result and the historical ~43 pp result are directly comparable.

The 31 pp vs 43 pp discrepancy is a mandatory first-stage forensic gate. A difference of roughly 12 percentage points is too large to treat as numerical noise and is explicitly hypothesized to arise from different source code, data lineage/data vintage, cluster reconstruction, execution contract, or metric definition.

## Non-negotiable execution order

No 149-vs-EU120 economic conclusion may be drawn until Stage 0 is completed.

### Stage 0 — 31 pp vs historical 43 pp provenance/parity audit

Identify the exact artifacts behind:

1. current canonical result: approximately 31.604 pp;
2. historical result: approximately 43 pp.

For each result freeze and record:

- repository, branch, commit SHA and source-file blob SHA;
- complete executable source chain;
- universe membership and ticker count;
- raw market-data source/provider;
- outer raw package/snapshot hash and, where applicable, inner member hash;
- data vintage / download timestamp / last observation date;
- adjusted-vs-unadjusted OHLC semantics;
- corporate-action treatment;
- cluster source, cluster algorithm, seed and persistent-cluster mapping;
- feature-builder source and feature count;
- model/producer source and model parameters;
- training windows, maturity cutoffs and retraining cadence;
- selection/basket construction;
- execution timing (signal date, D+1/open/close assumptions);
- transaction costs, slippage and turnover definition;
- cash/defensive sleeves, stops, overlays and alternative-routing rules;
- evaluation start/end dates;
- exact performance formula and annualization convention.

### Stage 0A — native replay parity

Reproduce both numbers using each result's own frozen source and own frozen inputs.

A historical number is considered reproducible only if the rerun agrees with the archived result within numerical tolerance. If the archived result cannot be rerun because raw bytes or executable source are unavailable, classify it as `HISTORICAL_REFERENCE_NOT_REPRODUCIBLE` and preserve the evidence explaining the missing dependency.

### Stage 0B — matched-contract comparison

Normalize the two runs to the same evaluation contract wherever possible:

- identical universe;
- identical start/end dates;
- identical price fields;
- identical execution timing;
- identical cost assumptions;
- identical annualization/performance formula.

This stage determines whether the ~12 pp discrepancy survives metric-contract normalization.

### Stage 0C — crossed source/data replay

If both source chains and both raw vintages are recoverable, execute the crossed matrix:

| Code / pipeline | Current raw/source snapshot | Historical raw/source snapshot |
|---|---:|---:|
| Current canonical implementation | required | required if available |
| Historical implementation | required if available | required |

The purpose is to separate:

- `DATA_VINTAGE_EFFECT`;
- `SOURCE_CODE_EFFECT`;
- `CLUSTER_RECONSTRUCTION_EFFECT`;
- `EXECUTION_CONTRACT_EFFECT`;
- `METRIC_DEFINITION_EFFECT`.

Where possible, perform one-factor-at-a-time substitutions after the crossed replay, beginning with raw data / cluster membership because prior ETF_trader source-fidelity work has shown that cluster raw-vintage differences can materially propagate into economic results.

### Stage 0 decision gate

Proceed to Original149 vs EU120 only after one of the following is true:

1. the 31 pp and 43 pp results are reproduced and the delta is causally attributed to one or more frozen lineage differences; or
2. the historical 43 pp result is formally classified as non-reproducible, with the unrecoverable dependency documented; or
3. after full contract normalization, the residual unexplained difference is <= 1.0 percentage point.

If none applies, the 149-vs-EU120 comparison is blocked as `BASELINE_LINEAGE_UNRESOLVED`.

## Stage 1 — canonical Original149 replay

Only after Stage 0 passes, run the frozen canonical ETF_trader engine on Original149 and require parity with the canonical benchmark produced by the matched source/data contract established in Stage 0.

The benchmark is not assumed in advance to be 31.604 pp or 43 pp; Stage 0 determines which number is a valid canonical reference under the final matched contract.

## Stage 2 — deterministic EU120 replay

Run the exact same frozen engine, execution assumptions, metric calculation and data-lineage rules on the deterministic EU120 universe.

No model tuning, feature changes, parameter changes, alternate seeds, alternate costs, or universe edits are permitted between Stage 1 and Stage 2.

## Stage 3 — attribution

Report at minimum:

- canonical Original149 result;
- EU120 result;
- absolute delta in percentage points;
- per-cluster contribution where the architecture supports it;
- turnover and cost delta;
- coverage / missing-history delta;
- concentration delta;
- exposure/regime differences;
- whether the economic gap is primarily attributable to universe composition or to data/source lineage.

## Required artifacts

Persist in the repository:

- `SOURCE_LINEAGE_31PP.json`;
- `SOURCE_LINEAGE_43PP.json`;
- `PARITY_31PP.json`;
- `PARITY_43PP.json`;
- `MATCHED_CONTRACT_COMPARISON.json`;
- `CROSSED_REPLAY_MATRIX.json` when technically possible;
- `BASELINE_LINEAGE_DECISION.md`;
- Original149 canonical result;
- EU120 canonical result;
- final gap-attribution report;
- hashes of all executable sources and raw-data manifests used.

## Anti-overfitting / anti-retrofitting rule

The purpose of the 31-vs-43 audit is forensic, not optimization. No source, dataset, seed, feature, or execution setting may be selected merely because it recovers the higher historical CAGR. The valid canonical configuration is the one supported by recoverable provenance and the frozen historical execution contract, not the one with the best performance.
