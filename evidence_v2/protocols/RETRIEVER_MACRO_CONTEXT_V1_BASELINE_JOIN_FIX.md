# Evidence V2 — Retriever macro-context v1 baseline join fix

Status: **ENGINEERING-ONLY AMENDMENT; NO SCIENTIFIC RESULT OBSERVED**

Initial model run `37069284576` completed the macro-context fits but failed before comparator evaluation because the frozen Retriever LTR checkpoint intentionally stores only `(signal_date, ticker, LTR_SCORE, LTR_RANK, LTR_POSITION)` and does not duplicate future-return/label columns.

The checkpoint's own manifest requires downstream users to join it to the frozen source-only panel for features/labels. The failed evaluator attempted to use `fwd_ret_21` directly from the checkpoint and raised `KeyError: ['fwd_ret_21']` before printing, persisting or uploading any model summary or performance metric.

Correction: in workflow orchestration only, make a temporary evaluation copy of the frozen `OOS_PREDICTIONS.csv` and join to the just-rebuilt Original149 panel on the immutable key `(signal_date, ticker)` to add exactly `fwd_ret_21` and `target_relevance`. The frozen LTR scores/ranks are not recomputed or changed.

No macro feature, model setting, target, training window, evaluation date, comparator score, primary gate or decision rule changes.