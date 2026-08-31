# STEP08D — Final checkpoint

Date: 2026-08-31

## Frozen research question
Use the authenticated historical Titanium V2 `TIT_R` ranking only as the destination selector when the already-frozen STEP07A q95 danger trigger fires. No new destination model and no tuning of trigger, horizon, margin, weights, or costs. Development is 2021–2022 only; 2023+ remains sealed.

## Source identity
The recovered authentic `ORTHOGONAL_SCORE_PANEL.pkl` is used as source of `TIT_R`; unrestricted rank parity is 72/72 monthly dates in the development-accessible history. Its SHA-256 matches the certified recovery hash.

## Frozen policies
- `TIT_R_TOP1`: 100% to highest eligible authentic TIT_R destination.
- `TIT_R_V2_BALANCED` (primary): official V2 concentration semantics, 100% top1 if top1-minus-top2 raw TIT_R >= 0.12, otherwise 75/25 top1/top2. Current leader and satellite excluded. BIL is an ordinary scored destination.

## Development result 2021–2022
Primary `TIT_R_V2_BALANCED` versus exact FUSION1:
- delta CAGR: **+0.209391 pp**
- delta mean MaxDD: **+0.678123 pp**
- delta p10 MaxDD: **+1.163579 pp**
- delta worst-decile MaxDD: **+0.246820 pp**
- delta Sharpe: **+0.003940**

Structural diagnostic `TIT_R_TOP1`:
- delta CAGR: **+0.338573 pp**
- delta mean MaxDD: **+0.700624 pp**
- delta p10 MaxDD: **+0.850347 pp**
- delta worst-decile MaxDD: **+0.127750 pp**

## Time split — decisive failure
Primary D2:
- 2021: delta CAGR **-2.226037 pp**, delta mean MaxDD **-0.685098 pp**.
- 2022: delta CAGR **+2.498097 pp**, delta mean MaxDD **+0.984366 pp**.

The preregistered gate required non-negative mean-MaxDD delta in both calendar years. D2 therefore fails despite an aggregate improvement.

## Mechanism diagnostics
- 1,124 frozen q95 decisions.
- Mean/median/max age of the latest authentic monthly score at a daily decision: 14.2 / 13 / 32 calendar days.
- Exact oracle destination hit rate for TIT_R top1: 1.16%.
- Top1 beats BIL on event utility in 71.44% of events, but beats exact FUSION1 continuation in only 49.56%.
- The inherited raw 0.12 V2 concentration condition fires 100%-top1 in 0% of full-universe events. This is a structural domain mismatch: the official 0.12 rule was defined inside 24-ETF baskets, whereas STEP08D ranks the nearly full 150-ETF cross-section. This observation is diagnostic only and is not used to retune STEP08D.

## Verdict
**REJECT_BEFORE_2023_HOLDOUT.**

No 2023+ data are opened. No post-result tuning is performed in STEP08D. The useful finding is that authenticated Titanium cross-sectional alpha moves the aggregate DD frontier in the desired direction, but monthly/stale full-universe destination ranking is not calendar-time robust enough: it hurts materially in 2021 and helps strongly in 2022.
