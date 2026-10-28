# EU165 — ETF Trader V2/V3 native portability gate (2026-10-29)

**Status: native full-stack V2/V3 comparison NOT yet executed.** Original production code, B0, USA149 and previous EU155 controls remain untouched.

## Source-based checks performed
- Inspected original V2/V3 source and source identity locks under `fullstack_legacy/`, including authentic basket RNG (seed 20260721; 500 baskets; 24 ETF/basket; 4 per each of six clusters).
- Ran original basket sampling algorithm on EU165: 500 unique baskets × 24 = 12,000 membership records. SHA256 of new fixed baskets: `124f47247142b8b00759d6961d6adeef3711dfc7437bf2af1176c1ee043cad9e`.
- Crossed 500 fixed baskets with all 101 month-specific historical LIQ50 eligibility snapshots. Across 1,212,000 positions only **68.1%** are historically eligible; **87/101** signals have **zero** full-24 eligible baskets. This does not mean that each basket lacks 2 eligible members, but no future-invalid candidates may enter the strategy.
- Generated TWO distinct 500×24 as-of basket portfolios for every monthly signal: seeded RNG resampling and stable deterministic hash priority; both have exactly 4 currently eligible ETFs per cluster. Data contains **2,424,000** row-level memberships (101 dates × 500 × 24 × 2 policies), all checked.
- Mean monthly **basket membership replacement**: RNG **70.54%**, stable hash **4.15%**.
- MOM252 prior-date ONLY diagnostic Top2 membership change: RNG **90.01%**, stable hash **34.27%**. These are diagnostics and NOT V2/V3 alpha, broker trade turnover or NAV metrics.
- Prepared source-contract-compatible `universe.csv` and 165 `<ticker>.csv` OHLCV files totaling 527,841 validated price rows. Tests pass.

## Three native blockers (fail closed)
1. Original V2/V3 full-stack runners assert benchmark/cash symbols `SPY`, `BIL`, `SHV` are in the original US universe; EU165 EUR UCITS does not contain these. A EUR UCITS benchmark/cash adapter with verified price histories is required and constitutes a new model version.
2. Original 149-ticker canonical basket hash is hardcoded to `36a45916b5d8191f3ccd206f39bf3fd3f1ed4bcaffd474e352b69c598f2b6a5e`; EU165 needs its **own** immutable hash and a new as-of basket consumer, not disabled guards.
3. The V3 Pair127 runner explicitly asserts 149 tickers × 102 dates from the original model. Need re-training of actual V3 corrected 127-leaf 3-seed ranker on EU165 (with matured labels), then native Hybrid24 / risk stack; cannot pass 149-era scores as predictions for 165.

Additionally, complete source-only clone cannot run inside the current network-restricted container. No invented native backtest performance values.

## Source archive
Full Python scripts, 165 source-compatible ticker CSVs, both dynamic PIT datasets, CSV audits and tests in downloadable conversation artifact `EU165_NATIVE_V2_V3_PORTING_GATE_20261029.zip`:
- SHA256 `cc8e72813b7c1e56c821af2bc15cb1dc0d1fa652b9bda9c1678b1da1fb6c5c44`.
- Input CSV ZIP SHA256 `04e1d9c2f5777620a0a20404722783cc241553692cb47b202a426e943d9ec2dd`.
- PIT membership CSV.GZ SHA256 `ed8362abd3fb72d354294cb51748dff652ba5c208896420221bf95f7521bf9cd`.
- The full source and large data are available in ZIP, not added to GitHub by this branch.

This is a **test outcome** and working porting input, NOT a validated EU165 V2/V3 execution. Next implementation gate: freeze a sourced UCITS market/cash trio, port native source-only renderer to date-effective baskets, rerun V2 as source-faithfully as possible with new version identity, then retrain original corrected V3 and compare to V2 and frozen B0 on identical calendar/costs, evaluating multiple testing and historical survivorship.
