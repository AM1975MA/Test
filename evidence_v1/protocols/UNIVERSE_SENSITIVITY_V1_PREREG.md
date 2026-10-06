# Evidence V1 — Universe Sensitivity v1

Status: **PREREGISTERED BEFORE EXECUTION**

Purpose: test whether the instability observed when the tradable universe changes is materially driven by universe-dependent representation (cross-sectional ranks and dynamic clusters), rather than only by candidate removal or by retraining on fewer names.

This is a **diagnostic**, not a promotion test. `Holdout70` is not used.

## Frozen inputs

- branch: `research/evidence-v1`
- evaluator source: `evidence_v1/src/universe_sensitivity_v1.py`
- evaluator Git blob: `9e51793b8e87f43fc691cbe42e02d9486f65c61c`
- source-only panel builder Git blob: `34cc133d4d44bb06cc21363b1444865e2d8ec5c1`
- canonical `FEATURES_42` producer Git blob: `e691376e3a8e0ec1bd38cc5b85a8ebbfa35d0592`
- frozen data manifest SHA256: `1efba2bc213ba26b042a9e77630fe26664343654629e658f43d314d068ba9e71`
- frozen source manifest SHA256: `cc4d315da68ec42275a7a74f05446ac6cbb484c3bd92a7861cd76805c5a94782`
- locked runtime SHA256: `01305fe62203c7b7895d95836267c4288f86d2c5a763ce7070c9c3d3d9f807ae`

### Frozen candidate subsets

Generated before this test by run `37053163614`, from Original149 metadata only.

- subset manifest: `evidence_v1/protocols/universe_sensitivity_v1/SUBSET_MANIFEST.json`
- subset manifest Git blob: `6d7709bc9f80b866fc241ed9cc10766a8b6481da`
- `U120.csv` Git blob: `7d0d56a3269f6e018b12c485939055f22be950b5`; file SHA256 `6b8d84a01ac7d33a23750154af872e68b57348029f667ef4206aea9ce791d0a0`
- `U100.csv` Git blob: `cfa45dbbd1c754f582bb382cd687d35bf63b1427`; file SHA256 `1e2b85b2b1fc03d3c8de4f43646331b6d930a4d031d1c81442352e55b576063c`
- `U70.csv` Git blob: `c6b56b97c4ee87cac51a948835d7ab475146d838`; file SHA256 `73071f3de06c9faa9f194ccb97e4563a6ceb97abe3ddf25179e8db1aff92b9ca`
- subset-freeze artifact: `11246978301`; artifact SHA256 `a6d313d201caaa3dfdca34b5d59736552483f782d76460ec94f10437a5a3c1f8`

The subsets are nested and preserve macro-category composition by the preregistered proportional-deficit rule. `SPY` is present in all three only to hold the calendar anchor constant.

### Frozen Retriever LTR v1 anchor

- reusable checkpoint: `evidence_v1/checkpoints/retriever_ltr_v1/`
- checkpoint manifest Git blob: `e51a8651f6696a0081acb09e3ed230e7e35fd79c`
- frozen OOS prediction Git blob: `1745a6d12b6957bc629998c7ac3417550ac9bceb`
- OOS prediction file SHA256: `3f9e054fdc0716161cec185ad5a32a62671ad3032070b9ca24ceed655011abd6`
- LTR config is unchanged from the certified Retriever LTR v1.

## Experimental design

For each frozen candidate universe `U120`, `U100`, `U70`, compare exactly three rankings.

### A — fixed full-reference anchor

Use the already-frozen Original149 LTR v1 OOS scores and simply remove tickers not belonging to the candidate universe. Re-rank the surviving candidates. No retraining and no feature recomputation.

This measures the purely mechanical effect of removing candidates from the existing full149 system.

### B — stable reference representation

Filter the full Original149 source-only panel to candidate tickers, preserving `FEATURES_42` as computed against the full149 reference universe and preserving full149 cluster context. Recompute the target ranks **inside the candidate universe** and retrain the unchanged LTR v1 annually expanding with the 63-day maturity gate.

Thus selection is in the candidate universe while representation remains `f(asset, reference_universe=Original149)`.

### C — native candidate representation

Rebuild the source-only feature panel and dynamic clustering using only the candidate universe. Recompute the same candidate-relative targets and retrain the identical LTR v1 with the identical annual expanding maturity gate.

### Isolation rule

Before fitting B or C, `(signal_date, ticker)` coverage must be identical and the recomputed candidate-relative `target_relevance` must be exactly identical. Otherwise the test fails closed.

Therefore B vs C differs in representation/context, not candidate membership or labels.

## Evaluation window

- OOS evaluation: `2017-01-01` through `2026-06-30`
- expected signal periods per subset: `114`
- temporal diagnostics: `2017-2022` and `2023-2026`

## Prespecified stability metrics

For B and C versus anchor A:

1. Top1 agreement rate — higher is more stable.
2. Top5 turnover, defined as `1 - Jaccard(Top5_method, Top5_A)` — lower is more stable. **Primary metric.**
3. Cross-sectional rank correlation to A — higher is more stable.
4. Mean absolute rank displacement divided by `N-1` — lower is more stable.

B vs C direct Top1 agreement, Top5 Jaccard, rank correlation and normalized rank displacement are also recorded.

## Prespecified representation diagnostics

- absolute drift of every one of `FEATURES_42` between full-reference and native candidate panels;
- dynamic cluster stability measured by Adjusted Rand Index, which is invariant to cluster-label permutation;
- reference/native cluster count by signal date.

## Performance diagnostics

For A/B/C, record candidate-universe exact winner Top1, winner in Top5, winner in Top10 and 21-day Top1 CAGR proxy. These values are **diagnostic only** and cannot determine the conclusion of this test.

## Decision rule

The hypothesis `stable reference universe reduces universe sensitivity` is supported only if **both** conditions hold:

1. B has lower Top5 turnover to A than C in **all three** subsets U120/U100/U70; and
2. B beats C in at least **3 of the 4** prespecified stability metrics in **every** subset.

No parameter sweep, subset replacement, metric replacement, or ex-post threshold tuning is allowed after seeing results.

If the rule fails, reference-universe stabilization is not supported by this test. A future test must introduce a genuinely new hypothesis/version.

## Durable outputs

After successful execution, persist without overwriting prior versions:

`evidence_v1/results/universe_sensitivity_v1/`

with at least:

- `SUMMARY.json`
- `CONFIG.json`
- `PER_DATE_STABILITY.csv`
- `FEATURE_DRIFT.csv`
- `CLUSTER_STABILITY.csv`
- `FIT_AUDIT.csv`
- `PROVENANCE.json`
- `RESULT_MANIFEST.json`

Only after these outputs exist may `EVIDENCE_V1.md` be updated.