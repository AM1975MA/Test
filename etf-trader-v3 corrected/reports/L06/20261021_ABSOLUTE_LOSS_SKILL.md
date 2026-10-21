# V3 L06.4 — Absolute severe-loss prediction among ETFs actually chosen by Tail

**Date:** 21 October 2026. **Prediction-only diagnostic PASS (limited), not operational risk policy approval.** No CAGR or changes to ranker, Tail, selection or allocation.

Completed [GitHub Actions 39671493979](https://github.com/AM1975MA/Test/actions/runs/39671493979), artifact ID **12379922220**, `v3-l06-absolute-loss-capability`.

## Predeclared, causally valid outcome

- **One absolute loss threshold, specified before testing:** actual next-open to 21-trading-days-forward adjusted ETF return **<=−10%**.
- Input immutable frozen 149 ETFs, 500×24 canonical baskets; old risk estimator `p_bad` was already strictly annual OOS in [39662062361](https://github.com/AM1975MA/Test/actions/runs/39662062361), trained using fully mature future labels. Frozen Tail expert remains unchanged.
- Only count each **unique ETF-month** that is in Top3 of at least one basket selected by Tail. This avoids pretending the ~500 overlapping baskets produce independent ETF outcomes.
- Train only one monotonic `LogisticRegression(C=.2)` calibration mapping risk score to probability of this particular absolute-loss event, expanding from 2018 and strictly requiring mature next-open+21-trading-day labels before each Jan 1 fit. Test 2022 through May 2026 (53 months).
- Compare with original `p_bad` risk ranking and the current-year **train-only constant event prevalence**. No future labels enter inference and no portfolio action is taken.

## Measured skill: 53 monthly dates

| Metric | Value |
|---|---:|
| Distinct selected ETF-months | **2,281** |
| Realized absolute losses <=−10% | **162** |
| Event prevalence | **7.1021%** |
| Original frozen risk Average Precision vs absolute event | **0.132503** |
| Lift of AP above prevalence | +0.061482, **1.866×** prevalence |
| Original frozen risk ROC AUC | **0.626553** |
| Calibrated risk Brier | **0.065499** |
| Train-only constant prior Brier | 0.066403 |
| Probability-calibration Brier skill vs prior | **1.36%** |
| Top 15% frozen risk alert precision, mean across months | **12.376%** |
| Top 15% frozen risk alert recall of severe losses, mean across months | **28.529%** |
| Top 15% frozen risk alert false positive rate, mean across months | **15.350%** |

Circular six-calendar-month block bootstrap, **1500 resamples**, recomputing pooled OOS unique ETF-month AP/AUC within resampled calendar blocks:
- ROC AUC **0.626553**, 95% exploratory CI **[0.542620,0.724198]**.
- AP **0.132503**, CI [0.085357,0.196452], base prevalence 0.071021 with CI [0.041739,0.105928].
- AP minus prevalence **+0.061482**, CI **[+0.023631,+0.115438]**.
- Calibrated Brier minus train-only constant Brier **−0.000903**, CI **[−0.001721,−0.000215]**.

The risk score indeed contains some information on **subsequent absolute large losses**, even among Tail-selected ETF opportunities. It is not a strong classifier: selected ETF event AUC is only about 0.63, so many signals are false or missed. The annual calibrator changes score ordering across different years (so pooled AP of calibrated risk may be lower), but enables proper probability scoring and slightly improves Brier versus train-only prevalence.

## Yearwise caution

| Year | N distinct ETF-months | Severe events | Frozen risk AUC |
|---|---:|---:|---:|
| 2022 | 499 | 58 | 0.532 |
| 2023 | 528 | 40 | 0.620 |
| 2024 | 513 | 13 | 0.744 |
| 2025 | 523 | 15 | 0.618 |
| 2026 through May | 218 | 36 | 0.721 |

Significant variation in event prevalence and skill. Data 2018–2026 have been previously explored; intervals are **research evidence, not an independent virgin holdout**.

## Decision and next isolated task

**Maintain `P(absolute next21d loss>=10%)` as a defensible, causal research risk forecast, not a veto.** Next test may use only these annual OOS calibrated probabilities for a **single predeclared soft reweighting of the original same-three Top3 50/30/20 ETF set**, measuring absolute-loss weight avoided vs true winner weight, regret, realized rank and turnover, on identical 53 later months. Do not tune the risk coefficient to these historical years or claim CAGR improvement.

Full V3 / production remains unchanged.
