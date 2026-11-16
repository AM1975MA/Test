# OLC111 — independent result analysis

## Finding

**The study did not discover alpha.** On the primary following-Close convention, BASE earns **22.57% CAGR**, PRICE **18.56%**, VIX **17.18%**, and TERM **15.95%**. TERM also has worse prequential MSE than VIX for all three action heads. Lower drawdown in some learned paths does not establish an information advantage: the paths change exposure, preserve old inventory, and spend long periods in cash. These are historical, exploratory results from an already inspected period.

The independent audit reproduces all 18 paths without changing any saved NAV, fee, order, model, or policy. The full account period is **2020-03-02 through 2026-10-30**. The common learned-policy evaluation period begins **2022-07-04**, with the actual **2022-07-01 closing NAV** as each account's denominator. All 12 learned-policy paths match their same-scenario BASE account exactly through that readiness close. STATIC_75 has a different exposure mandate and is not expected to match BASE.

Sources: [`INDEPENDENT_DIAGNOSTICS.json`](../../results/INDEPENDENT_DIAGNOSTICS.json), [`INDEPENDENT_SCORES.csv`](../../results/INDEPENDENT_SCORES.csv), [`FIT_READINESS.json`](../../results/FIT_READINESS.json), and the frozen [`DESIGN_AND_PROTOCOL.md`](../../docs/DESIGN_AND_PROTOCOL.md).

## Primary results

The primary scenario executes at the following accepted Close with EUR1 plus 15 bp per actual filled order. MaxDD samples both the pre-fee account mark and the recorded Close. Percentages below are rounded; the JSON and CSV retain full precision.

| Policy | Whole-period CAGR | Whole-period MaxDD | Post-warmup CAGR | Post-warmup MaxDD | Post-warmup mean exposure | Full-cash sessions |
|---|---:|---:|---:|---:|---:|---:|
| BASE | 22.57% | -36.51% | 20.01% | -36.51% | 99.77% | 0 |
| STATIC_75 | 18.38% | -30.08% | 16.53% | -28.64% | 75.40% | 0 |
| MEAN | 16.23% | -36.10% | 10.58% | -22.34% | 100.00% | 0 |
| PRICE | 18.56% | -36.53% | 14.02% | -36.53% | 83.88% | 178 |
| VIX | 17.18% | -36.10% | 11.97% | -34.72% | 66.21% | 373 |
| TERM | 15.95% | -36.10% | 10.17% | -29.70% | 74.46% | 282 |

All full-cash sessions in these learned paths occur after readiness. The full-period CAGR includes almost 2.3 years of common BASE warmup and must not be attributed entirely to the learner. For the primary learned paths, the post-warmup denominator is EUR17,631.835384592854. STATIC_75 uses its own EUR15,883.039595 preceding balance.

Primary terminal equity from EUR10,000 is EUR38,816.56 for BASE, EUR30,780.90 for STATIC_75, EUR27,243.27 for MEAN, EUR31,100.60 for PRICE, EUR28,758.70 for VIX, and EUR26,812.67 for TERM. Actual filled-order fees are EUR4,029.40, EUR2,633.73, EUR881.17, EUR1,190.19, EUR1,848.82, and EUR1,393.87 respectively. Those fee totals are already embedded in NAV.

The scientific figures show log-scaled relative wealth and sampled drawdown. The post-warmup figure includes the preceding Close anchor, so the first post-warmup return is retained. The full figure shades the common model warmup.

- [`INDEPENDENT_PRIMARY_POSTWARMUP.png`](../../results/INDEPENDENT_PRIMARY_POSTWARMUP.png)
- [`INDEPENDENT_PRIMARY_FULL.png`](../../results/INDEPENDENT_PRIMARY_FULL.png)

## Execution and cost sensitivities

Each cell gives **whole-period CAGR / post-warmup CAGR**. These are the three frozen scenarios, with no refitting for the stress cases.

| Policy | Following Close | Following Close, double costs | Following Open sensitivity |
|---|---:|---:|---:|
| BASE | 22.57% / 20.01% | 19.71% / 17.26% | 25.75% / 23.23% |
| STATIC_75 | 18.38% / 16.53% | 16.01% / 14.10% | 20.50% / 18.66% |
| MEAN | 16.23% / 10.58% | 15.24% / 10.58% | 17.21% / 10.58% |
| PRICE | 18.56% / 14.02% | 17.33% / 13.68% | 20.37% / 15.20% |
| VIX | 17.18% / 11.97% | 15.49% / 10.94% | 17.96% / 11.67% |
| TERM | 15.95% / 10.17% | 14.61% / 9.66% | 18.63% / 12.64% |

TERM's post-warmup CAGR difference from VIX is -1.80 percentage points for primary Close, -1.29 points with double costs, and +0.98 points for the Open sensitivity. This sign reversal weakens robustness; it does not reverse the negative primary forecast and account evidence. The Open convention retains the protocol's final-daily-volume availability limitation and is not certified opening-auction execution. None of the 18 paths meets the 30% whole-period CAGR target.

## Forecast information test

The audit independently recomputes date-balanced errors from the saved prequential ledger on `ALL_HEADS_READY` support and agrees with every saved forecast score. It verifies that the maximum training terminal index precedes the fit cutoff and that reported outcomes precede the reporting cutoff. It does not rebuild the counterfactual label bank.

| Head | VIX MSE | TERM MSE | TERM relative MSE change | TERM positive-buffer mean realized log advantage | TERM separated positive-buffer episodes |
|---|---:|---:|---:|---:|---:|
| CASH | 0.0039126730 | 0.0039859283 | +1.87% | -0.0021285551 | 9 |
| FRESH | 0.0015870574 | 0.0016013589 | +0.90% | +0.0064813838 | 6 |
| ENTRY | 0.0039371691 | 0.0040041819 | +1.70% | -0.0065603896 | 19 |

There are 1,050 common evaluation dates for CASH and ENTRY and 980 for FRESH. TERM fails the incremental information test on every head. Its CASH and ENTRY signals with positive buffers have negative average realized advantages on the bank states. These overlapping 21-session forecast-label outcomes are not additive portfolio returns, are not annualized into CAGR, and are not the causal profit of the repeated policy.

Sources: [`PREQUENTIAL_FORECASTS.csv.gz`](../../results/PREQUENTIAL_FORECASTS.csv.gz), [`FORECAST_SCORES.csv`](../../results/FORECAST_SCORES.csv), and the `forecast` section of the independent diagnostics.

## Filled actions and evidence limits

Count actual filled instructions, not intended trace signals or individual ETF order rows. For each action family, greedily select signal dates at least 21 panel sessions apart, after requiring that `signal_idx + 21` is within the recorded history. Each cell gives **filled instructions / completed, separated episodes** for the primary scenario.

| Policy | CASH | FRESH | ENTRY |
|---|---:|---:|---:|
| MEAN | 0 / 0 | 0 / 0 | 0 / 0 |
| PRICE | 1 / 1 | 4 / 4 | 1 / 1 |
| VIX | 4 / 4 | 13 / 5 | 4 / 4 |
| TERM | 3 / 3 | 4 / 4 | 3 / 2 |

The same completed episode counts hold in both sensitivities. No learned action family reaches the predeclared 12-episode evidence threshold. TERM's final ENTRY is filled after the 2026-10-19 signal, but its 21-session endpoint lies beyond the dataset. The original native `entry_realized_instructions = 3` remains correct; the stricter completed-window audit reports only two completed ENTRY episodes. This is a denominator clarification, not a revision of orders or returns. Temporal spacing does not by itself establish independent treatment effects or supported counterfactual outcomes.

Source: [`INDEPENDENT_INTERVENTIONS.csv`](../../results/INDEPENDENT_INTERVENTIONS.csv).

## Actual account behavior and state support

MEAN authorizes no learned action and therefore holds its last warmup inventory instead of continuing the selector's monthly rotations. Its longest continuous ownership reaches **1,104 sessions**, compared with 190 for BASE and STATIC_75, 403 for PRICE, 190 for VIX, and 452 for TERM. Continuous ownership is reconstructed from fills: a top-up or partial sale preserves age, while complete liquidation followed by re-entry resets it.

PRICE's only full-cash spell lasts **178 sessions**, from the 2025-07-21 Close through 2026-04-01, with the next invested Close on 2026-04-02: 255 calendar days from first cash Close to next invested Close. VIX and TERM each have a longest spell of **193 sessions**, from 2025-06-30 through 2026-04-01, or 276 calendar days until the next invested Close. TERM also stays in cash for 42 sessions in late 2024/early 2025 and for 47 sessions in August–October 2026. The primary paths' cash spells are fully observed rather than right-censored.

The largest recorded absolute standardized price feature in the FRESH head is 7.85 for MEAN, 6.18 for PRICE, 6.94 for VIX, and 6.84 for TERM. CASH-head maxima are 3.34, 2.99, 3.09, and 3.06 respectively. These extremes are descriptive state-distribution diagnostics using each contemporaneous training scaler. They are not a calibrated OOD test and do not license retrospectively changing thresholds. The full JSON stores dates, actions, 95th/99th percentiles, and maxima separately by head and scenario.

The results expose a continuation mismatch: training labels compare a one-time intervention followed by monthly BASE continuation, while the repeated learned account can skip monthly rotations and stay in cash for many months. This is a concrete mechanism diagnosis. It does not prove that one particular behavior caused the whole return deficit. The separate OLC112 design tests only the invested monthly-rotation mechanism after inspecting these results; it cannot validate OLC111's options-information claim retroactively.

Sources: [`INDEPENDENT_CASH_SPELLS.csv`](../../results/INDEPENDENT_CASH_SPELLS.csv), the `held_marks` and `trace` sections of the independent diagnostics, and [`OLC112 design`](../../../olc112/docs/DESIGN_AND_PROTOCOL.md).

## TERM versus VIX year attribution

In the primary post-warmup period, the annual additive log-wealth increments of TERM minus VIX are -0.003980 for partial 2022, -0.126559 for 2023, -0.055601 for 2024, +0.146720 for 2025, and -0.030646 for partial 2026. They sum to **-0.070066**, a final relative wealth ratio of **0.93233**. Only 2025 contributes positively; removing that year's positive increment leaves -0.216785. Annual simple-return differences are also saved but are not summed as wealth attribution.

Source: [`INDEPENDENT_TERM_VIX_ANNUAL.csv`](../../results/INDEPENDENT_TERM_VIX_ANNUAL.csv). Complete annual performance for every path is in [`INDEPENDENT_ANNUAL_RETURNS.csv`](../../results/INDEPENDENT_ANNUAL_RETURNS.csv).

## Drawdown and recovery

These are the worst sampled episodes inside the common post-warmup window, with each drawdown history anchored to the actual preceding Close.

| Policy | Peak | Trough | Recovery | Peak-to-recovery sessions |
|---|---|---|---|---:|
| BASE | 2026-05-28 | 2026-10-16 | Not recovered by 2026-10-30 | — |
| STATIC_75 | 2026-05-28 | 2026-10-16 | Not recovered by 2026-10-30 | — |
| MEAN | 2024-10-07 | 2025-04-11 | 2026-01-14 | 319 |
| PRICE | 2024-12-09 | 2025-04-09 | 2026-04-16 | 338 |
| VIX | 2024-07-16 | 2024-09-06 | 2024-11-07 | 82 |
| TERM | 2024-07-16 | 2024-09-06 | 2024-11-11 | 84 |

MEAN, VIX, and TERM's worst **whole-period** drawdown is the shared warmup episode from the 2020-03-19 peak to the 2020-08-11 trough, recovered on 2022-06-08. Consequently their equal whole-period -36.10% MaxDD does not summarize their different learned-policy risks.

## Accounting, quote support and reproducibility

The independent reconstruction applies every filled buy and sell to economic units and cash, including its actual cost, and values held units from the latest positive finite **observed** raw Close. It scans every complete daily account calendar; missing sessions are rejected. Across the 18 accounts it checks **56,166 held-asset closes**. There are 126 held-asset closes without a current accepted raw quote, but every such position has an accepted prior quote within the permitted age. Maximum source age is **five calendar days**, with **zero** violations above five and no held assets lacking any accepted mark.

All 18 unit-count, cash, and NAV reconstructions pass. The maximum absolute cash discrepancy is EUR1.0551e-10 and NAV discrepancy EUR1.1642e-10. All whole/post financial fields match native `METRICS.json` and `SCORES.csv`; the largest field difference with round-trip CSV parsing is 3.33e-16. Source SHA-256 hashes are recorded in the JSON. Any future unsupported held mark is explicitly non-promotable and remains in the violation ledger; the audit never changes NAV to conceal it. The current violation CSV is empty with its schema retained.

Validation: **77 tests pass**, including 14 independent result-audit tests. The tests cover preceding-NAV anchoring, sampled drawdown/recovery, calendar CAGR, cash-spell gaps and censoring, log attribution, filled/completed episode counts, exact warmup, source-age boundary/sale timing, invalid marks, continuous ownership through top-ups/partial sales, liquidation/re-entry, and missing daily-session rejection. A separate read-only review reproduced the principal metrics and inspected helper conventions.

Reproduce from the OLC111 directory:

```bash
python -m unittest discover -s tests -v
python src/analyze_results.py
```

Sources: [`INDEPENDENT_TESTS.log`](../../results/INDEPENDENT_TESTS.log), [`analyze_results.py`](../../src/analyze_results.py), and [`test_result_metrics.py`](../../tests/test_result_metrics.py).

The account audit does not remove the frozen panel's current-catalog/survivorship and adjustment-vintage limitations, certify intraday executability, rebuild counterfactual labels, or create a fresh holdout. No model is promoted, no threshold is relaxed, and no claim of discovered alpha follows from these results.
