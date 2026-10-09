# R0-R — Data audit: availability of downside-risk features among future top-performing ETFs

**9 October 2026 — completed, read-only, Test research branch.** No ETF model training, no historical full-V2 replay. Protocol preregistered first in commit 0301bc448aee490515dc3f1fcff9b1e6808c67fa.

## Verified matched frozen Yahoo inputs

149 ETFs, 114 month-end signals January 2017–June 2026, 21-session next-Open to Open future returns; original adjusted Close prior to signal for downside feature. Repeat1/Repeat3 original raw snapshot archive SHA256 fcc02918b3a42c3fecde273c4639ca4eed1b5f31e4b8c32aeea4c2a8e4c00f86. Fixed ex-post future Top15 and Bottom15, all 149 eligible ETFs and every date retained. Future returns were used solely to evaluate groups, NOT to form an as-of predictive feature.

| Native downside feature | Missing in eventual Top15 | Missing in eventual Bottom15 | Overall missing | Missing for eventual Best1 | Continuous LPM2 available in Top15 |
|---|---:|---:|---:|---:|---:|
| 21-session | **835/1710 = 48.83%** | **712/1710 = 41.64%** | **48.25%** | **45/114 = 39.47%** | **1710/1710** |
| 63-session | 1044/1710 = 61.05% | 1009/1710 = 59.01% | 63.62% | 65/114 = 57.02% | 1710/1710 |
| 126-session | 1208/1710 = 70.64% | 1180/1710 = 69.01% | 74.72% | 75/114 = 65.79% | 1710/1710 |

For 21 sessions, 2017–2022 Top15 missing 49.91% vs Bottom15 42.59%, and Best1 missing 27/72; in 2023–2026 Top15 46.98%, Bottom15 40.00%, Best1 missing 18/42. Exact winner ticker matches previously frozen R0-D ledger on 114/114 dates for BOTH Repeat1 and Repeat3. Same-market revisions are not independent market holdouts.

**Critical nuance:** Feature missingness is 48.83% among realized Top15 but only 39.47% among exact Best1, less than the 48.25% all-ETF rate. Therefore do NOT interpret higher missingness among the Top15 as a simple monotonic signal predictive of positive returns. This is a descriptive audit with temporally correlated ETF rows.

## Why this changes the engineering decision

Canonical source-only kernel.py rolling_downvol uses conditional standard deviation of negative-return days and a minimum number of *negative observations*. Crossing the count threshold can switch a value to missing after a tiny Yahoo return sign revision. The original 125-column Compact21 includes 21/63/126 downside volatility and their percentile/deviation versions (nine columns). The R0-Q continuous zero-target lower-partial-moment formula reduces vintage numerical feature-difference on strictly identical existing support by 23.2x/44.0x/24.2x for 21/63/126 lookbacks, with high-amplitude anomalies >0.1 dropping 44/16/4 to zero; however it changes feature semantics and availability.

This new R0-R analysis confirms that continuous LPM2 would make features available in large numbers of *historically important winner observations*. It is NOT a drop-in safe fix for an existing trained Booster. Numeric stability of a feature does not prove model training stability or preserve selection/CAGR. Most importantly, source-only models.py accepts a row when at least **30/125** model features exist: feature missingness DOES NOT mean the ETF was excluded from training. Need entire panel/cohort before any such statement.

**Data decision:** REAL_INPUT_DISCONTINUITY_IDENTIFIED; REAL_TAIL_FEATURE_COVERAGE_SHIFT_CONFIRMED; ACTUAL_MODEL_ALPHA_UNTESTED. R0-M hard 20bp masked-loss objective already failed joint synthetic gate; avoid further parameter sweeps on burned Original149. Continue via one versioned LPM2 feature-schema challenger only on genuinely new point-in-time matched data, with original group/date/mature labels, three XGB seeds, 21/63 horizons, 360 rounds and original MA3/daily risk. Check tail selection, vintage score instability and complete full V2 economic noninferiority before promotion. Do not claim new CAGR.

## QA

Three focused TDD tests passed (after fixing incomplete initial test fixture), Python compileall passed. Independent Data audit reconciled 684 rows = 2 versions x 3 lookbacks x 114 dates, 149 tickers/date, Top15/Bottom15 and winner counts. 114/114 ex-post winner tickers also matched the independent previously frozen reference. Portable executed source, monthly CSV, JSON results, tests, logs and SHA256 manifest are in the attached ZIP ETF_Trader_V2_R0R_Data_Missingness_Tail_20261009.zip; ZIP CRC verified, SHA256 58bbca0653f7dca2aa146ecfd30a5266a8f81dbe2eba7475b8b0cba871d95e46. Scripts are not separately committed; this report is.
