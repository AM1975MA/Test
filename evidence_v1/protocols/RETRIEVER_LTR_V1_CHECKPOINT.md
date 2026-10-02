# Evidence V1 — Retriever LTR v1 durable checkpoint

Status: **FROZEN BEFORE EXECUTION**

Purpose: materialize the already-validated Retriever LTR v1 OOS predictions and Top5/Top10 shortlists in the repository so downstream rerankers do not need to retrain the retriever after unrelated failures.

This operation does **not** introduce a new model or tune any parameter.

## Frozen identity

- source: `evidence_v1/src/materialize_retriever_ltr_v1_checkpoint.py`
- source Git blob SHA: `159556acbb5487e3929151a6e6e8cd6a8709f797`
- source SHA256: `cec776029910d46abfb01d9f3a80fc0e50b0f8b998ff89e47726a330e6930a9a`
- data manifest SHA256: `1efba2bc213ba26b042a9e77630fe26664343654629e658f43d314d068ba9e71`
- source manifest SHA256: `cc4d315da68ec42275a7a74f05446ac6cbb484c3bd92a7861cd76805c5a94782`
- runtime: `evidence_v1/requirements.lock.txt`

The Action must fail closed if any of these frozen identities do not match.

## Expected checkpoint files

Directory: `evidence_v1/checkpoints/retriever_ltr_v1/`

- `OOS_PREDICTIONS.csv`: signal date, ticker, LTR score/rank/normalized position;
- `TOP5.csv`;
- `TOP10.csv`;
- `FIT_AUDIT.csv`;
- `CONFIG.json`;
- `VALIDATION.json`;
- `CHECKPOINT_MANIFEST.json` with SHA256 of checkpoint files.

Downstream models must join this checkpoint to the frozen feature panel by `(signal_date, ticker)` and independently enforce label maturity before fitting.

## Validation gate

Before committing the checkpoint, regenerated development metrics on Original149 2017–2026 must reproduce the already-certified Retriever LTR v1 counts:

- periods: `114`;
- exact Top1 winner count: `10`;
- winner in Top5 count: `32`;
- winner in Top10 count: `47`.

If any count differs, checkpoint materialization fails and nothing is committed.
