# ETF Trader V3 Corrected — L10.E3 conditional postrank pair veto, functional + fee-aware economics

**22 October 2026: COMPLETED, RESEARCH ONLY, NOT PROMOTED.** This is the user's intended architecture: freeze the original CORRECTED Pairwise127 ML ranking; assess an already-selected questionable trajectory **against its specific next-ranked ML replacement**; approve only an exceptional substitution, keep all other positions and Top3 slot weights fixed. No new global ranker. Do NOT interpret a positive rare-action outcome as proof of deployable aggregate alpha.

## Provenance and strict protocol

- [Protocol and pre-outcome engineering amendment](./20261022_L10E3_PAIRWISE_VETO_PREREG.md); [predictive source](../../experiments/l10_postrank_trajectory/evaluate_e3.py); [fee-aware next-open replay](../../experiments/l10_postrank_trajectory/economic_e3.py).
- Frozen OHLCV [run 39482809691](https://github.com/AM1975MA/Test/actions/runs/39482809691) and frozen CORRECTED OOS scores [run 39700865721](https://github.com/AM1975MA/Test/actions/runs/39700865721); 149 original ETFs, 500 canonical overlapping 24-ETF baskets, SHA256 `36a45916b5d8191f3ccd206f39bf3fd3f1ed4bcaffd474e352b69c598f2b6a5e`.
- Initial software-only [run 39752728805](https://github.com/AM1975MA/Test/actions/runs/39752728805) stopped before fit/results because an unnecessary assertion demanded >=100 months with E1 candidate pairs. Months with no warnings should **abstain**. Corrected before examining any E3 result, rule/model unchanged. Successful evaluation [run 39752940429](https://github.com/AM1975MA/Test/actions/runs/39752940429), artifact **12414128295**; original E1 and BASE exact metric parity passed, all 101 mature months included. Archive success [39753447149](https://github.com/AM1975MA/Test/actions/runs/39753447149).
- No position or allocation changes except where an already selected original ML top3 incumbent has the frozen E1 flag (negative 21D momentum AND >=10% fall from 63D high). Next unflagged candidate is the next available CORRECTED original rank4+ ticker. A standardized logistic classifier (L2 C=0.25, yearly expanding refit, minimum 18 signal months and 150 independent unique candidate pairs, 7 fixed relative trajectory/ML rank-gap features) permits the substitution ONLY if **P(challenger next21D beats incumbent by >=1pp) >=0.70**. No class reweighting or threshold search.
- Fit-year strict original daily-market maturity: candidate next-open+21 trading-session exit must be strictly before Jan1 fit cutoff; no data from current year labels in fitted model. 2018–19 abstain due to inadequate prior archived OOS vintages, yearly train fit 2020 onward. Total deduplicated possible pair observations **18,218**, all pair/date duplicates across baskets counted once for training; equal calendar-month total training sample weight; no data leak via future outcomes as features.
- Source-only prefix invariance check PASSED and original E1 and BASE reference OOS metrics reproduced; all 101 forward21D labels matured. Prediction sample is 2018–2026 and repeatedly researched; bootstrap is not independent new-vintage confirmation.

## E3 matched 21-trading-day functional skill (all 101 mature months)

| ETF basket Top3 50/30/20 metric | Unmodified CORRECTED | Aggressive E1 | E3 pair-specific veto |
|---|---:|---:|---:|
| Basket's realized best ETF in selected Top3 | **35.4713%** | 29.2713% | 35.3327% |
| Capital on actual basket-best ETF | **12.5818%** | 10.1826% | 12.5202% |
| Capital in ETFs with next21D realized loss >=10% | 8.4861% | **6.7834%** | 8.4026% |
| Weighted future percentile rank | 0.524852 | 0.516791 | **0.524932** |
| Weighted next21D forward return | 1.35596% | 1.29642% | **1.36979%** |
| Weighted oracle regret21 | 0.105470 | 0.106066 | 0.105332 |

E3 changed **1.8634% of baskets** on average: **965 basket/slot replacement events** across 50,500 basket-months, much less than E1's 45,684. Most ML choices remain intact.

Paired six-month-block bootstrap of 101 calendar-month cross-basket averages, 6000 draws:

| E3 − BASE metric | Delta | Descriptive CI 95% |
|---|---:|---:|
| Basket's best ETF selected Top3 | −0.1386 percentage points | [−0.3565,+0.0238] pp |
| Capital assigned to best ETF | −0.0616 pp | [−0.1578,+0.0071] pp |
| Capital exposed to severe loss | −0.0836 pp | [−0.3010,+0.1469] pp |
| Weighted future rank | +0.000079 | [−0.001966,+0.001858] |
| Mean forward21D return | +0.0138 pp | [−0.0262,+0.0563] pp |
| Bottom-three future ETF exposure | −0.1592 pp | [−0.4515,+0.0965] pp |

No interval establishes a robust E3 benefit over frozen original ML. Improvement over rejected aggressive E1 alone is not an investment justification.

### Conditional action concentration / calibration

Of **18,218** unique distinct candidate pairs over 101 months, 14,961 had a valid annual trained model from 2020 onward. Among all predicted pairs the challenger truly beat the incumbent by >=1pp in **43.83%**, with mean 21D relative return **−0.14%**. Among the **363 DISTINCT pairs** crossing the fixed 0.70 threshold, relative return averaged **+2.828%**, and the >=1pp classification succeeded **60.61%**; this produced 965 basket-slot changes because basket composition overlaps. These are conditional post-fit-year outcomes, not 363 independent market events and **not a 2.83% portfolio return**.

**Critical calibration issue:** average predicted success probability for the 363 acted-upon unique pairs was **74.96%**, but observed >=1pp success rate was **60.61%**. The model appears **overconfident on the acted-upon subset**. The small high-probability group may contain useful conditional information but should not be used as a production probability. Action intensity is regime-dependent: around 9.12% of 2021 baskets changed, while 2026 mature months had zero changes. Repeated-exploration bias prevents confirmation.

## Fee-aware portfolio replay — same original L07 next-open executor, 10bps one way

Given the encouraging conditional pair-advantage but neutral portfolio endpoints, the user's requested CAGR check was performed WITHOUT retuning any model/threshold/action. Successful [economic run 39753426512](https://github.com/AM1975MA/Test/actions/runs/39753426512), artifact **12413574353**, permanently archived by successful [39753612579](https://github.com/AM1975MA/Test/actions/runs/39753612579). Original [source-only L07 execution](../../experiments/l07_integrated/evaluate.py) and [V3 source-only statistics](../../src/etf_trader_v3/source_only/statistics.py). Weighted original CORRECTED Top3 allocations [50%,30%,20%] or same slots after only the 965 archived E3 adjustments. Per dollar traded, one-way fee 0.001. Both arms have EXACT SAME dates, OHLCV, tickers, rebalance schedule, fill semantics, basket inputs and policy. Results shown below use **aggregate NAV of 500 baskets**, NOT the arithmetic average of 500 individual CAGRs.

| Common replay calendar | Frozen CORRECTED aggregate CAGR | E3 aggregate CAGR | E3 minus BASE |
|---|---:|---:|---:|
| 2018-02-01 to 2026-06-01 | **15.6504%** | 15.6132% | **−0.0372 pp** |
| 2022-02-01 to 2026-06-01 | **21.4346%** | 20.9823% | **−0.4523 pp** |

Annualized paired **daily log alpha** of E3−BASE after 10bp fees:
- Long 2018–26: +0.000881 (about +0.0881 pp per year log-alpha), 21-trading-day calendar block CI95 **[−0.004120,+0.006022]** across 2,092 common observed dates. Note that this paired mean log-alpha measure is NOT the same as the difference of aggregate NAV CAGRs above; do not conflate them.
- 2022–26: **−0.003077** (−0.3077 pp per year log-alpha), 21-day block CI95 **[−0.010712,+0.003780]** across 1,085 common observed dates.

Aggregate maximum drawdown:
- 2018–26: BASE **−38.4188%**, E3 **−38.4629%** (marginally worse).
- 2022–26: BASE **−19.4571%**, E3 **−19.4260%** (marginally less severe).

**Important window restriction:** the last independently 21D matured signal in E3 is **29 May 2026**. Hence the common execution ends **1 June 2026** rather than the L08 window ending 1 July. The June30 signal was not backfilled with a hindsight or synthetic E3 choice. These are fair **new matched windows** but not interchangeable with L08 full 2018–July 2026 metrics. The E3 absolute aggregate CAGR cannot be used to claim comparison versus fully integrated V2 Golden.

The occasional positive relative pair returns were NOT sufficiently frequent/stable to raise portfolio aggregate CAGR after accounting for the relevant positions, dates, original portfolio opportunity cost, rebalancing and fees. Average basket-level long-window CAGR showed small differences of the opposite sign, a further reminder to report **which aggregate** is being measured.

## Decision and next isolated research

**DO NOT PROMOTE L10.E3.** The direct ML-incumbent-versus-challenger formulation is closer to the desired mechanism and can identify promising exceptions, but the 70% cutoff is not empirically calibrated in the selected set. Aggregate CAGR (both common vintages) fails to improve; no significant paired 21D risk or rank uplift, and 2022–26 CAGR worsens. No production V2, frozen V3 ranker or historical code was overwritten. All negative and partial discoveries remain in central registry.

Potential E4 is a **research plan only**: calibrate the *conditional substitution decision* with strictly past-matured chronological data and distinct risk vs rebound confidence, explicitly imposing high cost for vetoing actual future basket winners. Predeclare all changes before new test, evaluate on new never-inspected chronological vintage for confirmation (already-researched 2018–26 is not a fresh holdout), avoid cutoff sweeps on E3 result. Retain original ML ranking as the immutable first stage; mathematically inspect selected trajectories only.

## Immutable repositories/artifacts

- [Frozen E3 protocol](./20261022_L10E3_PAIRWISE_VETO_PREREG.md)
- [All original E3 fit audits, individual pair probabilities, monthly/yearly metrics, 965 substitutions, bootstrap, manifest](./data_run_39752940429/)
- [Common-window next-open 10bp NAV daily, CAGR scores, calendar annual returns and paired uncertainty](./economics_run_39753426512/)
- Code: [maturity-safe predictor](../../experiments/l10_postrank_trajectory/evaluate_e3.py), [independent same-policy economic replay](../../experiments/l10_postrank_trajectory/economic_e3.py)
