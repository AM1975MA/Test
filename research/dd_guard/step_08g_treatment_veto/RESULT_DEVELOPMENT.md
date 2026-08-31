# STEP08G — Event-Time Titanium + Treatment-Value Veto

**Verdict: REJECT_BEFORE_2023_HOLDOUT.** 2023+ remains sealed.

## Development vs FUSION1

| policy | cagr | dd | sh | calmar | p10 | p5 | worstdec | worst | delta_cagr_pp | delta_maxdd_pp | delta_p10_pp | delta_p5_pp | delta_worst_decile_pp | delta_worst_pp | delta_sharpe | delta_calmar |
|:--|--:|--:|--:|--:|--:|--:|--:|--:|--:|--:|--:|--:|--:|--:|--:|--:|
| EVENT_TIME_TIT_R_PLUS_TREATMENT_VETO | 19.652651 | -26.506487 | 0.728242 | 0.896821 | -36.296295 | -39.547746 | -41.306371 | -53.106276 | -0.790293 | -0.354431 | -0.482474 | -0.279792 | -0.628451 | 0.000000 | -0.021172 | -0.043086 |

## Annual deltas vs FUSION1

- 2021: delta CAGR **-1.072595 pp**, delta mean MaxDD **-0.338849 pp**, delta p10 **-0.754944 pp**.
- 2022: delta CAGR **-0.514810 pp**, delta mean MaxDD **-0.160823 pp**, delta p10 **-0.004603 pp**.

## Mechanism

- Decisions: **1,124**.
- STAY: **83.452%**.
- BIL: **16.281%**.
- ETF: **0.267%**.
- Among non-STAY actions, realized utility beats exact FUSION1 only **28.495%** of the time.

## Direct comparison vs STEP08F

The veto gives back **-1.422776 pp CAGR** and **-0.404934 pp mean MaxDD** versus STEP08F. It improves some tail quantiles versus STEP08F (p10 +0.382539 pp, p5 +1.694694 pp), but not enough to beat FUSION1 and it destroys the saved event-time alpha improvement.

Validation replay parity was corrected to use exactly the 2021–2022 FUSION1 alert set used by STEP08F. The frozen treatment model and all ETF/BIL/STAY decisions were unchanged by that accounting correction.

No 2023+ outcome was opened. No post-result tuning was performed.
