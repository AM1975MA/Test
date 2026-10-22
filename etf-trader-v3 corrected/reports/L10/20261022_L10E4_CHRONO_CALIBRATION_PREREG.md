# ETF Trader V3 L10.E4 — strict chronological calibration of the *same* post-ML pairwise veto (pre-registration)

Frozen 2026-10-22 before computing any E4 outcomes. No global re-ranking, no retraining Pairwise127 or the E3 pairwise model.

## Hypothesis

E3 approved 965 basket-slot changes from 363 distinct ETF-month pairs based on uncalibrated model P(challenger outperforming incumbent by >=1 percentage point next21D) >=70%. E3 acted-pair mean score was ~74.96%, observed success ~60.61%, and 10bps fee-aware aggregate CAGR did NOT improve: long period ~15.65% original vs ~15.61% E3, recent ~21.43% original vs ~20.98% E3. E4 checks whether an **expanding past-only out-of-time probability calibration** can avoid false E3 vetoes. Do not reinterpret reduced action as outperformance.

## One, and only one, new variable relative to E3

Read frozen 18,218 unique date/incumbent/challenger E3 candidate rows from archived run **39752940429** (all original E3 scores, outcomes, label exit dates). Do not regenerate or refit the E3 estimator. Within each calendar year Y, fit Platt logistic regression (L2 C=1.0, random_state=20261022, intercept, no class balancing) to **logit(clipped raw probability, 1e-6, 1-1e-6)** versus observed E3 binary label. Include only E3 predictions from calendar years strictly <Y for which the actual forward next-open+21D outcome exit **< January 1 Y**. Deduplicate exact date/incumbent/challenger pairs and weight each past calendar signal month equally (per pair 1/number of unique pairs that month; normalize mean sample weight to 1). Require at least **8 distinct fully mature OOS signal months, 300 OOS unique pair observations, two label classes**. If insufficient sample or fitted sigmoid has a nonpositive raw-score coefficient, abstain (all original ML Top3 unaltered); never use non-out-of-time E3 pair predictions to calibrate.

For E4 in year Y, for each original top3 ETF that was **already E1 flagged**, take its **specific first unflagged next ML-ranked replacement** per E3 original algorithm, look up the exact unique pair/date frozen E3 raw probability, apply only this pre-year frozen sigmoid. Approve substitution **only when calibrated P(success) >=0.70**. E3 uses uncalibrated >=.70 on the very same proposals, re-evaluated here for exact parity. All other ML selections, 50/30/20 position weights, 149 ETFs, same original 500 overlapping baskets, candidate set, monthly signal dates, labels and E3 first-stage model stay unchanged. This calibration is the ONE changed variable.

## Independent checks and gate

Synthetic prefix past-only raw price features and source E3 fit audits already passed in prior run. Before viewing any E4 results check: E3 pair source 18,218 unique keys, parity of label and exit maturity with reconstruction; reconstructed E3 exactly 965 basket-slot replacements and corresponding E3 monthly aggregate and BASE metrics from archived run; 101 fully mature months; each calibrator cutoff and used source prediction/label exit strictly earlier; all flags/proposals must match original E1 source. Calibration curve and Brier/log-loss by year on out-of-time evaluated pairs, report number of months with abstentions, coefficient slope and intercept, raw vs calibrated acted-upon observed precision and future relative return, false veto of actual basket-best invested weight, loss10 weight avoided, winner coverage, weighted rank/regret. Paired 6-month calendar bootstrap 6000 draws on 101 monthly basket aggregates, compare E4 minus BASE and E4 minus E3, no treatment of 500 overlapping baskets as independent.

**CAGR rule:** fee-aware exact same L07 next-open 10bps Top3 replay, common last mature May29 2026 signal with end June1 2026, ONLY if E4 shows a credible improvement versus BASE in winner protection and loss control/return, NOT if it simply reduces E3 activity to zero. No tuning probability cutoff after evaluating E4. Repeated 2018–2026 history is heavily explored, not a virgin external validation. Do not touch V2 or frozen V3.

This E4 is calibration only. Cost-sensitive false-veto penalty is a *measured decision consequence*; it is NOT a new learned threshold or feature in this test.
