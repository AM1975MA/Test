# V3 L03 — can market regime predict which frozen ETF expert succeeds?

**Date:** 21 October 2026. **STATUS: COMPLETED — simple supervised market-regime selector REJECTED.** Do not turn off the tail or switch experts on the basis of this model.

## Protocol

- Provenance: [successfully executed GitHub Actions 39659065223](https://github.com/AM1975MA/Test/actions/runs/39659065223), complete artifact **12372647559**.
- Frozen source: 149 original ETFs and 500 canonical baskets from run 39482809691; independent annual OOS score artifacts: L01 `CORRECTED` pairwise-127 ranker from 39652989033, L02 `TAIL_EVENT_LOGIT45` from 39655513813. **No modification or retraining** of L01/L02.
- Historical regime-expert outcome for month t: winner-capture Top-3 by the ranker vs the Tail over the exact same baskets and 21-trading-day forward target. The binary label is whether Tail's capture was higher.
- Seven ex ante month-end features only: SPY 21/63/126d return, 21d realized volatility, 63d zero-target downside deviation, 21d cross-sectional breadth and dispersion.
- Fit annually from 2022 onward with L2-logistic regression `C=.1` on expert outcomes with **exit_date21 strictly before the current annual cutoff**; 2018–2021 controls are only historical training observations. Compare with train-only Laplace-smoothed static prior and fixed experts. No oracle future outcomes at inference.
- No CAGR, financial allocation, active Tail modification, portfolio optimization or risk overlay.

## Completely out-of-year predictions, 53 test months, 2022-01 to 2026-05

| Intrinsic regime metric | Gate | Train-only constant-prior baseline |
|---|---:|---:|
| Predict future Tail-higher-Top3 event ROC-AUC | **0.470238** | — |
| Brier probability loss | 0.253953 | **0.250041** |
| Log loss | 0.718008 | **0.695026** |
| Correct expert choice fraction | 62.264% | 60.377% |

On common-month 500-basket Top-3 captures:
- Fixed pairwise L01 ranker: **39.162%**.
- Fixed upper-winner Tail L02: **44.268%**.
- Static train-prior expert choice: **44.268%**.
- Logistic market gate choice: **44.830%**.
- Future-knowing oracle choice (**not live feasible**): **50.177%**.

Logistic gate gain over the train-prior static choice: **+0.562 percentage points**, paired 6-month block-bootstrap interval **[0,+1.687] pp**, 6,000 draws; sparse switching and 53 monthly samples yield little independent evidence. Its worse AUC, Brier and log loss *contradict* a claim of general regime predictability. Retrospective gain from occasional switching is insufficient to promote a classifier whose actual declared function (forecast expert reliability) fails.

## Decision and L04 handoff

**Reject L03 market-only gate.** The two experts may contain complementary information even though a market feature-only classifier cannot predict which is better. Keep both frozen and test nonconditional, explicit score-level blends in **L04** against the better static expert, with all dates, data and return-rank targets identical. A blend must improve true Top-3/recall and regret, not simply a single CAGR. Do NOT optimize blend weights to the test years and call the resulting number unbiased.

No full ETF Trader production configuration changes. Re-evaluate any regime classifier only with new ex ante sources, a predeclared training protocol and an independent future vintage.
