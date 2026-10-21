# ETF Trader V3 Corrected — L07 complete frozen execution-aware economic diagnostic

**Completed:** 21 October 2026. **GitHub Actions run: [39683840686](https://github.com/AM1975MA/Test/actions/runs/39683840686)**, successful. Complete, independently inspectable ZIP artifact **12385666508** (`v3-l07-integrated-full-economic-results`). Code: [`experiments/l07_integrated/evaluate.py`](../../experiments/l07_integrated/evaluate.py). **No production changes and no new layer tuning.**

## Test protocol — execution, not ex-post 21D proxy

- Entire original source-only snapshot: **149 ETFs**, 500 **canonical fixed 24-ETF baskets**, archived from run 39482809691, SHA256 basket membership `36a45916b5d8191f3ccd206f39bf3fd3f1ed4bcaffd474e352b69c598f2b6a5e`.
- Compare strictly historical **annual out-of-year model scores**, independent of realized future portfolio results.
- `V2_LEGACY_RANKER_TOP2`: source-only ORIGINAL LEGACY ranker predictions from run **39515716383**, same-month percentile score, select Top1 if percentile gap>=0.12, otherwise Top2 weights 75/25. **This is the original ranker + Top2 reference, NOT the fully deployed V2 upper-layer chain.**
- `V2_CORRECTED_RANKER_TOP2`: mathematically corrected125 feature ranker from the same genuine mature-OOS run; same Top2 policy.
- `V3_TAIL_TOP3_STATIC`: locked unique45 Tail future-elite logistic classifier from run **39655513813**, select same three ETFs each month by frozen score, weights **50/30/20**, no L03 regime switch, no L04 blend, no L06 hard veto.
- `V3_TAIL_TOP3_ABS_SOFT`: same Tail Top3 names, strictly fitted past-only absolute <=−10% next21-day probability from run **39671493979**, weights `normalize(original_weight × exp(−3×p_abs_loss10))`, coefficient fixed **before** the test, available only 53 matched matured risk-score signal dates 2022-Jan..2026-May.
- Signals from month-end Close, trades at next trading-session Open, mark daily to adjusted Open, maintain actual units between rebalances, sell/buy current holdings; fee paid on true trade notional with exact self-financing fixed-point correction.
- Cost scenarios **0,10,20,50 bps** one-way executed notional; base reference **10 bps**. Do not confuse gross annual turnover with monthly selection churn.
- Compare same **53 risk-available monthly signals** (execution Feb 2022 through terminal 1 July 2026), same 500 baskets, and full period **2018-Feb through 2026-Jul** with 101 mature economic signal holding months for ranker + static Tail.
- No CAGR used to choose any layer during design. Prior period already repeatedly examined, therefore confidence ranges remain **exploratory rather than virgin OOS**.

## Results, identical matched period 2022-Feb – 2026-Jul, 10 bps

| Metric | Legacy V2 ranker Top2 | Corrected V2 ranker Top2 | V3 Tail Top3 | V3 Tail Top3 + abs-risk weights |
|---|---:|---:|---:|---:|
| Mean per-basket CAGR | **19.961%** | 16.476% | 12.237% | 12.530% |
| Median per-basket CAGR | 19.997% | 17.807% | 13.844% | 13.803% |
| p10 basket CAGR | +0.402% | −4.349% | −2.751% | −1.986% |
| **Aggregate NAV CAGR** (equal capital across baskets) | **23.157%** | 19.634% | 13.856% | 14.070% |
| **Aggregate NAV max drawdown** | **−17.829%** | −19.169% | −22.873% | −22.413% |
| Mean per-basket max DD | −38.065% | −37.980% | −35.876% | **−35.444%** |
| Worst single basket max DD | −84.496% | −84.641% | −72.221% | **−71.931%** |
| Mean per-basket Sharpe (risk-free=0) | **0.718** | 0.629 | 0.549 | 0.559 |
| Annualized actual gross trade notional / NAV | 16.532× | 16.493× | **8.566×** | 8.769× |

**Key finding:** frozen V3 does not improve mean or aggregated CAGR or Sharpe over original legacy Ranker Top2; lower turnover, improved *average single basket* DD and a better lower-tail worst-basket DD are genuine offsetting strengths. The aggregate NAV DD over the *2022+ period* is worse for V3 than original V2 ranker. Must distinguish per-basket and aggregate DD.

## Long historical period, 2018-Feb – 2026-Jul, 10 bps

| Metric | Legacy V2 ranker Top2 | Corrected V2 ranker Top2 | Frozen V3 Tail Top3 |
|---|---:|---:|---:|
| Mean per-basket CAGR | **13.297%** | 12.057% | 10.293% |
| Aggregate NAV CAGR | **15.941%** | 14.729% | 11.564% |
| Aggregate NAV max DD | −40.517% | −39.077% | **−36.344%** |
| Mean per-basket Sharpe | **0.557** | 0.524 | 0.487 |
| Annualized actual gross turnover | 17.094× | 16.983× | **9.383×** |

The 2018 long source-only V2 LEGACY ranker results reproduce the earlier independently archived economic scorecard: **mean CAGR 0.132973, aggregate CAGR 0.159410, aggregate DD −0.405174**, validating the source lineage.

## Cost sensitivity: matched period aggregated CAGR

| One-way fee | Legacy V2 Ranker Top2 | V3 Tail Top3 | V3 Tail + abs-risk |
|---|---:|---:|---:|
| 0 bps | 25.245% | 14.829% | 15.067% |
| 10 bps | **23.157%** | 13.856% | 14.070% |
| 20 bps | **21.105%** | 12.892% | 13.082% |
| 50 bps | **15.159%** | 10.055% | 10.174% |

Legacy V2 turnover is roughly double, so its advantage shrinks when costs rise, but the V3 does **not** surpass it even in the preregistered 50 bps stress.

## Yearly contribution and paired uncertainty

Ensemble NAV calendar-year returns (2026 is **partial**, through 1 July):

| Year | Legacy V2 ranker | V3 Tail Top3 | V3 Tail + abs-risk |
|---|---:|---:|---:|
| 2022 (from February) | +11.4% | −3.9% | −3.7% |
| 2023 | +5.4% | +2.2% | +2.5% |
| 2024 | +21.3% | +6.2% | +6.5% |
| 2025 | +51.6% | **+56.8%** | +56.4% |
| 2026 (partial) | +15.5% | +8.0% | +8.4% |

Paired **daily-calendar 21-trading-day circular block bootstrap**, 3,000 replications, 500 overlapping baskets aggregated BEFORE resampling:
- V3 Tail static versus Legacy V2 Ranker: mean annualized log-return delta **−0.0625**, exploratory 95% CI **[−0.1584,+0.0302]**, so positive/negative relative gain cannot be called statistically established across independent histories.
- V3 Tail + abs-risk versus V3 Tail static: mean annualized log-return delta **+0.0029**, 95% CI **[−0.000069,+0.00607]**; small and interval contains zero.
- Do not confuse this bootstrap log-uplift with an arithmetic difference of CAGR point estimates, and do not interpret dependent basket paths as independent replications.

## Verification PASS

- Source-only exact basket/ETF hash and all three OOS 102-month score/date/ticker matches validated previously in L07 preflight [39676155405](https://github.com/AM1975MA/Test/actions/runs/39676155405).
- The new **independent cost-aware executor matches the existing immutable V2 `source_only.execution.replay`** to **absolute tolerance 1e−10** on every daily NAV and turnover for LEGACY, in **BOTH matched53 and long101 periods**. Both control and new strategies run through the same new engine.
- Optional risk treatment uses identical original Top3 ticker set at every one of the 53 signal dates, all probabilities strictly fitted before test-year labels matured, all weights positive and summing to one.
- No ex-post return proxy substituted for daily open-price execution; actual path-dependent NAV, cost, turnover, MaxDD and Sharpe used.

## Decision

**Do NOT promote V3 to live production from these results.** The key research finding is a **misalignment between high upper-event Tail Top3 identification and realized long-horizon path-dependent wealth/Sharpe in the selected 50/30/20 portfolio**, with especially adverse relative economic outcomes in 2022, 2024 and part of 2026. A plausible mechanism is target/policy/exposure mismatch, but this test does not isolate causal drivers.

Next scientifically appropriate steps, separately:
1. Investigate L02 label horizon/objective and distribution conditional on extreme Tail event (21/42/63D) versus actual next-month return and its concentration; *no ex-post retuning on same years*.
2. Assess role of frozen central Pair127 in selecting portfolio names, rather than assume Tail's high capture is the correct financial top-three criterion. Preserve prior independent controls and use new vintage / nested research split.
3. Only after a different candidate is predeclared should full cost-aware L07 be rerun. Do not use CAGR from this historical replay to choose scores or weights retroactively.
4. A true **production V2 full-system versus V3** match additionally requires frozen original upper-layer (tail, macro, risk) configuration and its causal OOS score/decisions. It is NOT the current `V2_LEGACY_RANKER_TOP2` source-only comparator.

**No new virgin OOS period, no production change, no automatic trading or financial recommendation.**
