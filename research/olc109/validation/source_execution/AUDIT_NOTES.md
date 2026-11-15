# OLC109 — independent source and execution review

**Bounded result:** 200 completed paths (110 original, 50 adaptive stage 2, and 40 adaptive stage 3), 49,055 recorded orders, and 257 actually traded ISINs were reviewed. No newly used material source event or obvious new source-price corruption was identified. Recorded quantities and NAV reconcile independently. This is a source-accounting result, not a certificate that the orders were executable at the reported Open.

## Independent reconstruction and staleness

The audit accumulates signed quantities and cash flows from ORDERS without importing strategy or engine code. Every residual unit remains in the cash/NAV reconstruction. Accepted Close is carried causally from its last observed source row; invalid and zero-volume raw rows never become replacement marks. The 1e-10 unit threshold is used only to describe economic holdings and stale exposure.

Maximum absolute differences from recorded decision snapshots: units 3.64e-12, cash EUR1.16e-10. Maximum daily Close NAV difference is EUR1.24e-10. Maximum value of numeric dust is EUR1.46e-11. There are 0 invalid-Open fill findings and 0 accepted-panel/raw-price discrepancies in the bounded source histories.

Maximum Close quote age for an economic holding is **5 calendar days**. There are **0 held asset/path sessions older than 5 days**. All five quarantined series remain absent from the panel and recorded orders. See `RECONSTRUCTION_CHECKS.csv`, `PATH_SOURCE_EXECUTION_SUMMARY.csv`, and `HELD_STALENESS_EVENTS.csv.gz`.

Opening marks that fall back to the prior accepted Close also have maximum quote age **5 calendar days**, with **0 economic asset/path sessions older than 5 days**. This check includes the interval from the source Close date to the current opening mark date.

## Execution participation

Participation = recorded EUR order notional / (raw EUR Close × that venue's full-day reported volume). This is deliberately a descriptive ex-post denominator. It does not observe opening auction volume, order-book depth, spread, primary-market creation/redemption capacity, or trading at other venues. The five scenario paths repeat related economic opportunities; pooled counts are not independent market observations.

| Stage | Paths | Orders | Orders ≥10% | Orders ≥100% | Maximum ratio |
|---|---:|---:|---:|---:|---:|
| stage1 | 110 | 24,230 | 682 | 78 | 14.2883× |
| results_stage2 | 50 | 11,897 | 397 | 16 | 15.4086× |
| results_stage3 | 40 | 12,928 | 237 | 13 | 27.0127× |

Across all paths, **1,316 orders are at least 10%** and **107 are at least 100%** of full-day venue turnover. There are 0 missing or nonpositive denominators. The maximum is **27.0127×**, a SELL of M9SD.DE on 2020-11-03 in `HORIZON252__LAG1`: notional EUR3,068.64, raw Close EUR113.599998, volume 1, full-day turnover EUR113.60.

Selected BASE paths:

| Path | Orders | ≥10% | ≥100% | Maximum participation |
|---|---:|---:|---:|---:|
| CLUSTER_DUAL21__BASE | 232 | 3 | 0 | 37.87% |
| CLUSTER_DUAL_PEERS2__BASE | 235 | 1 | 0 | 34.72% |
| DUAL21__BASE | 230 | 61 | 6 | 940.97% |
| LIQ_DUAL21__BASE | 213 | 13 | 0 | 46.47% |
| CLUSTER_PEERS2_RISK15__BASE | 263 | 1 | 0 | 16.13% |
| CLUSTER_PEERS2_RISK20__BASE | 258 | 1 | 0 | 22.37% |
| DEDUP_DUAL21__BASE | 226 | 12 | 0 | 52.16% |
| DEDUP_DUAL_PEERS2__BASE | 240 | 14 | 0 | 62.13% |
| CAPITAL_3H_TILT__BASE | 683 | 2 | 0 | 13.41% |
| CAPITAL_3H__BASE | 643 | 2 | 0 | 13.90% |
| HORIZON126_TOP1__BASE | 115 | 1 | 0 | 11.83% |
| HORIZON126__BASE | 333 | 2 | 0 | 29.37% |
| HORIZON252_TOP1__BASE | 79 | 7 | 0 | 22.56% |
| HORIZON252__BASE | 266 | 3 | 0 | 15.29% |
| HORIZON63_TOP1__BASE | 123 | 14 | 0 | 42.96% |
| HORIZON63__BASE | 346 | 7 | 0 | 29.14% |

Concentrated TOP1 controls and delay stresses:

| Arm | BASE maximum | LAG1 maximum | LAG2 maximum | Orders ≥100% across all scenarios |
|---|---:|---:|---:|---:|
| HORIZON63_TOP1 | 42.96% | 293.07% | 222.13% | 3 |
| HORIZON126_TOP1 | 11.83% | 14.18% | 14.63% | 0 |
| HORIZON252_TOP1 | 22.56% | 223.16% | 65.95% | 2 |

Every TOP1 BASE case has zero orders at or above 100% of venue turnover. Some delayed HORIZON63_TOP1 and HORIZON252_TOP1 orders exceed that level; concentration and execution timing therefore still require explicit scrutiny. See `TOP1_PARTICIPATION_SUMMARY.csv`.

The rolling EUR100,000 signal filter reduces participation problems in several paths, but it cannot ensure sufficient volume on a later exit or delayed execution day. Fixed transaction-cost assumptions do not establish attainability of the larger orders. This limitation matters even when source quotes themselves are valid. The complete per-order evidence is `EXECUTION_PARTICIPATION.csv.gz`.

## Source-event coverage and actual use

The audit combines the frozen V3 source catalogue with a fresh bounded scan of histories of actually traded instruments and the three specifically requested suspicious Open cases. Review triggers are adjustment-factor change >10%, adjusted Close return >30%, raw or adjusted Open jump >30%, accepted-panel jumps >30%, and existing frozen flags. The catalogue has 512 event rows, including 64 material review-trigger rows. It is not a universe-wide rescan or a new primary-source validation of every quote.

An event counts as directly used only when its accepted Open supplies a fill or opening mark, or its accepted Close supplies a held Close mark or later carry/fallback. Holding an instrument on a date whose raw quote was discarded is insufficient to count that discarded quote as used.

There are 250 event/path uses across 8 distinct source dates. 7 dates are newly held ordinary dividend-factor context; material direct uses are individually retained in the event evidence. None of those new dividend-context dates meets the fresh material thresholds. No source or outcome was deleted or changed.

### 7 new ordinary dividend-context dates

| Symbol | Date | Paths holding source event | Factor multiplier | Provider cash-dividend multiplier | Fills |
|---|---|---:|---:|---:|---:|
| EXX1.DE | 2023-07-17 | 25 | 1.0435273 | 1.0435273 | 0 |
| LYMH.DE | 2023-12-12 | 35 | 1.0223646 | 1.0223647 | 0 |
| LYMH.DE | 2025-12-09 | 5 | 1.0304746 | 1.0304745 | 0 |
| EXX1.DE | 2025-07-15 | 25 | 1.0346306 | 1.0346306 | 0 |
| IS0R.DE | 2022-11-17 | 5 | 1.0249100 | 1.0249099 | 0 |
| DXSA.DE | 2025-08-20 | 5 | 1.0346745 | 1.0346746 | 0 |
| IQQB.DE | 2022-09-15 | 40 | 1.0418513 | 1.0418512 | 0 |

These were already labelled `DESCRIPTIVE_CONTEXT_ONLY` in the frozen review. Their factor changes agree with the recorded provider dividend arithmetic to an absolute log residual below 1.1e-7. This arithmetic check supports retaining the existing descriptive classification; it does not independently certify issuer ex-dates or point-in-time adjustment availability. All reconciled context dates have positive volume and accepted observations; their event-day fills are reported explicitly in the table. See `NEW_CONTEXT_EVENT_RECONCILIATION.csv`.

### Known material events and unusual Opens

**VOOL, 12 March 2020:** used in 110 paths. Four new simulated sells use the event's Open: CLUSTER_DUAL_RISK15/20 and DEDUP_DUAL_RISK15/20, all LAG2. Notionals range from EUR347.31 to EUR774.80; participation ranges from 0.0108% to 0.0242% of that day's EUR3,205,817.60 venue turnover. The event was already marked in V3; the newly used execution type is explicitly retained in the evidence. Its accepted Close move is +29.2082%, with unchanged adjustment factor. No new source-error finding follows from this volatile move, while exact Open execution is still not independently certified.

**LBRA, 26 October 2026:** no direct accounting or selected-history use in OLC109. The prior review's issuer-NAV corroboration and its warning that the exact EUR22.84 Xetra Open was not certified remain applicable to the archived V3 event; no fresh LBRA source investigation was needed here.

**F703, 18 March 2020; IQSE, 15 February 2021; UEQU, 8 March 2022:** each suspicious Open is present in the accepted input, but none of these three instruments is traded by any OLC109 path. There are zero event-day holdings/fills and zero selected-Close-history joins in the checked paths. Their Open anomalies therefore do not supply a new OLC109 fill or mark. See `PRIORITY_OPEN_EVENT_CHECKS.csv`.

## Selected feature history

The conservative selected-instrument 253-session lineage has 1190 rows covering 4 material frozen events. None coincides with the checked selected momentum endpoints at horizons 0, 21, 63, 126, or 252. A historical observation can nevertheless enter correlation, volatility, or moving-average windows; endpoint absence is not a general proof of no influence.

| Source event | History rows | First selected signal | Last selected signal | Direct event use paths |
|---|---:|---|---|---:|
| IS0D.DE 2020-03-09 | 20 | 2021-02-26 | 2021-02-26 | 0 |
| UBUD.DE 2020-03-18 | 190 | 2020-04-30 | 2020-08-31 | 0 |
| XBAK.DE 2023-09-28 | 15 | 2023-09-29 | 2024-08-30 | 0 |
| VOOL.DE 2020-03-12 | 965 | 2020-03-31 | 2021-01-29 | 110 |

UBUD is the additional selected-history case requiring a distinction between Open and Close: its accepted 18 March 2020 Close is +7.1569% with an essentially unchanged factor, while the flagged intraday Open/reversal is not a Close-based feature input and was never traded or held on the event date. XBAK similarly has an unusual +25.7426% Open while its accepted Close is -0.6828%; it has zero direct event use. IS0D's -27.0508% March 2020 Close is a pre-existing large market-move context and appears only in later selected history. Exact source quotes are not independently certified by these lineage checks. The per-event decisions and all joins are preserved in `MATERIAL_SELECTED_HISTORY_REVIEW.csv` and `SELECTED_FEATURE_HISTORY_MATERIAL_FLAGS.csv`.

This source audit does not replay every non-selected cluster member and competing rank. It therefore supports the bounded finding of no obvious new source-derived fake win in the recorded accounts; it does not claim exhaustive historical signal-source certification.

## Remaining conventions and reproducibility

The current-catalogue universe retains survivorship limitations. An accepted Open is conditioned on the completed day's positive reported volume, which was not known at the opening trade time. Historical adjustment factors are retrospective and their point-in-time availability is uncertified. Lag stresses do not remove these source conventions. The economic exposure and execution caveats above remain even though the accounting reconstruction passes.

Reproduce with:

```bash
python validation/source_execution/audit_source_execution.py --results results results_stage2 results_stage3
python validation/source_execution/finalize_audit_notes.py
```

Frozen ETF panel SHA256: `14b4ee4a5834e93407f5b7aac2c4857cf6f0b0403f38296daea2725fe4848b96`. `SOURCE_EXECUTION_AUDIT.json` records input and result hashes; `ARTIFACT_MANIFEST.json` records this audit package's hashes. Financial source, protocols, panels, result paths, orders, and instructions were not modified. No real trade, automation, external message, or remote mutation occurred.
