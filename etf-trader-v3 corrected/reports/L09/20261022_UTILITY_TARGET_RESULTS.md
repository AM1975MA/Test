# V3 L09 — 21-trading-day expected-utility objective experiment

**Completed 22 October 2026. Decision: REJECT BOTH NEW MODELS. No V3 reference model or V2 production changes.**

- Verified successful prediction fit: [GitHub Actions 39690121638](https://github.com/AM1975MA/Test/actions/runs/39690121638), artifact **12388882435**, `v3-l09-21d-utility-complete`.
- Verified successful matched execution and loss-functional diagnostic: [GitHub Actions 39691623601](https://github.com/AM1975MA/Test/actions/runs/39691623601), artifact **12388986240**, `v3-l09-utility-economic-replay`.
- Rejected earlier superseded run **39690087601** (before correcting the sign of the below−10% downside term); it was NOT used for the numbers here. Extra duplicate run **39690260857** triggered by the addition of economic source while prior fits were running and is not used for the reported result.
- Preregistered experiment and literal source code: [protocol](./20261022_UTILITY_TARGET_PROTOCOL.md), [train/test](../../experiments/l09_utility_target/evaluate.py), [calendar bootstrap](../../experiments/l09_utility_target/aggregate.py), [functional loss exposure](../../experiments/l09_utility_target/functional.py), [economic replay](../../experiments/l09_utility_target/economic.py).

## One narrow hypothesis, fixed controls

After L08 found that high rare-elite Tail Top3 capture fails to translate into net portfolio value, test whether directly forecasting the **exact next-open +21-trading-session expected relative return** improves investor selection quality.

All **125 corrected Compact features, 149 original ETFs, 500 original 24-ETF baskets, 2012+ expanding training calendar, annual chronological refits, 127 max leaves, 360 trees, 3 seeds, median future-return centering and a strictly mature 21D training label** were retained. Compared the frozen historical `CORRECTED` XGBRanker pairwise baseline from run 39515716383 with:

1. `L09_EXCESS21`: XGBRegressor `reg:squarederror` trained on 100× clipped [−.25,+.25] median-centered *actual 21D log return* from next market open. This changes both the learning objective and target relative to the baseline, a controlled target-alignment alternative.
2. `L09_DOWNSIDE21`: identical regressor and every other condition, except an additional **−0.5×clip(log(.9)−log(1+future ETF return),0,.20)** term in the training label. It is exactly **zero for any return ≥−10%**, strictly penalizing only worse losses. The coefficient was not searched.

Both new models were refit on independently mature *historical* labels before every held-out test year. Test-year future return and future cross-sectional median were **never features**, only evaluation outcomes. Nothing in L02–L07 was enabled, changed or retuned.

## 101-month intrinsic forecasting, OOS 2018–May2026

| Metric | Corrected Pairwise127 frozen | L09 21D relative return | L09 21D relative return + loss penalty |
|---|---:|---:|---:|
| Mean monthly universe RankIC | 0.038536 | **0.059904** | 0.056782 |
| Best realized ETF included in basket Top3 | **35.4713%** | 20.1465% | 19.6950% |
| Top1 best ETF rate | **14.5525%** | 9.7505% | 8.9683% |
| Basket nDCG@3 | **0.542279** | 0.541367 | 0.536965 |
| Basket Top1 selected 21D oracle regret | **0.104115** | 0.106939 | 0.109119 |
| Top1 selected excess over equal-ETF basket mean | **0.007122** | 0.004298 | 0.002118 |

**Prediction verdict:** both new models fail the principal task, notwithstanding greater universe-wide rank IC. The Top3 capture decrease relative to frozen corrected pairwise ranker is −15.32pp for raw return and −15.78pp for downside-penalized; paired 6-month calendar-block 95% intervals [−18.44,−12.12]pp and [−18.83,−12.58]pp respectively, with exploratory Holm-adjusted p≈0 in both comparisons.

## Task-aligned portfolio quality, SAME Top2 / Top3 candidates per prediction

Only score rankings changed; the portfolio policy in each comparison stayed exactly fixed and was applied to 500 identical baskets with identical future 21D outcomes. Top2 is the original gap-based V2-like policy, Top3 weights [50%,30%,20%].

| Metric, Top3 policy | Corrected pairwise | Excess21 regression | Asymmetric loss utility regression |
|---|---:|---:|---:|
| Weight invested in ETFs that *will lose ≥10%* over next21D | 8.4861% | 5.8248% | **5.5842%** |
| Weight invested in future best basket ETF | **12.5818%** | 7.5628% | 7.2323% |
| Weighted next21D realized [0–1] rank quality | **0.524852** | 0.522934 | 0.518505 |
| Weighted regret vs realized basket best ETF | **0.105470** | 0.106808 | 0.107728 |

Important: the **reduction in actual future large-loss exposure is material within this historical sample** and confirms the penalty biases toward safer outcomes, but it is **not a free improvement**: it also loses substantially more payoff from true future winners.

Top2 loss≥10% exposure falls from **8.9644%** (frozen corrected) to 6.5119% (excess label) and **6.1327%** (asymmetric utility). Paired month block CI asymmetric minus baseline loss exposure: **[−4.28,−1.43] pp**, but winner weight and quality simultaneously fall. Do not promote a losing selector merely for being more risk averse.

## Actual fee-aware self-financing economic replay

Next trading-session adjusted Open after month-end signal, positions drift with market prices, fees 10bps on actual traded notional; exact same daily executor across every arm. Original LEGACY Top2 replay matched immutable source-only engine to within 1e−10 on both test windows.

| Score with original Top2 policy | CAGR equal-capital 500-basket NAV 2022–Jul2026 | CAGR NAV 2018–Jul2026 | Aggregate MaxDD 2022–26 | Mean Sharpe 2022–26 |
|---|---:|---:|---:|---:|
| LEGACY original reference | **23.1568%** | **15.9410%** | −17.8287% | **0.7175** |
| Frozen CORRECTED Pairwise127 | 19.6339% | 14.7292% | **−19.1692%** | 0.6289 |
| L09 EXCESS21 | 16.2964% | 11.7519% | −24.1711% | 0.5881 |
| L09 DOWNSIDE21 | 13.5271% | 9.7945% | −20.9527% | 0.5153 |

Under a fixed **Top3** policy on same **2022–Jul2026** window, aggregate CAGR is CORRECTED Pair127 **17.7774%**, EXCESS21 **15.1996%**, DOWNSIDE21 **13.0281%**; full 2018–Jul2026 Top3 CAGR 13.8830%, 11.6172%, 10.4730%. Historical economic results agree with the failure of the intrinsic ranking objective.

Paired 21-trading-date block bootstrap on 500-basket-aggregated daily log performance, 1500 replications: 2022–26 EXCESS21 Top2 minus corrected pairwise Top2 **−0.0213** annualized log alpha (exploratory CI [−0.1051,+0.0636]), and DOWNSIDE21 Top2 minus corrected **−0.0424** (CI [−0.1311,+0.0390]). These intervals cross zero and are not untouched proofs, notwithstanding economically inferior aggregate CAGR point estimates. Treat the *large reduction in winner capture* as the stronger negative layer evidence.

## Decision and future separate research direction

**REJECT both L09 regression utility heads; keep original corrected Pairwise127 and the independent Tail expert frozen.** The hypothesis that a single asymmetric next21D expected utility label would resolve model-to-portfolio mismatch is **disproved for this particular formulation and model family** in explored historical data. The increased universe RankIC is not enough to justify replacing a model that better retrieves top buy candidates.

This experiment supplies actionable **error asymmetry evidence**: absolute next21D loss information can reduce risky exposures, but collapsing general alpha and downside protection into the same score discards strong winning opportunities. Any next proposal should preserve distinct **alpha ranking** and **severe-loss event risk score**, with any coupling tested through predeclared, chronological, training-only decision calibration, not a fixed large penalty tuned on the same OOS sample.

**Prior research reused the same 2018–2026 calendar for model and strategy decisions. This is an exploratory reproduction, not virgin external validation. No portfolio configuration or V2 production release was modified.**
