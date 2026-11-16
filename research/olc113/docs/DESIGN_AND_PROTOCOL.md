# OLC113 — Monthly reentry deadline: continuation-contract ablation

**16 November 2026. Adaptive research after OLC111 and OLC112. Protocol written before any OLC113 financial result.**

## Intent and authorization

The user seeks a material joint improvement in CAGR and drawdown, with approximately 30% CAGR as an aspiration, and has explicitly authorized autonomous research and saving to AM1975MA/Test. This study changes no trading or production workflow. Prior studies and OLC100 remain frozen.

## Evidence and approaches considered

The native label generator `olc111/src/research_pipeline.py::counterfactual_values` applies one intervention, then applies the baseline target at future scheduled monthly signals within the 21-session outcome window. The ENTRY comparator therefore waits in cash until that baseline continuation; it is not indefinite cash. OLC112 preserves monthly rotation only for invested accounts. Its cash accounts can ignore the monthly baseline indefinitely, producing 194- and 215-session cash spells. This is a specific continuation mismatch. It was not caused by missing model readiness or universally unavailable candidates.

Three approaches were considered:

1. **Restore the scheduled continuation for cash accounts.** Reuse every saved forecast model, feature, buffer and candidate, changing only the monthly default. This is the selected immediate experiment because it isolates the documented mismatch.
2. **Learn complete bounded protection/reentry cycles on actual policy states.** Potentially addresses repeated-action and state-distribution mismatch, but requires new labels and models. Deferred until this mechanism control is measured; it adds no demonstrated information by itself.
3. **Per-ETF stops, faster rebounds and fresh replacements.** These mechanisms already exist in OLC110 and underperformed its static exposure control. Repeating them without a distinct new hypothesis is rejected here.

Monthly reentry itself is not novel. OLC110 tested it with technical stops. OLC113 tests the missing scheduled continuation in the current learned-action architecture. This change does not make the entire repeated policy identical to its one-intervention label bank: that limitation remains explicit, as do state-distribution changes and the finite 21-session horizon (some calendar months exceed 21 sessions).

## Exact policy

Use OLC112's initial/warmup rules and OLC111's unchanged CASH/FRESH/ENTRY predictions. At a scheduled monthly close, after all three heads are ready, if there are no pending/queued orders, issue the original baseline selector target for **every account, including fully cash accounts**. Use the normal 3% rebalance band (`force=False`). A cash account consequently receives a scheduled reentry instruction even when ENTRY predicts a negative advantage. Actual execution remains the next accepted bar and is not assumed to occur on the signal day.

Initial orders, incomplete readiness, pending/queued orders, missing quotes, and nonscheduled decisions are delegated unchanged to the existing policy. At nonscheduled closes, cash may enter early on the unchanged positive ENTRY buffer; invested accounts retain CASH/FRESH/HOLD. Scheduled reentry cannot be vetoed by an ENTRY forecast. A new exit cannot be issued on the same scheduled close.

There is no new cooldown, maximum-day threshold, forecast model, fitting, new data, new candidate selector, transaction-cost assumption, volatility threshold, or parameter search.

## Frozen comparison matrix

Four new accounts: `MEAN_RESET`, `PRICE_RESET`, `VIX_RESET`, `TERM_RESET`. Map them to the same underlying OLC111 arm. `PRICE_RESET` remains the primary learned arm; VIX and TERM are secondary. Do not substitute a successful secondary outcome for the primary result.

Three original scenarios are retained: NEXT_CLOSE (1 EUR + 15 bp per executed order), DOUBLE_COST (2 EUR + 30 bp, next Close), NEXT_OPEN (1 EUR + 15 bp). Total: **12 new paths**, no fitting. Reuse OLC111 BASE/STATIC_75 and OLC112's matching ROTATION paths as unchanged controls. The Open scenario retains the known completed-daily-volume availability limitation and is only a sensitivity.

Initial capital is 10,000 EUR, fractional economic units, no account borrowing/shorting, cash return zero, taxes excluded. Data and candidate remain the frozen 2,096-ISIN EUR current-catalog panel and DEDUP_DUAL_TREND_OPP. Historical eligibility/liquidity filters do not remove survivorship or adjusted-price-vintage concerns.

Full period: 2020-03-02 through 2026-10-30. Common learned period: first executable day after all-head readiness, 2022-07-04, using each path's actual 2022-07-01 Close NAV. Preserve both periods; do not credit warmup returns to the learned policy.

## Pre-result judgments

- **Mechanical repair:** every idle scheduled cash account receives the baseline target. The realized cash spell may extend because of unavailable quotes or a pending instruction, which must be reported. No claim of a universal 21-session holding limit.
- **Baseline parity:** MEAN_RESET with no discretionary interventions must exactly reproduce same-scenario BASE daily fields and order ledger.
- **Economic comparison:** report every arm and scenario against BASE, STATIC_75 and its OLC112 predecessor. Evaluate CAGR and sampled MaxDD together, cash spells, exposure, turnover, fees, annual returns, drawdown episodes, and filled intervention counts.
- **Material improvement criterion:** at least +3 percentage points of CAGR versus BASE with no worse sampled MaxDD, on both the full and common learned periods, in primary next-Close execution. Report whether any candidate meets it and whether the primary arm meets it. The original 30% CAGR aspiration is a separate explicit column.
- **Stress consistency:** gains that reverse with doubled costs are not robust. Open sensitivity cannot establish executability. The number of completed separated intervention episodes remains diagnostic; sparse episodes bar an assertion of reliable timing skill.
- **Information attribution:** this ablation cannot overturn OLC111's failed incremental TERM forecast comparison. Gains from scheduled baseline reentry must not be called new predictive alpha.

No threshold search or post-result primary-arm change follows this run. Any subsequent cycle-model study needs a separately written protocol disclosing these observed results. There is no pristine holdout in this repeatedly studied history.

## Reproducibility and audit

Freeze this protocol, new runner, all transitive old financial code/inputs through the OLC111/112 freezes, all 81 saved fit files, readiness, and reused controls before the first OLC113 financial run. Refuse to fit a missing model. Save all daily accounts, orders, instructions, decisions, policy traces and metrics. Independently reconstruct units, cash, fees and NAV from accepted source marks, check no held quote exceeds five calendar days, verify full/common metrics, all calendars, warmup parity and the exact MEAN control. Save the full study on a new research-only branch derived from the archived OLC111/112 commit.
