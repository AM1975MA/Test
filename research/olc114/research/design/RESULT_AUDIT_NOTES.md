# OLC114 independent results audit

The auditor reads the completed, frozen experiment. It fits no model and generates no alternative financial policy path. It reconstructs account quantities and cash from recorded orders, then independently checks each immutable instruction's fixed sizing arithmetic, execution eligibility, queue maturity, costs and final target. This includes the one-session execution delay and targeted masks that preserve unaffected quantities.

## Economic result

TREE_CYCLE is the primary model fixed before this experiment. The primary next-Close account earns **23.4913% full-period CAGR**, against **22.5708% BASE**; full-period sampled MaxDD is **−36.1036%**, against **−36.5142%**. The older OLC113 PRICE_RESET earns **24.1622%** on the same full window, with nearly BASE's drawdown.

The common period begins on **2022-07-04**, following the activation signal on **2022-07-01**, index865. Each account uses its own immediately preceding actual Close NAV. For normal-cost BASE and TREE that anchor is **EUR17,631.835384592854**. TREE's common-period CAGR is **21.4034%**, versus BASE **20.0121%**, and sampled MaxDD improves to **−27.2365%**, versus **−36.5142%**: a **9.2777 percentage point** reduction in drawdown depth. The full-window maximum includes the earlier baseline warmup and cannot be presented as a failure to improve the later active-period drawdown.

The primary model therefore produces a meaningful historical protection improvement during its available period, but it **fails the predeclared +3 percentage point CAGR/no-worse-MaxDD criterion in both windows** and does not reach30% CAGR. Its CAGR advantage against the corresponding BASE retains its positive sign with doubled costs and delayed Close execution. This does not mean the strategy is insensitive to delay: both strategy and baseline absolute returns fall materially in the delayed scenario.

The mean-value control has zero discretionary plans and exactly reproduces all daily fields and the complete BASE order ledger in all three scenarios. RIDGE's50primary plans reduce exposure and lower active-period drawdown, but also lower CAGR. TREE starts10primary plans: seven PARK and three REDEPLOY. The modest number of independent completed42-session outcomes remains a material limitation.

## Predictive result is separate

TREE's date-balanced prequential MSE is worse than MEAN for both PARK and REDEPLOY. PARK's positive-buffer forecasts have positive average realized advantages, but cover only four nonoverlapping42-session intervals. REDEPLOY's positive-buffer forecasts cover11distinct dates and three nonoverlapping intervals; their date-balanced mean realized advantage is **−0.002380916494377255 log units**. The account result is therefore not evidence of a reliable emerging-opportunity reentry predictor. Overlapping plan advantages and hindsight-best labels are not additive CAGR.

## Actual-state support

All actual eligible states, feature vectors and saved-model predictions are independently reconstructed. The primary TREE log contains a maximum standardized value near **1.732×10^14**. It comes from candidate-availability feature index8: the training feature is identically1, its weighted mean is numerically just below1, and the recorded scale is about5.77×10^−15. On five dates the actual feature is0. This is an unseen state in a previously constant binary feature, accompanied by an ill-conditioned diagnostic scale; it is not a market observation an astronomical number of standard deviations away.

The frozen tree consumes raw features, and that constant feature is not a split in the relevant saved model. The flagged examples fail the positive decision buffer. Without constant training dimensions, the maximum primary TREE standardized feature magnitude is **11.0185**, so ordinary state-distribution shift still exists and should not be dismissed. The auditor records both the original diagnostic and the separate nonconstant-feature maximum. No model, scaler, frozen prediction or financial path was altered.

## Mechanical verification

The final audit covers all15paths, their complete calendars and receipts, the four original BASE/STATIC_75 normal/double-cost controls, and all three MEAN/BASE exact replications. It verifies training admission strictly before monthly cutoffs, the504date/24month/12nonoverlapping-interval readiness conditions, per-date leg weights, paired32×63-session bootstrap draws, saved portable model identities, and causal prequential predictions. Bank event hashes and NPZ rows reconcile; every supported BASE endpoint is checked against the old full-account reference.

The order audit checks accepted-source marks, five-calendar-day support, fees, quantities, affordability, immutable targets, masks, unaffected holdings, pending-order supersession and delayed maturity. The policy audit checks full targeted sale requests, strictly later first eligible weekly candidate attempts, actual cash/NAV purchase budgets, at most one active plan and monthly handoff priority. It rejects every nonscheduled instruction not attributed to a plan's sale or entry.

A filled sale on the terminal Close has no subsequent callback and may legitimately retain a `sale_complete_idx=None` summary. Likewise, handoff ends discretionary control at the monthly signal; native pending fills can still occur before the newer instruction matures. The independent plan table preserves actual order dates alongside the executor summaries.

The separate reviewer found and helped close target/quantity and unattributed-instruction false-pass risks in the initial auditor. Synthetic failing examples were observed before the fixes. **13targeted audit tests pass**. These were audit-boundary defects; frozen account results were not changed. The independent review appendix records the reviewed source identities.

## Reproduce and artifacts

From the workspace root:

```bash
python -m unittest discover -s olc114/tests -p test_cycle_audit.py -v
python -u olc114/src/analyze_cycles.py
```

`results/INDEPENDENT_DIAGNOSTICS.json` contains numerical checks and per-path details. The corresponding score, criterion, comparison, annual, plan, execution-attempt and forecast tables preserve every model and scenario. Two Italian figures show the full and common periods with each series normalized to its own actual window anchor. Both figures were visually inspected for legibility. Source and output manifests seal stable inputs and outputs; mutable run logs are excluded from the output manifest.

The historical sample has already informed several adaptive experiments. It is not a pristine holdout. Current-catalog survivorship, adjusted-price vintage, execution/capacity assumptions, reference-policy training states and unmodeled taxes remain limitations.
