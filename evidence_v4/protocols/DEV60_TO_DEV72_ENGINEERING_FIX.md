# Evidence V4 — Dev60 to Dev72 engineering-only universe-size fix

Status: **ENGINEERING-ONLY AMENDMENT BEFORE ANY V4 PERFORMANCE RESULT**

Initial V4 model run `37075621569` passed all frozen-input gates and then failed inside the canonical MA3 source-only panel builder, before Stage 1, Stage 2, labels/scores evaluation, summary generation, persistence or artifact upload.

## Failure

The frozen canonical clustering implementation requires:
- defensive sleeve (`C05_BONDS_CASH_CREDIT`) size >= `MIN_CLUSTER_SIZE = 8`;
- dynamic eligible universe size >= `N_DYNAMIC_CLUSTERS * MIN_CLUSTER_SIZE = 7 * 8 = 56`.

Dev60 was frozen as 10 ETFs in each of six categories. That provides 10 defensive ETFs but only 50 non-defensive/dynamic ETFs, so the canonical 7-cluster dynamic reconstruction is structurally impossible even with perfect data coverage. The builder therefore produced no persistent membership rows and stopped before any V4 model/performance computation.

## Correction

Change **only** the V4 development-universe quota from 10 to 12 ETFs per each of the same six categories: 72 total.

Everything else remains frozen:
- exact candidate categories/order inherited from the pre-V3 `evidence_v3/src/freeze_dev72.py`;
- same burned/tested exclusions: Original149 + Holdout70 + tested EU110 + V3 Dev72 (400-name union);
- same Yahoo data window and coverage/OHLC quality rules;
- no performance criterion;
- same Evidence V4 magnitude-direction architecture, Stage-1 LTR, Stage-2 sign target, Top10 shortlist, classifier hyperparameters, decision rule and primary gate already preregistered before this engineering failure.

The corrected universe must preserve all 60 frozen Dev60 constituents. For each category, its first ten selected names must match Dev60 exactly and only the next two coverage-valid names in the already-frozen candidate order may be added. If this prefix check fails, the corrected freeze fails closed.

## Scientific status

Run `37075621569` is **INVALID / NO PERFORMANCE OBSERVED**. It is not a failed scientific test and does not burn the magnitude-direction hypothesis.

The corrected dataset is named `Dev72V4`. No model run may occur until its data, manifest, hashes and provenance are committed.