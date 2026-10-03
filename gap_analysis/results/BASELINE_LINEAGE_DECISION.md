# Baseline lineage decision — 31.604% vs historical 43.146%

Date: 2026-10-03  
Protocol: `ETF_TRADER_149_VS_EU120_GAP_ANALYSIS_V1`

## Decision

**STAGE 0 PASS — baseline lineage resolved.**

The approximately 12 percentage-point discrepancy is real and reproducible. The exact difference is:

- Historical Original149 Annual V2 CAGR: **43.1459524203%**
- Fresh Original149 same-source CAGR: **31.6039945629%**
- Fresh minus historical: **−11.5419578574 percentage points**

The comparison is between the same 149-candidate economic universe, the same 2017-02-01 to 2026-07-01 evaluation interval (2366 sessions), the same canonical productive V2 source chain, the same Annual V2 metric identity, and the same adjusted-OHLC construction convention.

The material changed factor is the **raw market-data vintage / raw bytes**.

## Evidence

### Historical 43.145952%

The historical reference is tied to five frozen OHLCV Parquet matrices with explicit SHA256 hashes and to canonical productive-source Git blob hashes. Its archived parity audit reproduces the Annual V2 CAGR exactly.

### Fresh 31.603995%

The fresh comparison downloaded Yahoo Finance data with `yfinance 0.2.66` on 2026-10-02, requested 2004-01-01 through 2026-08-01 exclusive, and generated adjusted OHLC by applying `Adj Close / raw Close` to same-row OHLC while retaining raw Volume.

Before model execution the workflow hash-gated the productive V2 source files to the canonical historical blobs and passed that gate. The valid later replay reproduces 31.6039945629% on Original149.

### Propagation into model state

The raw-vintage change does not merely alter final realized prices. It changes reconstructed intermediate state:

- Titanium historical SHA256: `8ec29dd155583b3721fd760fcec9bfbbe43cf96f79e79dd6fd034d478e411dcc`
- Titanium fresh SHA256: `9fdc99dd750653b34ecb5b29dfb5989c71e4ae010483f6e8431e923c9c320f6f`
- Predictions historical SHA256: `5caf2d1047234e854ff484d5794e421fe1dd6b5283ccde202907a3f0769ab238`
- Predictions fresh SHA256: `0aaad6bc99466e5bfa2bac48287bbd127dc45a9aaa393ec68998840803aab02b`

Prior MA3 source-fidelity ablation independently showed that raw-vintage changes can alter cluster-derived features and persistent KMeans membership materially even when the source algorithm is fixed. That is a strongly supported propagation mechanism, but this Stage 0 decision does **not** claim that clustering alone explains 100% of the 11.542 pp economic delta; changed execution prices and other raw-derived features are part of the same data-lineage effect.

## Classification

- `DATA_VINTAGE_EFFECT`: **CONFIRMED**
- `SOURCE_CODE_EFFECT`: **NOT SUPPORTED** for this 31.604 vs 43.146 comparison
- `METRIC_DEFINITION_EFFECT`: **NOT SUPPORTED** after identifying the historical comparator correctly as Annual V2
- `EXECUTION_CONTRACT_EFFECT`: **NOT SUPPORTED** by the matched canonical contract
- `CLUSTER_RECONSTRUCTION_EFFECT`: **STRONGLY SUPPORTED PROPAGATION CHANNEL; NOT YET FULLY QUANTIFIED**

## Important metric clarification

The historical **43.145952%** result is the **Annual V2** benchmark. The historical **P45** result is approximately **46.963230%** and is a different strategy variant. It must not be used as the comparator for the 31.603995% Annual V2 replay.

## Consequence for Original149 vs EU120

The preregistered Stage 0 gate is satisfied. The next comparison may proceed only under a **single frozen raw-data contract** for both Original149 and EU120, with one identical productive source chain and one identical metric/execution definition.

Neither 43.145952% nor 31.603995% should be used as an unconditional universal benchmark independent of data vintage. For an apples-to-apples Original149-vs-EU120 test, the canonical comparator is the Original149 result generated from the exact same frozen raw contract used for EU120.

No configuration is selected because it yields the higher CAGR.
