# STEP08F — event-time Titanium score distillation / protective rotation

Date: 2026-08-31

## Scientific question
STEP08D/E showed that authentic monthly `TIT_R` has useful destination information but is stale at daily q95 risk events, particularly in 2021. STEP08E2 showed that forcing inverse/downside correlation is not the missing solution. STEP08F tests whether refreshing the Titanium cross-sectional state at the actual risk-event close improves protective rotation.

## Identity constraint
The original historical Titanium/Super-Gold score producer is not available as a bit-identical callable daily model; the recovered authentic monthly `TIT_R` panel remains the source of truth. STEP08F therefore does **not** claim to recreate the original historical model bit-for-bit.

Instead, STEP08F distills the authentic same-date `TIT_R` mapping using only causal OHLCV features available at each date. The supervised target is the authentic historical score `TIT_R`, not a future return. This lets the producer be validated for identity reconstruction without looking at 2021-2022 economic outcomes.

## Frozen inputs
- Authentic `ORTHOGONAL_SCORE_PANEL.pkl` and frozen 24-ETF basket membership from the certified Titanium recovery.
- Frozen OHLCV matrices used by STEP08C-E2.
- STEP08C/STEP07A q95 decision schedule.
- Exact FUSION1 development replay.
- Same 10-session action window and 10 bp round-trip replacement cost.
- Development performance window: 2021-01-01 through 2022-12-31. 2023+ remains sealed.

## Event-time feature contract
Use the frozen Super-Gold/Titanium price/volume feature family recovered from the self-contained source notebook. It contains the raw causal OHLCV features and their same-date cross-sectional percentile/deviation transforms used by the frozen Tail/Compact rankers. Features are computed through the close of the score date only; no future label enters an event-time feature.

The event-time producer receives the union of frozen Tail and Compact feature contracts plus static macro-category indicators. Missing values are imputed from training history only.

## F0 — producer selection and parity gate (pre-development only)
Model families are frozen before parity evaluation:
1. `RIDGE10`: median imputer -> StandardScaler -> Ridge(alpha=10).
2. `HGB`: median imputer -> HistGradientBoostingRegressor(max_iter=180, learning_rate=0.04, max_leaf_nodes=15, min_samples_leaf=30, l2_regularization=5, random_state=20260831).
3. `ET`: median imputer -> ExtraTreesRegressor(n_estimators=300, max_features=0.70, min_samples_leaf=8, random_state=20260831, n_jobs=-1).

Selection metric: mean same-date Spearman correlation between predicted score and authentic `TIT_R` on monthly signal dates in 2019-2020, using annual expanding fits (2019 trained only through 2018; 2020 trained only through 2019). Ties are broken by basket-local top-3 overlap, then simpler model order RIDGE10 -> HGB -> ET.

Parity acceptance required before calling the producer a Titanium event-time reconstruction:
- mean cross-sectional Spearman >= 0.60;
- median cross-sectional Spearman >= 0.60;
- mean basket-local top-3 overlap >= 0.40.

If these fail, the event-time score may be reported only as a diagnostic surrogate and cannot authorize a 2023+ holdout.

## F1 — frozen event-time destination policy
After F0 selection, refit the selected surrogate annually:
- 2021 event scores: authentic monthly score observations strictly before 2021-01-01;
- 2022 event scores: authentic monthly score observations strictly before 2022-01-01.
No intrayear refit and no use of 2021/2022 returns or event outcomes in model fitting.

For each frozen q95 decision at close d:
1. compute event-time causal features for all available ETFs at d;
2. predict the event-time distilled Titanium score and convert it to a full-universe percentile rank;
3. restrict destinations to the basket's frozen 24 ETFs and exclude current leader/satellite;
4. BIL is the outside option: if no eligible basket candidate has event-time rank strictly above BIL, use 100% BIL;
5. otherwise apply native V2 sizing inside the eligible basket: 100% top1 if event-time rank(top1)-rank(top2) >= 0.12, else 75/25 top1/top2;
6. hold only for the frozen STEP08C 10-session action window, then return to exact FUSION1.

## Development gate
F1 qualifies for any one-shot 2023+ holdout only if producer parity passes and, versus FUSION1 over 2021-2022:
- delta CAGR >= -0.50 pp;
- delta mean MaxDD >= +0.50 pp;
- delta p10 MaxDD >= +0.50 pp;
- delta worst-decile MaxDD >= 0;
- delta mean MaxDD >= 0 separately in 2021 and 2022.

No score threshold, model hyperparameter, feature family, horizon, q95 trigger, V2 margin, candidate universe, cost or sizing may be retuned after observing F0 or F1 results. 2023+ remains sealed if any gate fails.
