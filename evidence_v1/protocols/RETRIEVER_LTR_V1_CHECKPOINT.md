# Evidence V1 — Retriever LTR v1 durable checkpoint

Status: **FROZEN BEFORE MODEL EXECUTION**

Purpose: materialize the already-validated Retriever LTR v1 OOS predictions and Top5/Top10 shortlists in the repository so downstream rerankers do not need to retrain the retriever after unrelated failures.

This operation does **not** introduce a new model or tune any parameter.

## Frozen identity

- source: `evidence_v1/src/materialize_retriever_ltr_v1_checkpoint.py`
- authoritative source Git blob SHA: `159556acbb5487e3929151a6e6e8cd6a8709f797`
- data manifest SHA256: `1efba2bc213ba26b042a9e77630fe26664343654629e658f43d314d068ba9e71`
- source manifest SHA256: `cc4d315da68ec42275a7a74f05446ac6cbb484c3bd92a7861cd76805c5a94782`
- runtime: `evidence_v1/requirements.lock.txt`

The Action must fail closed on the Git blob identity and frozen data/source manifests. The executed file SHA256 is recorded in provenance, but Git blob SHA is the authoritative pre-execution identity.

### Preflight-only amendment

Technical run `37047189409` stopped **before dependency installation, panel rebuild, model fit, or result generation**. The Git blob gate matched, while a redundant locally precomputed text SHA256 did not match the repository serialization. That redundant gate was removed without changing the source/model/configuration. No scientific result had been observed when this amendment was made.

## Expected checkpoint files

Directory: `evidence_v1/checkpoints/retriever_ltr_v1/`

- `OOS_PREDICTIONS.csv`: signal date, ticker, LTR score/rank/normalized position;
- `TOP5.csv`;
- `TOP10.csv`;
- `FIT_AUDIT.csv`;
- `CONFIG.json`;
- `VALIDATION.json`;
- `CHECKPOINT_MANIFEST.json` with SHA256 of checkpoint files;
- `PROVENANCE.json`.

Downstream models must join this checkpoint to the frozen feature panel by `(signal_date, ticker)` and independently enforce label maturity before fitting.

## Validation gate

Before committing the checkpoint, regenerated development metrics on Original149 2017–2026 must reproduce the already-certified Retriever LTR v1 counts:

- periods: `114`;
- exact Top1 winner count: `10`;
- winner in Top5 count: `32`;
- winner in Top10 count: `47`.

If any count differs, checkpoint materialization fails and nothing is committed.
