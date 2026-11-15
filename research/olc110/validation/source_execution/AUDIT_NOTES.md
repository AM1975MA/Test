# OLC110 — Independent source and execution audit

**Result: PASS_BOUNDED_KNOWN_EVENT_AND_EXECUTION_LIMITS_RETAINED.** All **78 frozen paths**, **32,533 recorded orders**, and **235 traded ISINs** were examined. There are **81 newly traded ISINs** versus the complete OLC109 set. No wrong accepted-quote fill, accepted-panel/raw-price mismatch, liquidity-source mismatch, or new obvious quote corruption was found in this bounded review. The 2026 Brazil-fund event is newly used relative to OLC109, but its earlier primary-source adjudication is retained. Execution capacity remains materially uncertain.

## Frozen scope and independent reconstruction

The protocol SHA256 is `aca685d1d228f857c48fd1a4aafc45170a847765e84352c932943c541d119740`. The audit requires the completed 13 × 6 matrix and checks its input/code hashes against the pre-result freeze. It imports neither strategy nor engine, creates no strategy account, and changes no prices, quarantine, protocol, order, decision, or financial result. Quantities and cash are accumulated solely from recorded orders using round-trip CSV parsing. This source-usage reconstruction supplements the separate full financial/state audit.

Maximum unit discrepancy is **0**, cash discrepancy **EUR1.5e-10**, pretrade-mark NAV discrepancy **EUR1.51e-10**, and Close NAV discrepancy **EUR1.51e-10**. Numeric dust never exceeds EUR6.68e-12. There are 0 invalid-fill findings, 0 accepted-price/source discrepancies, and 0 turnover discrepancies. Both quarantine files are byte-identical to OLC109; all five quarantined series remain absent.

Economic holding Close age and execution-fallback Close age both peak at **5 calendar days**. There are **0 held asset/path sessions** and **0 fallback asset/path sessions** older than five days. The 1e-10 quantity threshold is used only to describe economic holdings/staleness; all signed numerical residuals remain in reconstruction.

## NEXT_CLOSE is a separate execution convention

The 65 original-scenario paths execute against accepted Open and the independent Open mask. The 13 NEXT_CLOSE paths execute against accepted Close and the Close-observation mask. For NEXT_CLOSE, the field named `nav_open` is the Close valuation before fees, not an opening quote. Its reported drawdown samples Close pre/post fees and does not measure intraday loss. The audit records `execution_quote`, Open fills, Close fills, Open-source use, Close-source use, and fallback marks separately. NEXT_CLOSE trades are never labelled as Open executions. Full-day turnover is only a descriptive denominator in both modes; neither opening nor closing auction capacity is observed.

## Participation and capacity

Participation = recorded EUR notional / (raw EUR Close × the venue's reported full-day volume). There are no missing/nonpositive denominators and no invalid-geometry raw Close denominators among recorded orders. This ratio does not observe spread, order-book depth, auction volume, market-maker inventory, creations/redemptions, or trading on other venues. The six scenarios repeat related opportunities; pooled counts are not independent observations.

| Scenario | Quote | Paths | Orders | ≥10% of daily turnover | ≥100% | Maximum ratio |
|---|---|---:|---:|---:|---:|---:|
| BASE | OPEN | 13 | 5,572 | 238 | 12 | 4.2839× |
| DOUBLE_COST | OPEN | 13 | 5,572 | 191 | 10 | 3.4966× |
| LAG1 | OPEN | 13 | 5,275 | 250 | 8 | 4.5706× |
| LAG2 | OPEN | 13 | 4,988 | 204 | 7 | 6.4072× |
| NEXT_CLOSE | CLOSE | 13 | 5,559 | 197 | 10 | 3.6491× |
| ZERO_COST | OPEN | 13 | 5,567 | 284 | 18 | 5.2295× |

Across the matrix, **1,364 orders are ≥10%** and **65 are ≥100%** of full-day venue turnover. The largest is **6.4072×**: `REFRESH_WEEKLY__LAG2`, SELL SC0W.DE on 2021-12-29, notional **EUR6,836.48**, volume **2**, full-day turnover **EUR1,067.00**.

All thirteen BASE accounts:

| Arm | Orders | ≥10% | ≥100% | Maximum ratio |
|---|---:|---:|---:|---:|
| BASE | 226 | 13 | 0 | 0.4864× |
| STATIC_75 | 224 | 8 | 0 | 0.3240× |
| EXIT63_STAGED | 320 | 18 | 0 | 0.9304× |
| EXIT21_MONTHLY | 239 | 10 | 0 | 0.5243× |
| TRAIL15_STAGED | 343 | 14 | 0 | 0.4930× |
| STATIC_HALF | 220 | 3 | 0 | 0.1890× |
| EXIT21_STAGED_FRESHD | 757 | 36 | 5 | 4.2839× |
| VOLTRAIL_STAGED | 354 | 9 | 0 | 0.4857× |
| REFRESH_WEEKLY | 701 | 39 | 2 | 2.6131× |
| EXIT21_STAGED_FRESHW | 674 | 29 | 1 | 3.3002× |
| EXIT21_STAGED | 541 | 19 | 1 | 2.9377× |
| EXIT21_SLOW | 449 | 17 | 1 | 2.9500× |
| EXIT21_FAST | 524 | 23 | 2 | 2.7301× |

The predeclared primary is **EXIT21_STAGED_FRESHW**; the observed highest BASE CAGR is **BASE**, and the highest dynamic-protection BASE CAGR is **EXIT63_STAGED**. This is a description after the fixed matrix, not an added strategy-selection test. Their full six-scenario capacity records, including FRESHD, are in `PRIMARY_AND_OBSERVED_BEST_CAPACITY.csv`. All arm/scenario counts are in `ALL_78_PATH_CAPACITY_SUMMARY.csv` and six-scenario totals for every cash/control model in `ALL_ARMS_PARTICIPATION_SUMMARY.csv`.

The primary FRESHW BASE has one order at 3.3002× full-day turnover. FRESHD BASE has five orders above 100%, with maximum 4.2839×. EXIT63_STAGED BASE has no order above 100% but a maximum of 93.04%; its LAG1 maximum reaches 3.1345×. The existing EUR100,000 median-turnover eligibility condition does not guarantee sufficient volume on a later exit or delayed fill day. Fixed transaction costs cannot establish that the reported price was attainable for these quantities.

## Actual use of reviewed source events

The bounded scan covers **238 histories**, comprising recorded traded/selected/monitored identities and three priority Open cases. The catalogue retains **411 event rows**, including **53 material review-trigger rows**. There are **177 source-event/path uses across 9 distinct source dates**. A discarded raw row is not counted as used just because its instrument was held that day: the audit traces accepted quote provenance, including carried Close and fallback marks.

### Known VIX futures event: 12 March 2020

VOOL is held by all 78 accounts on this date, with zero event-day fills. Its accepted Close rises 29.2082% with unchanged factor and positive volume. The event was already used in V3 and OLC109. Its source history enters the current strategy/monitoring lineage, but the audit identifies no new corruption finding or independently certified exchange execution price.

### Newly used Brazil event: 26 October 2026

LBRA is newly used relative to OLC109 in 12 paths: nine Open-scenario paths and three NEXT_CLOSE paths. Six Open-scenario FRESH accounts retain the adverse held-fund move; the two NEXT_CLOSE FRESH accounts also retain their loss. Three REFRESH_WEEKLY Open accounts buy at EUR22.84 and receive the recorded intraday rebound; the NEXT_CLOSE weekly account buys at EUR24.48500061035156 and receives no same-day price PnL. These are four buys in total, comprising three Open and one Close fills.

The archived issuer NAV moves from EUR30.5324 to EUR24.8836, a loss of 18.5010%, corroborating a large economic decline. The source Close falls 19.6950%, the Open 25.0902%, with unchanged adjustment factor and reported volume 169,561. Both primary NAV archive hashes match the previous independent review. Exact Open EUR22.84, spread, and auction depth remain uncertified; issuer NAV is not substituted for a venue quote. The BASE primary FRESHW loses EUR1,709.67 before costs on this source date; FRESHD BASE loses EUR2,049.21. REFRESH_WEEKLY BASE records EUR566.41 of intraday gain before costs. All of these outcomes remain unchanged. See `MATERIAL_EVENT_ACCOUNT_IMPACT.csv` and `MATERIAL_EVENT_ADJUDICATION.csv`.

### New ordinary dividend context

Five dates are newly used descriptive factor/dividend context. All reconcile with the provider dividend arithmetic; the maximum absolute log residual is **6.9e-07**. This checks arithmetic consistency, not issuer ex-dates, currency treatment, or historical adjustment-factor availability.

| Symbol | Date | Paths | Open fills | Close fills | Factor multiplier |
|---|---|---:|---:|---:|---:|
| EXXW.DE | 2022-12-15 | 4 | 0 | 0 | 1.03297614 |
| SMLD.DE | 2026-03-12 | 4 | 3 | 1 | 1.02169368 |
| EHDL.DE | 2021-09-16 | 4 | 0 | 0 | 1.03082362 |
| IBC9.DE | 2023-09-14 | 7 | 0 | 0 | 1.02805487 |
| EXH5.DE | 2026-07-15 | 4 | 0 | 0 | 1.03015066 |

The earlier source review's distinction between arithmetic consistency and correct ex-date remains essential; no new primary dividend-date certification is claimed. See `NEW_CONTEXT_EVENT_RECONCILIATION.csv`.

## Selected and daily-monitored source history

There are **7,820 potential material Close-source lineage rows**: 7,812 for VOOL and eight for LBRA. The audit includes raw targets, selected monthly identities, slot asset/base identities, and daily monitoring even when no order is emitted. This broader coverage is not directly comparable to OLC109's monthly selected-history count. Lineage includes carried source observations at the oldest endpoint and reports endpoints at 0/1/5/10/21/63/126/252 sessions, SMA windows, volatility21, and correlation126 price windows. Membership in a window is potential influence, not proof that a particular ranking or exit changed because of that observation.

The three priority suspicious Open cases (F703 2020-03-18, IQSE 2021-02-15, UEQU 2022-03-08) remain absent from all actual trades and selected/monitored history. They have zero event-day accounting use and zero fills in either mode. Close-based feature lineage does not use an unusual Open merely because the date shares an instrument identity.

## Remaining limits

The current catalogue does not reconstruct all closed or delisted funds. Historical source-adjustment vintages are uncertified. Original accepted Opens depend on the completed day's positive volume, which is not information available at the Open. NEXT_CLOSE changes price timing but does not repair survivorship or adjustment vintage. Fractional economic units, zero cash interest, omitted taxes, and source Open/Close proxies remain research conventions. Review thresholds do not rule out smaller source errors. The audit does not replay every rejected competitor or establish source correctness across the entire historical universe. A source-accounting pass is not certification that the portfolio could trade at the quoted auction prices. The negative protection results are preserved and no additional threshold or financial arm was tested.

## Reproduction and files

```bash
python validation/source_execution/audit_source_execution.py
python validation/source_execution/finalize_audit_notes.py
```

`SOURCE_EXECUTION_AUDIT.json` records all financial-result and input hashes, including the frozen panel/turnover and source CSVs. `EVENT_ADJUDICATION.json` retains inherited judgments and primary archive checks. `FINAL_VERIFICATION.json` records the final unchanged-input checks. `ARTIFACT_MANIFEST.json` hashes the audit package, excluding active log files. No real order, automation, external message, source download, or remote mutation was performed.
