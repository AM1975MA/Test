# R0-P — Data + Superpowers: VERIFIED numerical amplification from real Yahoo price revisions
**2026-10-09 · research-only, no full V2 or ETF retraining · AM1975MA/Test `research/v2-xgb-immutable-checkpoints-20261008`**

**Frozen diagnostic before examination:** [R0-P preregistration](2026-10-09-r0p-real-feature-outlier-prereg.md), commit `f8542c742eb2df52bdaa182277a53dd093c9bca2`. The follow-up **illustrative** `epsilon=1e-6` was proposed **after observing the IYT sign-flip** and is exploratory *post-hoc mechanism confirmation*, NOT an independently validated production parameter.

## Decision

**REAL, EXACTLY REPRODUCIBLE FEATURE CONSTRUCTION DISCONTINUITY FOUND.** In actual Yahoo raw-close snapshot Repeat1 vs Repeat3, the adjusted Close of **IYT on 2007-06-28** differs by only ~5.72×10^-6 adjusted price units. The resulting daily log return switches sign from **+1.045489e-7** to **−1.045489e-7**. Original `rolling_downvol` treats negative returns as valid observations and nonnegative returns as NA. The one tiny sign flip:
- In **63 trading sessions** before **2007-06-29**, makes negative count **30→31**, meeting `min_periods=31` in Repeat3 only. IYT enters the cross-sectional downside-volatility median/MAD calculation in only one Yahoo acquisition.
- In **126 trading sessions** before **2007-10-31**, makes negative count **62→63**, meeting `min_periods=63` in Repeat3 only; a long-lived cohort discontinuity **four months after** the tiny quote revision.
- In the **21-session** window before 2007-06-29, negative count changes **11→12** (both pass min=10), but the downside volatility of IYT itself shifts **0.0064668 annualized units** solely because one near-zero return is added/removed from the conditional set.

This is a data-to-feature **threshold/cohort propagation mechanism before any XGBoost fit**, not merely noisy training labels and not a synthetic construction. It may contribute to previously observed X-only learner sensitivity, but its **causal contribution to 43.15% Golden→31.60% or the 4.92pp repeat span remains UNMEASURED**; the presence of these months in model train histories does not establish split or capital impact.

## Source-faithful formula (exact productive `kernel.py` semantics)

```python
lr = np.log(adjusted_Close.where(adjusted_Close > 0)).diff()
downvol_h = lr.where(lr < 0).rolling(h, min_periods=max(10, h//2)).std(ddof=0) * np.sqrt(252)
med = downvol_h.median(axis=1)
mad = (downvol_h - med).abs().median(axis=1).replace(0, np.nan)
downvol_h_dev = ((downvol_h-med)/(1.4826*mad)).clip(-8, 8)
```

The robust normalizer is **not numerically wrong**: its input cohort changes discontinuously because a near-zero sign changes whether an ETF has enough negative observations. Med/MAD amplify cohort changes into **other tickers' features even when their own raw downside-volatility values do not change**. A fixed physical trading effect or price gap is not involved.

## Actual examples validated from Repeat1 vs Repeat3 prices

| Source-visible event | Repeat1 | Repeat3 |
|---|---:|---:|
| IYT 2007-06-28 adjusted Close | 18.24360466003418 | 18.24359893798828 |
| IYT same-date daily log return | +1.04548897e-7 | −1.04548918e-7 |
| IYT negative returns over 63 sessions on 2007-06-29 | 30 | 31 |
| IYT `downvol63` available 2007-06-29 | NO | YES |
| Cross-section valid downside-vol63 ETF count that day | 21 | 22 |
| UNG *raw* downvol63 | 0.18993965232977053 | **0.18993965232977053** |
| UNG normalized `downvol63_dev` | **2.1530021957** | **2.5145808339** |
| SLV *raw* downvol21 2007-06-29 | 0.23678576522077308 | same |
| SLV `downvol21_dev` | **5.82376100597** | **4.91274771527** |
| Cross-section valid downside-vol126 count 2007-10-31 | 10 | 11 |
| LQD raw downvol126 2007-10-31 | 0.03500424908536 | 0.03500582505060 |
| LQD `downvol126_dev` | **−6.5512811** | **−5.5836344** |

**Direct cause of 63/126 median differences:** If the same common 21 ETF subset at 2007-06-29 is used for both price snapshots, median is 0.07981188052 vs 0.07981335376 and MAD 0.03450073790 vs 0.03449883247: UNG common-cohort normalized values **2.1530022 vs 2.1530923**, instead of 2.1530022 vs 2.5145808. Likewise for 126-day, same 10-member cohort removes the large LQD delta. This directly isolates the effect of one IYT availability flip, not a guess about numerator volatility drift.

## Replication of old forensic maxima (independent from the original result collector)

Using the same 149 frozen adjusted Close series and 270 monthly last-SPY-session dates, we reconstructed exactly the *previously archived* `forensics_v1/results/TITANIUM_INTERNAL.json` repeat1/3 extreme difference magnitudes to <1e-10. These are **real ETF observations** (early training history), not a new financial backtest.

| Feature | Repeat1 vs Repeat3 max absolute original normalized difference | Ticker and month | Comparison units |
|---|---:|---|---|
| `downvol21_dev` | 0.9110132907 | SLV, 2007-06-29 | normalized score units |
| `downvol63_dev` | 0.3615786382 | UNG, 2007-06-29 | normalized score units |
| `downvol126_dev` | 0.9676466902 | LQD, 2007-10-31 | normalized score units |

**Note early ETF availability:** only 63 raw `downvol21`, 21/22 `downvol63` and 10/11 `downvol126` valid constituents in the cited early-history months; the full original dataset has 149 tickers across the **total universe**, not 149 valid downside-volatility histories each of these dates. Claims should never obscure the dynamically small early cohort.

## Exploratory one-value precision stress test, NOT candidate authorization

A strictly illustrative numerical **deadband** treats daily log returns with `abs(r)<1e-6` as nonnegative for conditional downside-volatility inclusion (equivalently uses `r<-1e-6`), leaving all other source formulas and dates fixed. No CAGR tuning of epsilon: this fixed value was chosen to be comfortably larger than observed ambiguous ±1.045e-7 log return; it is nevertheless selected **after the example** and hence is not an independent test. It should not be claimed a universally correct provider precision bound.

The same 149 ETF and 270 monthly signal dates were evaluated in both price snapshots, no model fitting or trading:

| Original cross-snapshot feature instability | Native kernel | Exploratory 1e-6 guard |
|---|---:|---:|
| `downvol21_dev` max absolute delta | 0.911013 | **0.001516** |
| `downvol63_dev` max absolute delta | 0.361579 | **0.001115** |
| `downvol126_dev` max absolute delta | 0.967647 | **0.002604** |
| `downvol21_dev` vintage missingness disagreements | 1 | **0** |
| `downvol63_dev` vintage missingness disagreements | 6 | **0** |
| `downvol126_dev` vintage missingness disagreements | 2 | **0** |
| Abs delta >0.01, h=21 | 106 | **0** |
| Abs delta >0.01, h=63 | 267 | **0** |
| Abs delta >0.01, h=126 | 47 | **0** |

**Important change relative to source:** in the Repeat3 dataset alone, guard-vs-original creates **81**, **79** and **10** finite ETF-month values with differences >0.01 for h=21,63,126, and some cohort entries become missing. This is precisely why no claim of preserved predictive alpha is justified, despite the improvement in cross-snapshot input stability. If we blindly change existing historical features and refit, we have created a *new model* whose opportunity capture is not yet established.

## Reliability / Data checks

- All 149 ticker names are compared by exact symbol identity, no positional ETF pairing; exclude raw ZIP metadata CSV `universe.csv` and `coverage.csv`.
- Input ZIP SHA256 `fcc02918b3a42c3fecde273c4639ca4eed1b5f31e4b8c32aeea4c2a8e4c00f86` matches frozen R0-G vintage source.
- 270 monthly SPY-last-trading-day signals between 2004-02-27 and 2026-07-31; 3 horizons. Number of **finite paired raw normalized feature values** 18,416 (h21), 12,747 (h63), 8,689 (h126). Note R0-G used 267 months with mature forward labels; here no future label is needed, hence the counts/period differ legitimately.
- 3 focused TDD tests written and observed RED on missing module, GREEN after implementation (`pytest: 3 passed`). Test scope includes exact epsilon=0 formula parity, a one-return threshold discontinuity and median/MAD semantics.
- Independent Data validation confirmed source raw ZIP SHA, 149 symbols/270 months, all **three** previously frozen maximum difference values to <1e-10, all three guarded extremes <0.003, 3/3 availability disagreement elimination and 3/3 changes-to-original warnings; **Data QA PASS**.
- No XGBoost, MA3, portfolio, full-V2 or real performance fit/test performed. The guard is **not** a completed V2 stability fix; other engineered features (including sign entropy, ranks, cross-category cluster features), true XGBoost histogram split ambiguity, target label flips, MA3 preprocessing and different data vintages remain.

## Narrow, financially responsible next step

**This is the first genuinely measured upstream *feature* mechanism that does not require altering the learner to address a discontinuity.** A defensible engineering next action is to design a principled **source-vintage-uncertainty treatment for sign-sensitive rolling features** and a **causal feature/label/cohort fingerprint**, in isolated Test with TDD and untouched V2. Do not blindly promote this specific 1e-6 guard or optimize epsilon using the burned Original149 CAGR. Before even an isolated new financial challenger, verify output/missingness for **all 125 features**, train eligibility and MA3 universe dependencies and avoid erasing true small but informative negative returns; save original model checkpoints and evaluate one preregistered candidate on genuinely new point-in-time data through full V2 with daily DD and rare-upside capture. If such data are absent, retain original production learner and record measured source-side instability as a reproducibility engineering bug.

### Archived analyses
- Baseline: `forensics_v1/results/TITANIUM_INTERNAL.json`.
- Supporting source files available in conversation ZIP `ETF_Trader_V2_R0P_Real_Feature_Root_Cause.zip`: `r0p_real_downvol_audit.py`, `r0p_rootcause_probe.py`, `r0p_iyt_signflip.py`, `r0p_numeric_guard/audit_all.py`, `r0p_numeric_guard/data_validation.py`, `ETF_R0P_*.json`, `ETF_R0P_top_feature_cases.csv`, TDD tests.
- Research-only minimal code and tests committed at `target_redesign_level2_v1/feature_stability_r0p/numeric_guard.py` and `tests/test_numeric_guard.py`, NOT vendored/production source.
