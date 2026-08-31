# STEP07B execution amendment — before model fitting

The frozen OHLCV payload is present, but the runtime lacks a Parquet engine and no network/package installation is available. No STEP07B result has been computed yet.

To avoid an unverifiable synthetic reconstruction of daily satellite returns, the substitution lane is changed from a new `SAT50/SAT100` sleeve to the **two exact frozen risky sleeves already available in the immutable path archive**:

- `TV`: exact Treatment Value HGB candidate path (contains the validated substitution policy),
- `FLIP`: exact ARMED_FLIP_25_75 path (same strategy family without Treatment Value substitution),
- `BLEND50`: 50/50 daily return blend of the two exact frozen paths,
- `CASH`.

This preserves the substantive test: whether a substitution-bearing risky sleeve is economically preferable to cash/de-risking during stress, while keeping every counterfactual path exact and avoiding a fabricated satellite path.

Ticker normalization remains in force using the frozen `RISK_LEARNING_PANEL.csv`, which already contains causal leader/satellite momentum, drawdown and volatility state by basket/month. These are converted to per-ticker volatility-scaled coordinates and joined to the daily STEP07A state. No 2023+ information is used.

Revised frozen lanes:
- B1 `EXPECTED_EXPOSURE`: TV100/75/50/25/CASH.
- B2 `EXPECTED_SUBSTITUTION`: TV / BLEND50(TV,FLIP) / FLIP / CASH.
- B3 `Q10_FULL`: TV100/75/50/25 / BLEND50 / FLIP / CASH.

All other protocol items and the quality-jump gate are unchanged.
