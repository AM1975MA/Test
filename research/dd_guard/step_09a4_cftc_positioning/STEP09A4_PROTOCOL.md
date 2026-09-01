# STEP09A4 — CFTC Positioning Topology Audit
Date: 2026-09-01

## Purpose
Test whether genuinely orthogonal CFTC positioning information improves STEP09A2's ability to distinguish robust episode-level states STAY / ROTATE / BIL.

## Frozen baseline
- Target, event panel, robust-escape threshold (25%), geometry feature set, statistical date weights, train/forward split and model are **identical to STEP09A2**.
- Primary model only: median imputation -> StandardScaler -> multinomial LogisticRegression(C=0.1,max_iter=3000).
- Training / LOO: 2018–2020.
- Forward development: 2021–2022; report 2021 and 2022 separately.
- No HGB, no threshold search, no contract search, no post-result feature selection.
- 2023+ is excluded from all A4 event data, feature data, fit and evaluation.

## CFTC data / causality
- CFTC Traders in Financial Futures (TFF), Futures Only.
- Contract: E-mini S&P 500, CFTC contract market code 13874A.
- Report observation date is Tuesday. Reports are published Friday.
- Conservative availability rule: a Tuesday report may be used only when `report_date + 4 calendar days <= trigger_date`.
- For each trigger use the latest eligible report under that rule.
- Frozen public source mirror: `m0narch810/vanta` at ref `c47809585b6c3334b0a599d69873a4100db9745f`, file `data/processed/cot_ES.csv`, Git blob SHA `14fe9693cd0de6ca21bf5d9953773d50c41b1ea2`.
- Only exact required report rows from 2018–2022 are frozen into the A4 package.
- Repository-specific `positioning_pctile` and `positioning_signal` are forbidden.

## Frozen CFTC feature block
1. `cot_lev_net_pct`
2. `cot_lev_net_pct_wow`
3. `cot_lev_net_4w_oi = lev_net_4w / open_interest`
4. `cot_asset_mgr_net_pct`
5. `cot_dealer_net_pct`

## Required parity
Before interpreting CFTC results, the geometry-only LOGIT replay must reproduce STEP09A2 forward metrics numerically (target tolerance 1e-12 on primary scalar metrics).

## STEP09A2 gate (unchanged)
- forward balanced accuracy >= 0.45
- forward macro OVR AUC >= 0.60
- forward ROTATE AUC >= 0.60
- forward BIL AUC >= 0.60
- 2021 balanced accuracy >= 0.40
- median pre-2021 LOO macro AUC >= 0.58
- no predicted class >95% forward date weight

## Incremental A4 safeguard
In addition to passing the unchanged A2 gate:
- CFTC macro AUC must be >= geometry macro AUC - 0.01; and
- at least one of forward balanced accuracy or forward macro AUC must improve versus the exact geometry parity replay.

## Decision
- Pass all A2 checks + incremental safeguard -> `QUALIFY_STEP09B_POSITIONING_TOPOLOGY`.
- Otherwise -> `REJECT_STEP09A4_CFTC_POSITIONING_INSUFFICIENT`.

No alternative CFTC feature subset, contract, lag or model may be tested after seeing the A4 forward result.
