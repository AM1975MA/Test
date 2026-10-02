# Evidence V1 — Results / artifacts registry

This registry points to the durable result directories and immutable run/artifact identifiers. `EVIDENCE_V1.md` remains the scientific source of truth.

| Test | Status | Run | Artifact | Artifact SHA256 | Durable result |
|---|---|---:|---:|---|---|
| Retriever LTR v1 | development evidence confirmed | `37040547189` | `11241807171` | `d139f0d31485dac1ae70c7b5fd7265887fac125626cb979e8054c18817496ead` | `evidence_v1/results/retriever_ltr_v1/` |
| Pairwise reranker v1 | rejected | `37041677418` | `11242493662` | `13e227467d5f6a52624c71ac2e06b9a1d7fabb58d30fe2a4ff55250e2c829aad` | `evidence_v1/results/pairwise_reranker_v1/` |
| Nonlinear reranker v2 | rejected by preregistered ranking rule | `37046279447` | `11244841228` | `ea8d03b91db5aa7fa3643dc7b93f575ea6d0b874599465cfa5a7b05e1e3865f4` | `evidence_v1/results/reranker_v2_nonlinear/` |

## Invalidated technical execution

`37045478600` / artifact `11243968811` is **not evidence**. The evaluator used the best 21-day return inside the retriever Top10 as the winner instead of the full Original149 winner. It was invalidated before any tuning; the corrected valid run kept the same reranker configuration. See `evidence_v1/protocols/RERANKER_V2_EVALFIX.md`.

## Frozen state

- branch: `research/evidence-v1`
- baseline frozen commit: `ea1c4e83118309bc7d4bc85f3ea93f658c687d3b`
- data manifest SHA256: `1efba2bc213ba26b042a9e77630fe26664343654629e658f43d314d068ba9e71`
- source manifest SHA256: `cc4d315da68ec42275a7a74f05446ac6cbb484c3bd92a7861cd76805c5a94782`

Do not overwrite result versions already cited here. A materially changed model/configuration receives a new test/version and a new durable directory.
