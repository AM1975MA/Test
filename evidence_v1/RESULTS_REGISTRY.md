# Evidence V1 — Results / artifacts registry

This registry points to the durable result directories and immutable run/artifact identifiers. `EVIDENCE_V1.md` remains the scientific source of truth.

| Test | Status | Run | Artifact | Artifact SHA256 | Durable result |
|---|---|---:|---:|---|---|
| Retriever LTR v1 | development evidence confirmed | `37040547189` | `11241807171` | `d139f0d31485dac1ae70c7b5fd7265887fac125626cb979e8054c18817496ead` | `evidence_v1/results/retriever_ltr_v1/` |
| Pairwise reranker v1 | rejected | `37041677418` | `11242493662` | `13e227467d5f6a52624c71ac2e06b9a1d7fabb58d30fe2a4ff55250e2c829aad` | `evidence_v1/results/pairwise_reranker_v1/` |
| Nonlinear reranker v2 | rejected by preregistered ranking rule | `37046279447` | `11244841228` | `ea8d03b91db5aa7fa3643dc7b93f575ea6d0b874599465cfa5a7b05e1e3865f4` | `evidence_v1/results/reranker_v2_nonlinear/` |
| Universe Sensitivity v1 | validated diagnostic; `SUPPORT_REFERENCE_UNIVERSE` | `37055155515` | `11248586812` | `8ecabaeb80268929ab5f7610ca5848c9b265ebfab7e794a0f4ed2d8df177d58a` | `evidence_v1/results/universe_sensitivity_v1/` |
| Reranker v3 target21 | rejected by preregistered ranking rule | `37056519705` | `11248488705` | `e3f380b4e33e7b6b6b824d4a47a646af4c1b13afe670a87ef0abee67015d3855` | `evidence_v1/results/reranker_v3_target21/` |
| Reranker v4 best classifier | rejected; deterministic reranker line closed | `37059193405` | `11249798147` | `1329862ae79af04b98aa5f26946a0be6fdbc9f210a000a1e31e0fb73b7ae32fe` | `evidence_v1/results/reranker_v4_best_classifier/` |
| Allocation v1 LTR-EW5 | rejected by CAGR gate; risk improvement diagnostic | `37059734467` | `11249119736` | `3c1a3b4522f1149b8e00336838eb00c38acd7e3f0343b0e1ed157b6a2e14b7ba` | `evidence_v1/results/allocation_v1_ltr_ew5/` |
| Allocation v2 causal expert blend | rejected; no causal relative-skill edge | `37060563323` | `11249594252` | `77a1914d46f9f32bb8d9cd27e42be9a0a289f71b8fcadd76ba894abbada8c134` | `evidence_v1/results/allocation_v2_causal_expert_blend/` |

### Universe Sensitivity v1

Result commit: `91ad9a5d9d717eb1a40f8d6bacb5cf12bbae8cc9`. The preregistered stability rule passed in U120, U100 and U70: reference-universe representation won all four stability metrics in every subset. This is **representation/stability evidence, not promotion evidence for a final selector**; diagnostic Top1/performance metrics did not improve consistently.

### Reranker v3 target21

Result commit: `5e57b61302ed76ac0c28756d519e74d019b82ea9`. The frozen LTR comparator reproduced 114 periods, 10 exact Top1 global winners, 15 winners in Top2 and 21 in Top3. v3 produced 10 Top1, 14 Top2 and 19 Top3; therefore it failed the preregistered requirement that Top2 improve while Top1 not worsen. Top1 CAGR proxy also declined from 22.06% to 18.77%. No ex-post tuning is permitted for this version.

### Reranker v4 best classifier

Result commit: `34f8f997ae1858a9007f6cc1809e6ad058855fca`. v4 used a single preregistered binary `best-in-shortlist` head with one positive and nine negatives per frozen OOS Top10. It produced 8/114 exact global winners, 12/114 global winners in Top2 and 16/114 in Top3 versus frozen LTR 10/15/21. Top1 CAGR proxy fell from 22.06% to 14.16%. The preregistered consequence is binding: **no v5 / no further deterministic reranker tuning on Original149**.

### Allocation v1 LTR-EW5

Result commit: `0117b203d83d0a0af478c7778a7de07e5ee3cc5e`. The single frozen allocation held the LTR Top5 at 20% each. Full-window CAGR was 20.36% versus frozen Top1 22.06%, so the primary gate failed even though EW5 materially improved risk: annualized volatility 24.97% vs 37.47%, max drawdown -31.94% vs -51.47%, Sharpe 0.869 vs 0.714 and Calmar 0.637 vs 0.429. Eligible-universe equal weight returned 9.92% CAGR. No ex-post K sweep is permitted.

The subperiod reversal is diagnostic only: 2017–2022 Top1 CAGR 23.72% vs EW5 16.26%, while 2023–2026 Top1 19.27% vs EW5 27.73%. It must not be converted into a hard-coded 2023 regime rule.

### Allocation v2 causal expert blend

Result commit: `3fdcf97f92c5b23a3e49fc8bd71bf8813052efe8`. The single preregistered meta rule used the 12 most recent **matured** expert periods and allocated between frozen Top1 and frozen EW5 proportionally to each trailing compounded wealth. Full-window CAGR was **21.93%**, narrowly below frozen Top1 **22.06%**, while max drawdown improved to **-40.12%** from **-51.47%**, Sharpe to **0.832** from **0.714**, and Calmar to **0.547** from **0.429**. The CAGR gate therefore failed and the protocol forbids lookback/temperature/switch sweeps on Original149.

A post-result diagnostic, explicitly **non-promotional**, found no meaningful persistence in relative expert skill: Spearman between trailing relative wealth and next-period Top1-minus-EW5 return was about **-0.052**, and the trailing leader predicted the next winning expert only **48.25%** of the time. This supports stopping adaptive-allocation tuning rather than trying nearby lookbacks.

## Reusable checkpoints

| Checkpoint | Status | Run | Artifact | Artifact SHA256 | Durable path |
|---|---|---:|---:|---|---|
| Retriever LTR v1 OOS predictions + Top5/Top10 | materialized and validation-matched | `37047338155` | `11244813213` | `2f1baed6984184e2123aa6df140c34882523b2eaf5a47a1874354e6dd5627f74` | `evidence_v1/checkpoints/retriever_ltr_v1/` |

Checkpoint commit: `6f966895d92773dadf8a5963ca7a848950c45504`. Validation reproduced the already-certified development counts before persistence: 114 periods, 10 exact Top1 winners, 32 winners in Top5, 47 winners in Top10. Downstream training must join by `(signal_date, ticker)` and independently enforce label maturity.

## Frozen diagnostic inputs

Universe Sensitivity v1 candidate subsets were frozen from Original149 metadata before model evaluation by run `37053163614`, artifact `11246978301`, artifact SHA256 `a6d313d201caaa3dfdca34b5d59736552483f782d76460ec94f10437a5a3c1f8`.

Durable subset path: `evidence_v1/protocols/universe_sensitivity_v1/`.

Subset file SHA256:
- U120: `6b8d84a01ac7d33a23750154af872e68b57348029f667ef4206aea9ce791d0a0`
- U100: `1e2b85b2b1fc03d3c8de4f43646331b6d930a4d031d1c81442352e55b576063c`
- U70: `73071f3de06c9faa9f194ccb97e4563a6ceb97abe3ddf25179e8db1aff92b9ca`

## Invalidated technical execution

`37045478600` / artifact `11243968811` is **not evidence**. The evaluator used the best 21-day return inside the retriever Top10 as the winner instead of the full Original149 winner. It was invalidated before any tuning; the corrected valid run kept the same reranker configuration. See `evidence_v1/protocols/RERANKER_V2_EVALFIX.md`.

Checkpoint preflight run `37047189409` is also **not evidence** and produced no model output: it stopped before dependency installation/panel/model execution because of a redundant text-SHA serialization mismatch. The authoritative Git-blob gate was retained; no model/configuration was changed.

Universe Sensitivity run `37053782730` is **not evidence**: it stopped at the preregistered support-equality gate because native candidate panels had fewer `(signal_date,ticker)` rows than the full-reference panel. No model metrics/result artifact was produced. Common-support alignment was frozen before the next run in `UNIVERSE_SENSITIVITY_V1_SUPPORTFIX.md`.

Universe Sensitivity run `37054571788` is **not evidence**: after rebuilding panels it stopped because anchor A was being required on pre-2011 rows, even though the preregistered evaluation starts in 2017. No summary, durable result or artifact was produced. The evaluation-window anchor correction was frozen before the valid run in `UNIVERSE_SENSITIVITY_V1_ANCHORFIX.md`.

The extra trigger-file commits used for v4 and Allocation v1/v2 are orchestration-only. Their scientific source and preregistration Git blobs were frozen before execution and verified fail-closed by the valid workflows.

## Frozen state

- branch: `research/evidence-v1`
- baseline frozen commit: `ea1c4e83118309bc7d4bc85f3ea93f658c687d3b`
- latest validated diagnostic result commit: `91ad9a5d9d717eb1a40f8d6bacb5cf12bbae8cc9`
- latest deterministic reranker result commit: `34f8f997ae1858a9007f6cc1809e6ad058855fca`
- latest allocation result commit: `3fdcf97f92c5b23a3e49fc8bd71bf8813052efe8`
- data manifest SHA256: `1efba2bc213ba26b042a9e77630fe26664343654629e658f43d314d068ba9e71`
- source manifest SHA256: `cc4d315da68ec42275a7a74f05446ac6cbb484c3bd92a7861cd76805c5a94782`

Do not overwrite result or checkpoint versions already cited here. A materially changed model/configuration receives a new preregistered test/version and a new durable directory.
