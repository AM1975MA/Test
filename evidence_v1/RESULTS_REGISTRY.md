# Evidence V1 — Results / artifacts registry

This registry points to the durable result directories and immutable run/artifact identifiers. `EVIDENCE_V1.md` remains the scientific source of truth.

| Test | Status | Run | Artifact | Artifact SHA256 | Durable result |
|---|---|---:|---:|---|---|
| Retriever LTR v1 | development evidence confirmed | `37040547189` | `11241807171` | `d139f0d31485dac1ae70c7b5fd7265887fac125626cb979e8054c18817496ead` | `evidence_v1/results/retriever_ltr_v1/` |
| Pairwise reranker v1 | rejected | `37041677418` | `11242493662` | `13e227467d5f6a52624c71ac2e06b9a1d7fabb58d30fe2a4ff55250e2c829aad` | `evidence_v1/results/pairwise_reranker_v1/` |
| Nonlinear reranker v2 | rejected by preregistered ranking rule | `37046279447` | `11244841228` | `ea8d03b91db5aa7fa3643dc7b93f575ea6d0b874599465cfa5a7b05e1e3865f4` | `evidence_v1/results/reranker_v2_nonlinear/` |
| Universe Sensitivity v1 | validated diagnostic; `SUPPORT_REFERENCE_UNIVERSE` | `37055155515` | `11248586812` | `8ecabaeb80268929ab5f7610ca5848c9b265ebfab7e794a0f4ed2d8df177d58a` | `evidence_v1/results/universe_sensitivity_v1/` |

Universe Sensitivity v1 result commit: `91ad9a5d9d717eb1a40f8d6bacb5cf12bbae8cc9`. The preregistered stability rule passed in U120, U100 and U70: reference-universe representation won all four stability metrics in every subset. This is **representation/stability evidence, not promotion evidence for a final selector**; diagnostic Top1/performance metrics did not improve consistently.

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

## Frozen state

- branch: `research/evidence-v1`
- baseline frozen commit: `ea1c4e83118309bc7d4bc85f3ea93f658c687d3b`
- latest validated diagnostic result commit: `91ad9a5d9d717eb1a40f8d6bacb5cf12bbae8cc9`
- data manifest SHA256: `1efba2bc213ba26b042a9e77630fe26664343654629e658f43d314d068ba9e71`
- source manifest SHA256: `cc4d315da68ec42275a7a74f05446ac6cbb484c3bd92a7861cd76805c5a94782`

Do not overwrite result or checkpoint versions already cited here. A materially changed model/configuration receives a new test/version and a new durable directory.
