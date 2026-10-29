# ETF Trader EU165 — persistence, calendar-phase and OOS loss-risk recalibration

**29 Oct 2026, research-only; no V2/V3/B0/USA149 production modifications.** Follows original archived self-financing EU165 500×24 V3 Top3 / specialist allocator V1 pilot.

## Most important evidence: apparent frequency win is phase dependent

2021-Feb–2024-Dec, original annual fitted V3 Corrected Pair127 scores held constant, 10bps per traded side:
- V3 Top3 monthly: **CAGR +8.174%, MaxDD −25.775%, turnover 14.810×/year.**
- Every 2 months, phase A: **+9.587%, −22.964%, 8.552×**.
- Every 2 months, phase B (shift 1 month): **+5.705%, −32.747%, 7.538×**.
- Equal mix of phase A/B: **+7.698%, −27.120%**.
- Keep until basket rank beyond 5: **+9.377%, −25.486%, 11.793×**.
- Keep until rank beyond 8: **+7.381%, −26.613%, 8.104×**.
- Quarterly phase A: **+4.804%, −26.749%, 4.892×**.
The selected bimonthly phase A only beats monthly by +1.35 pp annual log return with month-block (6-month) 95% **[−4.63,+7.70]pp**, and 21/46 months better. Buffer5 +1.15 pp [−0.91,+3.28]. **Neither is a validated improvement**; calendar phase is critical.

## Prequential risk calibration

Original classifier P(ETF Open-to-Open loss >5%) overstated 2023–24 risk:
- horizon 21: event 5.8055% vs raw prediction 13.7567%; Brier raw .061696; sequential Platt .058609; historical-only base event frequency .059256.
- horizon 42: event 8.9695% vs predicted 18.7976%; Brier raw .097294, Platt .089531, base .089126.
- horizon 63: event 8.6035% vs predicted 19.7579%; Brier raw .100424, Platt .093121, base .094025.

Calibration model trained from **only preceding genuinely OOS predictions with already matured forward labels**, each signal date. 2023–24 evaluable 24 months, 3445 ETF-months at 21/42 and 3301 at 63. However Platt loss AUC ~.617/.357/.416 for horizons 21/42/63, so predictive discrimination is **inadequate beyond 21** even if Brier improves.

Using unchanged original 2021–24 self-financing V1 V3 risk veto at P21≤20% and P42≤25%:
- V3 Top3 w/o veto **CAGR 8.174%, DD −25.775%**.
- with original loss estimates **6.181%, DD −25.284%**.
- with strict past-only Platt calibration from 2023 **8.838%, DD −27.436%**.
- with simple past-only loss-frequency-only probabilities from 2023 **7.182%, DD −27.436%**.
- Specialist HOLD/SWITCH risk original **7.222%, DD −29.182%**; Platt **8.349%**, base-frequency **8.349%**, identical; risk-score advantage is not proven in that layer.
- Platt V3 veto vs original V3 veto **+2.57 pp/year** difference in mean monthly log returns; month block 95% [−2.73,+8.36]. Platt V3 veto vs V3 no veto +0.52pp/year [−2.05,+3.91]. **No statistically robust return improvement**.
- Score-gap diagnostics: V3 score improvement vs future actual next 21/42/63 day rotation delta, 45 months 2018? actual 2021–24, month-level Spearman +.200/+ .245/+.206. 21-day top-third vs bottom-third basket gap +.361pp, block CI [−.026,+.776]. Neither confirms score gap as trade threshold.

## Audit and limitations

- New source-native V3 monthly benchmark exactly equals the **immutable original V1 ZIP's** daily NAV across all 1429 original market days: maximum difference **0**. A local, nonfrozen daily NAV copy was inconsistent despite the same ledger; it was **not** used as ground truth. Input V3 trade ledger identical.
- Calibrated overlays preserve exact V1 V3 benchmark and preserve veto-path NAV through 2022 (calibration begins 2023).
- Portfolio replay is full, endogenous self-financing shares, genuine raw next Open, cost of 0.1% on buys + sells, no fake fill on missing Open. Valuation may ffill missing Close. True total-return/dividends, executable spreads and history of delisted European ETFs NOT verified.
- 500 portfolios share many instruments: bootstrap time unit = month, not basket. Historical 2018–26 has been reused extensively, 2026-survivor ETF universe, no pristine holdout. These many variants also introduce multiple-testing risk. Do not deploy/promote or declare statistically proven alpha.

**Complete research archive:** `ETF_TRADER_EU165_SPECIALISTI_V2_CALIBRAZIONE_20261029.zip`, SHA256 **eade510cfa9a828d10e2cb895e7c616546446052a4bdb10e5e4cadb4df8a9bb7**, 52,214,403 bytes / 47 entries. Includes entire original source-data V1 frozen ZIP, all analysis/overlay replay Python scripts, fully audited daily NAV and trade ledgers, 3 OOS risk models and comparisons, monthly/block CI, rank-gap counterfactuals and Italian report. ZIP testzip CRC passed.

Next gate: no portfolio policy change; improve ability to predict **relative future uplift conditional on endogenous holdings** with real historical sector/fund risk context, and obtain truly new future observations for final selection.
