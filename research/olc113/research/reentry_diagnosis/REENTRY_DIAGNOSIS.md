# OLC111/112: why re-entry was withheld

## Finding

The long OLC112 cash spells were produced by the saved ENTRY predictions and the positive lower-bound gate. They were not caused by missing candidates, model warmup, pending instructions, unavailable features, or a failed buy. The more consequential design issue is that the ENTRY target rewards entry now **relative to automatic monthly baseline entry later**, whereas the deployed cash branch can reject entry at every monthly date and remain in cash indefinitely.

This is a diagnosis of the existing frozen experiments. It does not establish that a particular modification would improve CAGR or drawdown. No new models, financial labels, policy replays, parameter grids, or alternative strategy returns were produced. All writes are confined to `olc113/research/reentry_diagnosis/`.

## 1. Exact gate accounting

These counts refer to the primary `NEXT_CLOSE` paths. The final cash Close is also the ENTRY decision date; the order fills at the following accepted Close.

| Measure | PRICE_ROTATION | TERM_ROTATION, longest spell |
|---|---:|---:|
| CASH decision | 2025-05-28 | 2025-06-26 |
| First full-cash Close | 2025-05-29 | 2025-06-27 |
| Last full-cash Close / ENTRY decision | 2026-04-01 | 2026-04-01 |
| First subsequent invested Close | 2026-04-02 | 2026-04-02 |
| Cash sessions | 215 | 194 |
| Valid, legal candidate / valid ENTRY features | 215 / 215 | 194 / 194 |
| All three heads ready | 215 | 194 |
| Busy / unsupported decisions | 0 / 0 | 0 / 0 |
| Mean <= 0 | 178 (82.79%) | 145 (74.74%) |
| Mean > 0 but lower <= 0 | 36 (16.74%) | 48 (24.74%) |
| Mean > 0 and lower > 0 | 1 (0.47%) | 1 (0.52%) |
| Monthly dates spent in cash | 11 | 10 |
| First positive mean | 2025-06-03 | 2025-08-04 |
| Missing option source | 6 days; PRICE unaffected | 5 days; PRICE fallback used |

Thus relaxing the uncertainty buffer alone does not describe the full diagnosis: even before that gate, the mean prediction rejected most days. The positive-mean/negative-lower counts are descriptive gate classifications, **not** results from a strategy that removes the buffer.

The same PRICE_ROTATION counts occur under all three saved execution/cost scenarios. The OLC111 PRICE path has a shorter, later spell (2025-07-21 through 2026-04-01): 178 predictions, 142 means <= 0, 35 positive means blocked by the lower bound, and one ENTRY. The ENTRY formula is independent of the actual cash account's holding history, so overlapping days use the same predictions in OLC111 and OLC112.

VIX_ROTATION's longest spell is also 194 sessions with 156 means <= 0, 37 positive means blocked by the lower bound, and one ENTRY. Across the complete VIX cash history, the only three unsupported days are 2023-12-04, 2023-12-05, and 2023-12-06: the candidate still has two holdings at gross 1, but representative breadth is missing. Those three days do not explain the 2025–2026 plateau.

Sources: original `POLICY_TRACE.csv.gz`, `DAILY.csv.gz`, saved selections and CBOE arrays; reproduced in `ALL_PATH_CASH_GATE_SUMMARY.csv`, `CASH_DECISION_DETAILS.csv`, and `DIAGNOSTICS.json`.

## 2. Which numerical terms held ENTRY down?

Values below are **log-wealth basis points**: 10,000 times the native log-advantage prediction. They are not annualized returns. Contributions are exact additive terms of the saved linear prediction, averaged across the stated spell.

| Prediction / contribution | PRICE, 215 days | TERM, 194 days |
|---|---:|---:|
| Average predicted mean | -41.96 | -47.01 |
| Average lower bound | -118.37 | -129.07 |
| Average mean-minus-lower gap | 76.41 | 82.07 |
| Fresh NM63 contribution | -32.96 | -34.88 |
| Breadth contribution | -17.86 | -18.82 |
| Fresh NM21 contribution | -0.47 | -0.56 |
| Fresh log(vol21/vol63) contribution | +5.53 | +8.07 |
| Time-to-next-month contribution | -0.06 | -0.03 |
| Intercept | +3.85 | +4.25 |
| Option residual contributions combined | 0.00 | -5.04 |

The saved PRICE ENTRY head assigns a negative slope to fresh NM63 and breadth during these months. The cash spell has a strong fresh basket and broad positive momentum: PRICE's fresh NM63 averages 1.8464 and breadth averages 0.82835. NM63 contributes negatively on 188 of 215 days, and breadth on 201 of 215 days. This is a model predicting the incremental merit of accelerating entry ahead of monthly continuation; it should not be interpreted as a direct forecast that the selected basket will lose money versus remaining in cash.

The additional options terms are smaller than the common price terms in this episode. TERM's options contribution averages -5.04 log-bp, compared with -34.88 from NM63 and -18.82 from breadth. The positive entry gate therefore cannot be diagnosed solely as a VIX or term-structure data problem.

The bootstrap 10th percentile is the predeclared heuristic buffer, not a calibrated confidence interval. PRICE's best rejected lower bound is -17.89 log-bp on 2026-03-31. TERM's best rejected lower bound is -31.57 log-bp on 2025-12-02. Neither is a floating-point zero-boundary artifact.

Sources: coefficients and fixed transforms in original `olc111/results/FITS/FIT_*.json.gz`; exact per-day decomposition in `CASH_DECISION_DETAILS.csv`.

## 3. The cash HOLD used in the labels is usually not 21 days in cash

`research_pipeline.counterfactual_values` applies the chosen intervention once, then supplies frozen baseline targets at later monthly dates. Its ENTRY comparison starts from hypothetical all-cash holdings at the baseline account's NAV and compares immediate FRESH with HOLD followed by that monthly continuation. `AccountPolicy.__call__` instead requires positive ENTRY mean and lower even when the actual cash account reaches a scheduled monthly date. OLC112's `RotationOverlay` preserves monthly rotation only when the account is invested.

The stored label bank confirms this mechanically:

| Saved comparisons on cash-spell dates | PRICE spell | TERM spell |
|---|---:|---:|
| Available native bank comparisons | 209 | 189 |
| HOLD branch has actual orders by endpoint | 196 (93.78%) | 177 (93.65%) |
| Positive ENTRY-minus-monthly-HOLD label | 105 (50.24%) | 97 (51.32%) |
| FRESH terminal wealth exceeds initial cash | 133 (63.64%) | 114 (60.32%) |
| ENTRY label <= 0 despite FRESH wealth exceeding initial cash | 44 | 32 |
| Mean saved ENTRY advantage, log-bp | +53.49 | +72.26 |
| Mean FRESH log growth from initial cash | +0.028703 | +0.025691 |
| Mean delayed monthly HOLD log growth from initial cash | +0.023354 | +0.018465 |

These are overlapping saved 21-session counterfactual-bank descriptions, not independent trials or additive strategy returns. They cannot be summed, annualized, or used as the causal gain from changing the live policy. They also use hypothetical cash at baseline NAV, not the actual stuck account's NAV. The fixed EUR1 ticket therefore has a slightly different relative scale. During these spells actual NAV / bank NAV ranges from 0.5945 to 1.0567 for PRICE and 0.6239 to 1.0751 for TERM.

The table nonetheless proves the target distinction: a negative ENTRY label can coexist with a positive return from entering because the comparison branch also enters later. Repeatedly choosing HOLD using that target does not implement the continuation assumed by the label. The eleven skipped PRICE monthly decisions demonstrate that mismatch in the actual account trace.

Sources: original `BANK_EVENTS.jsonl`, specifically cash-branch `nav`, `orders`, `initial_nav`, and `net`; generated `CASH_DECISION_DETAILS.csv`.

## 4. State support: no large marginal feature excursion, but missing behavioral state

The reconstruction exactly matches every saved ENTRY prediction used in the primary cash-path analysis: maximum absolute mean/lower difference is **0.0**. The reconstructed ENTRY price features also match all **1,564** available corresponding bank feature rows exactly, including repetitions across account paths.

During both long OLC112 spells, the maximum absolute standardized price coordinate is 2.756532. No day exceeds 3 training standard deviations. TERM's complete standardized representation, including residualized option coordinates, also never exceeds 2.756532; its option-coordinate maximum is 2.095085. These comparisons use the contemporaneous monthly model's strictly mature training sample, not the full future bank.

There are six dates outside at least one historical marginal min/max: breadth on 2025-07-10, 2025-10-24, and 2025-10-29; NM63 on 2026-02-25, 2026-02-26, and 2026-02-27. These are limited marginal extensions, not gross standardized extrapolation. Marginal ranges and z-scores do not certify joint support or the correctness of a conditional forecast.

The ENTRY inputs contain fresh NM21, fresh NM63, log(vol21/vol63), breadth, and time to the next monthly date, plus the selected options blocks. They contain **no time already spent in cash, prior skipped opportunities, actual NAV, or an explicit consequence of continuing to postpone the baseline entry**. Since the bank deliberately includes a hypothetical all-cash state on every supported date, ordinary current candidate features can be well supported while the repeated policy's prolonged cash continuation is not represented by the training target. The meaningful mismatch is chiefly the continuation and the selected trajectory, rather than a large numerical feature excursion.

Sources: `state_features`, `AccountPolicy.__call__`, original saved transforms and banks; `SUPPLEMENTARY_DIAGNOSTICS.json` and `*_FULL_FEATURE_SUPPORT.csv`.

## 5. Exit and entry symmetry: no sign inversion, but a large abstention region

I evaluated the already fitted CASH head on a synthetic state holding today's fresh target at its target exposure, and the ENTRY head on that same day's fresh basket. This changes neither fitted parameters nor account returns. There are 1,101 post-readiness supported calendar observations per arm. The CASH and ENTRY starting inventories differ, so exact costless antisymmetry is not imposed.

| Arm | Correlation of CASH and ENTRY predicted means | Both means > 0 | Both action gates pass | Neither action gate passes |
|---|---:|---:|---:|---:|
| PRICE | -0.95870 | 0 | 0 | 952 / 1,101 (86.47%) |
| VIX | -0.89445 | 32 | 0 | 922 / 1,101 (83.74%) |
| TERM | -0.96146 | 10 | 0 | 825 / 1,101 (74.93%) |
| MEAN | -0.86308 | 0 | 0 | 1,101 / 1,101 |

Thus the frozen lower-bound rules never simultaneously authorize selling the fresh basket and buying that same basket in this matched-state exercise. There is no evidence of a simple CASH/ENTRY sign reversal. Independent fitting does allow a small number of both-positive means in the option arms, but their buffers suppress simultaneous approval.

As a separate outcome check, the saved bank has **130** dates when actual baseline weights and the fresh target differ by less than the explicit 3% no-op band. On those near-matched dates, realized CASH and ENTRY labels have correlation **-0.999769**, no pair has both labels positive, and their sum averages **-0.00332147** (-33.21 log-bp). This is consistent with opposing opportunity value plus transaction drag, although near-matching, native fills, future weights and fees prevent an exact algebraic identity. The average sum across all 1,642 dates is similar (-32.88 log-bp), but the lower correlation there (-0.82952) reflects genuinely different held and fresh baskets.

The potential architectural inefficiency is duplication of much of the same opportunity judgment and a broad abstention region, not an observed contradictory buy/sell command. In that region an invested account stays invested while a cash account stays cash. Some state dependence is rational with costs and uncertainty; this evidence does not say the buffer should be removed. Its consequence becomes problematic when HOLD's deployed continuation differs from HOLD's label continuation.

Sources: `MATCHED_FRESH_HELD_PREDICTIONS.csv`, `MATCHED_BANK_LABELS.csv`, `DIAGNOSTICS.json`.

## 6. Why the gate finally crossed on 2026-04-01

The synchronized April entry is not solely a monthly-refit discontinuity. Re-evaluating the existing March model on the April 1 features already yields positive lower bounds:

| Frozen head | March model, March 31 features | March model, April 1 features | April model, April 1 features |
|---|---:|---:|---:|
| PRICE lower | -0.00178942 | +0.00300207 | +0.00414474 |
| VIX lower | -0.00361935 | +0.00419774 | +0.00478037 |
| TERM lower | -0.00387934 | +0.00299709 | +0.00415464 |

Using the April model on the prior day's features leaves all three lower bounds negative. That latter comparison is explicitly a hindsight decomposition, not an eligible historical prediction.

The fresh target changes one of its two 50% holdings from `IE00B53H0131` to `LU2233156749`, retaining `IE0003BJ2JS4`; total absolute weight change is 1.0. Fresh NM63 falls from 1.170698 to 0.558264, and log(vol21/vol63) rises from -0.226946 to +0.165830. These changes move the existing ENTRY rule toward approval. Under the old PRICE fit, the mean rises from 0.00273124 to 0.00931875; the April refit adds a further 0.00104893. This is an exact saved-model/feature decomposition, not an attribution of realized investment profit.

Sources: original selections, saved March/April fits, `SUPPLEMENTARY_DIAGNOSTICS.json`.

## Reproduction and limits

Run `PYTHONDONTWRITEBYTECODE=1 python olc113/research/reentry_diagnosis/diagnose_saved_reentry.py`, then `check_saved_feature_support.py` with the same environment setting. The first script records SHA-256 identities of every input it reads. It loads 52 existing calendar-fit files needed for this post-warmup diagnosis; it does not call the training function, bundle builder, or account simulator. The second script only reads saved heads and arrays and writes supplementary descriptions.

The causal statements supported here are the deterministic program flow: the signs gate ENTRY; invested-only monthly rotation does not restore cash entry; and labels use a different continuation. Forecast bias, concurrent market moves, contribution averages and matched-state correlations are descriptive evidence. No claim is made that correcting a single component would cause a particular CAGR or drawdown improvement.
