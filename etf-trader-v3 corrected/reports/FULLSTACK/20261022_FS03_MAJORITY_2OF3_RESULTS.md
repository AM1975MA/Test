# V3 Full-stack FS03 — majority 2-of-3 confidence vote in original risk-off Top2 sleeve

**22 October 2026: exploratory comparison completed; NO robust full-period improvement vs the original ETF_TRAINER_V2 risk-sleeve, NOT PROMOTED.**

Research action [GitHub run 39838818618](https://github.com/AM1975MA/Test/actions/runs/39838818618), artifact **12452641034**. [Predeclared source](../../fullstack_legacy/experiments/fs03_majority_risk_replay.py) and [pre-result protocol](./20261022_FS03_THREE_VOTE_PREREG.md). Same source-only as-of Titanium/S3B/MA3 Hybrid24 scores and risk from **FS02 run 39836842157**, artifact 12451018561; same original frozen 149 ETF price snapshot [run 39482809691](https://github.com/AM1975MA/Test/actions/runs/39482809691), original annual mature-OOS V3 Pairwise127 run 39700865721, canonical 500×24 membership SHA256 `36a45916b5d8191f3ccd206f39bf3fd3f1ed4bcaffd474e352b69c598f2b6a5e`.

## What actually changed versus ETF_TRAINER_V2

Only when the original source-only V2 DD-first/HighCAGR24 systemic risk budget is below 100% and the **original Hybrid24 Top1−Top2 score margin ≥0.03**, permit concentrating the already-allocated risky sleeve into its original Top1 when **at least two of three** as-of original predictors prefer Top1 over Top2: MA3 ExtraTrees Tail rank, MA3 XGBoost Tail rank and frozen original V3 CORRECTED Pairwise127 rank. The original ETF_TRAINER_V2 reference requires ET **and** XGB unanimous agreement. On 2017 dates before valid V3 original OOS scores, use **exact original V2 model-agreement** action, never fabricate V3 scores.

Crucially: **the Top1/Top2 names are NOT reordered**, original V2 Hybrid24 model + monthly smoothing 40/30/30 and producer BASE/Tail .475/.525 unchanged; original V2 DD-first systemic risk budget, V6 alternative, HighCAGR24 gross, daily original intraday/next-open executor, 10bp per traded notional unchanged. Zero V3 ranker refit or future outcome features. Paired 500 baskets share the same market days and much of the same ETFs.

FS03 checks original V2 Hybrid24 and ETF_TRAINER_V2 *both* archived per-day NAV and traded-notional paths to absolute tolerance 1e-10 **before** evaluating the new majority arm. The two-model V2 consensus is always a subset of majority-of-three: **41,965** V2 consensus basket×day riskoff actions, **52,715** majority actions, **10,750 incremental action basket×days**. Those counts are heavily autocorrelated exposures **not independent opportunities/trades**.

## Matched economic comparison

All CAGR values below are **arithmetic mean of CAGR over 500 individual baskets**. Daily equal-capital 500-basket *aggregate NAV CAGR* is shown separately. Calendar 2017-02-01 through 2026-07-01, 2,366 sessions. **Not** a virgin 2026 OOS research period.

| Metric | Original Hybrid24 full stack | Frozen ETF_TRAINER_V2 + ET/XGB agreement | New FS03 V3 majority 2/3 |
|---|---:|---:|---:|
| **Full-period mean basket CAGR** | 22.1772% | **22.4593%** | **22.4545%** |
| **Full-period aggregate NAV CAGR** | 24.7616% | **25.0915%** | 25.0538% |
| Mean MaxDD, 500 baskets | **−35.2972%** | −35.3786% | −35.5022% |
| Mean Sharpe (rf=0) | 0.86963 | **0.87402** | 0.87277 |
| 10th percentile basket CAGR | 10.8041% | 10.8948% | **11.0820%** |
| Worst single basket MaxDD | −64.997% | **−63.2049%** | −63.2073% |
| Annualized gross traded notional / NAV | 11.9102× | 11.5733× | **11.4746×** |
| 2017–2022 mean basket CAGR | 17.9112% | **18.3242%** | 18.3169% |
| 2023–2026 mean basket CAGR | 30.5149% | 30.5594% | **30.5668%** |
| 2022+ mean basket CAGR | 25.1255% | 25.4122% | **25.4722%** |

The FS03 majority vote is **nearly tied with best V2 Stage19**, but not better on the complete historical full period (difference −0.0048 percentage points mean CAGR; aggregate NAV CAGR −0.0377 percentage points, and slightly worse mean drawdown/Sharpe). FS03 improves 2022+ mean basket CAGR by +0.0600 percentage points and full p10 by +0.1872pp, but this is tiny, time-dependent and selected from extensively researched historical years. No policy promotion.

## Uncertainty and dependent baskets

Paired 3000×21-trading-day calendar-block bootstrap, 500 basket log-return differences averaged **within trading date first**:

- FS03−ETF_TRAINER_V2 full annualized paired log alpha **−0.000004**, exploratory CI95 **[−0.001132,+0.001136]**, includes zero.
- FS03−ETF_TRAINER_V2 later 2023+ annualized paired log alpha **+0.000068**, CI95 **[−0.000035,+0.000251]**, includes zero.
- FS03−ETF_TRAINER_V2 2022+ annualized paired log alpha **+0.000480**, CI95 **[−0.001466,+0.002679]**, includes zero.
- FS03−original Hybrid24 annualized paired log alpha **+0.002252**, CI95 **[−0.000317,+0.005409]**. This is not a clean gain over the *best* V2 Stage19 comparator.

These are calendar-averaged mean log-alpha estimands, not simple CAGR differences. Bootstrap under explored historical years is descriptive, not genuinely external prospective confirmation.

## Interpretation / next strict improvements

Full-stack V2 SOURCE code with combined producer, smoothing, dynamic Top2, DD-first and V6 was successfully restored in V3; original *best* source-only Stage19 ETF_TRAINER_V2 remains the benchmark at 22.4593% on this current source vintage. The new majority V3 vote is interesting for portfolio-tail/turnover analysis but does not establish full-period better performance. In particular, forcing Pairwise127 either into 25% Titanium base (FS01) or requiring unanimity in Stage19 (FS02) degraded CAGR; even majority vote (FS03) is not robustly superior.

Potential next research: conditional non-blind, regime-specific vote based on calibrated **incremental portfolio utility** of concentration versus original Stage19 decision, on only strictly earlier matured trade/market outcomes, with unchanged original V2 Top2 and risk gross. Pre-register a single policy and demand a truly unseen vintage for out-of-time generalization. Separately audit full 149 unrestricted investment universe with own matching source snapshot; the 43.15% older raw and 31.60% fresh raw must never be conflated with constrained baskets. Original production V2 and all frozen V3 model reference unchanged.

## Files

- [FS03 pre-registration](./20261022_FS03_THREE_VOTE_PREREG.md)
- [FS03 source](../../fullstack_legacy/experiments/fs03_majority_risk_replay.py)
- [FS02 complete-risk replay data source](https://github.com/AM1975MA/Test/actions/runs/39836842157)
- [FS03 complete outcome, 2,366-day daily NAV and 500 overlapping baskets](https://github.com/AM1975MA/Test/actions/runs/39838818618) — artifact 12452641034.
