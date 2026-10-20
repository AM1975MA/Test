# ETF Trader V2 — 125-feature formula migration: independent source-only replay

Date: 21 October 2026
Status: **COMPLETE, 9-year paired validation. Do not promote corrected formulas to production.**

## Provenance and numerical oracle
- Exact source baseline: immutable original `regeneration/campaign/etf_trader/source_only/kernel_legacy_frozen_20261020.py`, Git blob SHA `351307d549fa70dea70f77cbefddfc24894b6882`.
- Corrected formulas: same repository kernel in `research-v2-formula-retrain-20261021`; canonical production-repo candidate is draft PR [AM1975MA/Etf_trader#2](https://github.com/AM1975MA/Etf_trader/pull/2).
- OHLCV frozen snapshot: [run 39482809691](https://github.com/AM1975MA/Test/actions/runs/39482809691), artifact `12292840548`, cutoff 2026-07-01.
- Official 500 canonical baskets, 24 members each; basket membership SHA256 `36a45916b5d8191f3ccd206f39bf3fd3f1ed4bcaffd474e352b69c598f2b6a5e`.
- Matched supervised training run: [39515716383](https://github.com/AM1975MA/Test/actions/runs/39515716383), result artifact `12307848715`, **success**.
- Economic replay run: [39516335427](https://github.com/AM1975MA/Test/actions/runs/39516335427), result artifact `12308480622`, **success**.
- EXACT NUMERICAL ORACLE: `LEGACY` scores vs original `leaves_127` full-result artifact `12294125130`: `15,198/15,198` same `(signal_date,ticker)` keys, maximum absolute raw score deviation `0.0` and mean deviation `0.0`.

## Frozen experiment contract
- Universe 149 ETFs, 101 fully matured 21-trading-day forward target months, signals 2018-01 through 2026-05 (monthly panel also contains June 2026 scores without matured forward labels).
- Annual expanding chronological training from 2012 with hard target exit before January 1 of fit year; fit anew for each of 2018–2026.
- Identical valid-row mask from frozen LEGACY >= 30/125 nonmissing features, identical tickers/dates, labels, baskets and seed sets.
- XGBRanker `rank:pairwise`, max_depth 0, `grow_policy=lossguide`, max_leaves 127, 360 boosting rounds, seeds (101,202,303).
- Treatments `LEGACY`: unchanged original 125 inputs; `DOWNVOL_ONLY`: replace the three underlying downvol with true zero-threshold downside deviations, with their percentile and robust deviation derived views; `CORRECTED`: all documented audited mathematical corrections, 125 compact inputs unchanged in count.
- Tail, Macro, expert mixing, overlays, risk and dynamic portfolio gates all **OFF**.

## All-universe and basket rankings
| Metric | LEGACY | DOWNVOL_ONLY | CORRECTED |
|---|---:|---:|---:|
| Universe IC mean | 0.042796 | 0.038953 | 0.038536 |
| Universe Top-1 hit | 6.931% | 7.921% | 8.911% |
| Universe Top-3 capture | 13.861% | 16.832% | 16.832% |
| Basket Top-1 hit | **15.087%** | 14.307% | 14.553% |
| Basket Top-3 capture | **35.745%** | 34.040% | 35.471% |
| Basket 21-day regret | 10.208% | 10.400% | 10.412% |
| Basket selected 21-day excess return | 0.916% | 0.723% | 0.712% |

Paired calendar-month bootstrap, circular 6-month blocks, 6,000 resamples; basket observations first aggregated by month, *never* treated as independent:
- Corrected minus Legacy basket Top-3: **-0.273 pp**, 95% exploratory CI **[-1.398, +0.933] pp**.
- Downvol Only minus Legacy basket Top-3: **-1.705 pp**, CI **[-2.689, -0.628] pp**.
- Corrected minus Legacy IC: **-0.00426**, CI **[-0.01176,+0.00423]**.
- Corrected minus Legacy universe Top-1 **+1.980 pp**, CI **[-1.980,+5.941]**; no statistically established improvement.
- Corrected minus Legacy basket selected 21-day excess: **-0.204 pp**, CI **[-0.464,+0.051] pp**.

## Economic next-open replay (XGB-only)
Methods: 500 canonical baskets, same cross-sectional percentile scores, next adjusted open fills, 10 bp on traded notional, no risk overlay, Top-2 75/25 unless score gap >=0.12 then 100% Top-1. First equity date 2018-02-02, last 2026-07-01.

| Metric | LEGACY | DOWNVOL_ONLY | CORRECTED |
|---|---:|---:|---:|
| Mean basket CAGR | **13.297%** | 11.021% | 12.057% |
| Median basket CAGR | **14.470%** | 11.615% | 13.554% |
| Aggregated NAV CAGR | **15.941%** | 12.951% | 14.729% |
| Mean MaxDD | -51.289% | -50.491% | **-50.341%** |
| Aggregated NAV MaxDD | -40.517% | **-38.106%** | -39.077% |
| Mean Sharpe, risk-free zero | **0.557** | 0.494 | 0.524 |
| Mean gross turnover / year | 17.094 | 17.010 | 16.983 |

Paired 21-trading-day bootstrap on **cross-basket mean daily log-return differences**, 4,000 resamples:
- Corrected minus Legacy annual log return: **-1.123 percentage points**, exploratory 95% CI **[-3.626,+1.365] pp**.
- Downvol Only minus Legacy annual log return: **-1.927 percentage points**, CI **[-4.847,+1.052] pp**.

### Interpretation
1. Mathematical correctness of lower partial moment (downvol) is unambiguous; **its isolated substitution in the old feature vector demonstrably removes information** needed by historical XGB decision boundaries, probably the frequency regime conveyed by structural NaN.
2. Full correction partially recovers lost basket Top3 and carries a higher universe-wide best-name capture, but no statistically compelling improvement vs Legacy in basket Top3/IC/CAGR.
3. Original full scorer (Tail + Macro) was not retrained here: the economic comparison is a clean XGB-only matched component replay. These CAGRs are **not** comparable to historically published full-score V2 CAGR numbers from differing windows/overlays.
4. Years 2018–2026 have already been repeatedly examined in previous ETF research; this is a rigorous matched **historical replay**, not a fresh untouched calendar holdout.
5. Preserve the corrected math as a versioned research basis and add explicit `negative_day_fraction{21,63,126}` and potential former missingness indicators only in a **new separately preregistered experiment**. Never deliberately revert to incorrect mathematical meaning under the same feature name.

## Decision and safety gate
**Do not merge draft PR #2 or overwrite production.** Preserve legacy checkpoints and cached scores for reproducibility. New formula version must always trigger complete from-scratch fitting and no stale score reuse. A full scorer/portfolio replay and independent time-source validation are separate prerequisites for production promotion.

This report and scripts reside on `research-v2-formula-retrain-20261021`, which is intentionally isolated from main.
