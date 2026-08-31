# STEP06R — causal score calibration protocol

Date: 2026-08-31

## Status before execution
Pre-registered before any 2023+ data are opened. The 2023+ holdout remains sealed.

## Frozen facts inherited from STEP06Q
- Selected new source variable: `dgs10_chg63` (63-session change in DGS10).
- Action target: STEP06L utility = `ret_adv + 0.5 * dd_adv`.
- STEP06Q discovery/forward evidence is retained as reported; its original artifact bundle was not persisted, so the exact regression specification is not claimed to be recovered.
- Controller semantics remain q30: bottom 30% = STANDARD FUSION1 tail (50% at -5%, 25% at -7.5%); above 30% = AGGRESSIVE STEP06K tail (25% at -5%, 0% at -7.5%).
- FUSION1 trigger generation, STEP06K initial breadth softening, recovery logic and 5 bp turnover costs remain frozen.

## Reconstruction policy
Because the exact STEP06Q regression object was lost, STEP06R will not fabricate parity. A primary low-dimensional proxy and several plausible reconstruction proxies are tested. The scientific conclusion is considered robust only if it is not dependent on one reconstruction.

Primary proxy (`QPROXY_A`): weighted Ridge(alpha=10), unweighted StandardScaler, target utility, controls =
`neg1_jump3_pct252`, `neg5_minus_neg21_pct252`, `down3h_jump5_pct252`, `xle_r63`, `xlv_r3`, `xlf_r10`, plus frozen `dgs10_chg63`.
Training = 2019-2020 crossing events, date weights = 1 / same-date multiplicity. Validation = 2021-2022 only.

Sensitivity proxies are fixed before replay from already-computed reconstruction diagnostics; no 2023+ information is used.

## Calibration variants
All use the frozen q30 action semantics; thresholds are not searched.

- `R1_EXPANDING_ECDF`: raw predicted action utility is converted to its empirical percentile against all strictly earlier crossing-date scores, seeded by 2019-2020. Scores from a new date enter history only after that date.
- `R2_ROLLING_252D_ECDF`: empirical percentile against earlier crossing-date scores from the trailing 252 calendar days; if fewer than 10 distinct historical crossing dates are available, fall back to expanding history.
- `R3_MATURED_BIAS_ECDF`: raw score is corrected by the date-weighted mean historical prediction residual (`actual - predicted`) using only events at least 126 trading sessions old; the corrected score is then ranked against prior corrected scores. If no mature residual history exists, bias correction is zero. This is deliberately conservative.

Percentile definition uses date weights so one market date, not basket multiplicity, is the effective evidence unit.

## Development replay gate
Exact engine replay is restricted to 2021-01-01 through 2022-12-31.
A calibration is eligible for a future one-shot holdout only if:
1. it creates treatment contrast (date-weighted aggressive rate strictly between 30% and 90%);
2. versus frozen STEP06K, mean MaxDD does not worsen and CAGR does not worsen by more than 0.02 pp;
3. for DD-first selection, candidates passing (1)-(2) are ranked by delta mean MaxDD, then delta CAGR.

Sensitivity requirement: the selected calibration must not show a material sign reversal under the plausible Q-proxy reconstructions. If reconstruction uncertainty is decisive, STEP06R is rejected before holdout.

## Holdout rule
No 2023+ data will be opened unless the development gate and reconstruction-robustness requirement pass. No retuning is permitted after a holdout opening.
