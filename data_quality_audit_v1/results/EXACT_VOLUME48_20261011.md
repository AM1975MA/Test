# Exact volume_surprise21 rolling null cause — 2026-10-11

Previous PR #66 static feature formula gate classified 18,401/18,449 missing Compact21 base cells as inadequate raw-history length and 48 as volume-domain cases requiring exact replay. Checked PR search for volume_surprise21 and rolling-volume classifications: no independent completed exact replay located. This diagnostic uses original immutable Yahoo acquisitions from run 37121749852 and fixed α=1 Compact21 panels from run 38094232042, with no model fitting, no OHLCV edits or imputations.

GitHub Actions [38136343074](https://github.com/AM1975MA/Test/actions/runs/38136343074) **SUCCESS**, artifact detailed CSV and JSON. Reproduces the exact `volume_surprise21` formula `lv=np.log(V.where(V>0)); (lv-lv.rolling(21,min_periods=15).mean()) / lv.rolling(21,min_periods=15).std(ddof=0).replace(0,np.nan)`.

At **each of three independent Yahoo download vintages**, 48 otherwise-eligible but incomplete Compact21 rows have missing volume_surprise21:
- 33 have **zero/invalid same-session Volume**, making log(V) undefined.
- 15 have a **21-observation window with fewer than 15 positive-volume sessions**, so both mean/std are undefined under exact min_periods=15.
- Zero cases unexplained by the implemented rolling formula (none due to exact zero standard deviation after enough observations and positive same-day volume).

The tested 18,449 missing base-feature cells in PR #66 therefore have root-level interpretations: 18,401 insufficient formula-specific bar history and 48 exact volume-log-domain violations. The 31,604 missing derivative cells inherited missing underlying base, as established in PR #64. This establishes current **Compact21 subset missingness**, not that the entire V2 input data or historical Yahoo adjustments, corporate actions, MA3/Tail/Macro/Extra, scoring and causality gates are certified.

Do NOT fill NaN with zero, invent volume, forward fill missing market data, or exclude instruments in-sample based on CAGR. Original149 is research-only; production Etf_trader was not touched.
