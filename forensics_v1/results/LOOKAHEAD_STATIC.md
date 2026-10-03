# ETF_TRADER_PERTURBATION_FORENSICS_V1 — static lookahead audit

Status: **STATIC PASS WITH RESEARCH-DESIGN CAVEATS; DYNAMIC AUDIT STILL REQUIRED**

This file records only static/source conclusions. Overall lookahead PASS requires the separately preregistered future-mutation and truncation tests.

## Productive source identity

The forensic uses the hash-gated canonical V2 productive source chain and the same controlled replay runner used in the three-snapshot repeatability experiment.

## Source-only Titanium model fitting

`source_only/models.py` is explicitly annual/prequential and contains fail-closed maturity checks.

For Compact 21/63 XGBRanker fits, training requires:
- `signal_date < cutoff`
- `exit_date_<horizon> < cutoff`
- mature non-null target.

It raises a runtime error if a training signal or target maturity reaches the prediction-year cutoff.

For the Ridge tail model:
- `signal_date < cutoff`
- `exit_date_63 < cutoff`.

For the macro model:
- `signal_date < cutoff`
- `label_exit_date_63 < cutoff`.

Imputation/scaling are fitted inside the training-only pipelines. No test-year rows are used to fit those transforms.

Static conclusion: **PASS** for annual model-label maturity and training-only transforms.

## MA3 ensemble / hybrid producer

The final producer also uses annual expanding maturity-safe fits. Training rows require both `signal_date < annual cutoff` and `exit_date_63 < annual cutoff`. The fit audit records and checks `maturity_ok`.

Static conclusion: **PASS** for operational walk-forward maturity.

Research-design caveat: model/blend/risk architecture contains components whose hyperparameters/architecture were historically selected on development periods such as 2017–2022. That makes those periods burned/development evidence. It is **not operational lookahead inside the replay**, but it must not be presented as untouched out-of-sample evidence.

## Clustering / persistent membership

`a4_cluster_destination.py` builds current cluster membership from historical price returns in a window ending at the current `signal_date`. Its source audit explicitly enforces that no source date exceeds the signal date.

Persistent cluster identity matching uses previous-month membership, not future membership.

The cluster panel can carry forward-return label columns for downstream destination-label work, but current membership does not use those forward returns to assign the current cluster. Destination-model training is separately maturity gated by `exit_date_h < prediction_date`.

Static conclusion: **PASS** for current cluster-membership causality.

## DD-first / risk state

Systemic conditions derived from closes are shifted by one session before they can affect the current session. Current-open gap information is used at the open; current-day low is used only for simulated intraday stop execution after the position exists.

Static conclusion: **PASS** for prior-close/open/intraday ordering in the inspected path.

## V6 alternate selection

V6 recovery/alternative logic uses prior-row information (`t = k - 1`) when choosing state for day `k`.

Static conclusion: **PASS** for inspected V6 state timing.

## Negative shifts / centered windows

Repository code search on the forensic branch found no productive-source occurrences of `shift(-` and no `center=True` hits in the inspected pipeline.

This supports, but does not alone prove, causal construction.

## `.bfill()` execution concern

The controlled replay contains `.ffill().bfill()` when constructing execution matrices. This pattern is unsafe in general because leading missing data could be filled from the future.

However, direct audit of the frozen Original149 evaluation interval 2017-02-01 through 2026-07-01 found:
- 2366 x 149 candidate close matrix;
- zero raw missing evaluation cells;
- zero cells requiring bfill after ffill;
- zero candidate tickers requiring bfill in the evaluation interval.

Therefore the `.bfill()` call did **not** inject future values in this controlled Original149 experiment. It should nevertheless be removed or fail-closed in production-quality code.

## Universe / survivorship caveat

Using a universe defined with later knowledge can create survivorship/universe-selection bias. This is distinct from code lookahead. It must be evaluated separately when certifying an investable backtest.

## Static verdict

No operational lookahead has been found in the inspected canonical Original149 source path. The strongest potentially suspicious areas — target maturity, clustering, risk timing, V6 timing, and execution bfill — have static explanations consistent with causal operation in the controlled dataset.

**Overall lookahead verdict remains INCOMPLETE until dynamic future-mutation and truncation invariance tests pass.**
