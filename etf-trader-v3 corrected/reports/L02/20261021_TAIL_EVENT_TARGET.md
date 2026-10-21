# V3 L02/02 — Direct upper-tail event classification vs continuous Tail regression

**Date:** 21 October 2026. **Model skill test complete. Acceptance:** Upper-tail winner recognition **PASS**; downside false-selection guardrail **FAIL** (separate single-variable mitigation required). No production/fusion promotion.

- [Successful Actions run 39655513813](https://github.com/AM1975MA/Test/actions/runs/39655513813), complete `v3-l02-tail-event-results` artifact **12370967578**.
- 149 frozen original ETFs, same 500 baskets, 98 months with fully matured 21/42/63D tailmix labels.
- Both variants use the **same 45 unique Tail input columns, same rows, same annual training maturity cutoff** and identical imputer/standardization.
- Reference `TAIL_DEDUP45`: Ridge(alpha=30) trained to regress original quartic future rankmix `0.60 * rank21^4 + 0.25 * rank42^4 + 0.15 * rank63^4`.
- Challenger `TAIL_EVENT_LOGIT45`: logistic(C=0.2, balanced classes) trained to identify ETFs within the **highest 10% of the monthly mature future Tail score**, using only training labels already known before each annual cutoff.

| Intrinsic Tail metric | Ridge 45 | Logistic event 45 | Difference |
|---|---:|---:|---:|
| Average precision for future best 10% | 0.269720 | **0.288357** | **+0.018637** |
| ROC AUC for best 10% | 0.710625 | **0.744162** | **+0.033536** |
| Recall of future best 10% among 15 signaled ETFs | 24.626% | **26.939%** | **+2.313 pp** |
| Basket Tail best-name in selected Top-3 | 35.465% | **39.798%** | **+4.333 pp** |
| Monthly continuous Tail-score IC | **0.123527** | 0.111076 | -0.012452 |
| False selections in future bottom 10% by 21D | **25.620%** | 28.020% | **+2.400 pp** |

Paired 6-month-block 6000-resample exploratory intervals (98 monthly units; overlap baskets not independent):
- ΔAP [+0.005488,+0.032322], point +0.018637.
- Δrecall top-15 [+0.010204,+0.036735], point +0.023129.
- Δbasket Tail Top-3 [+0.021222,+0.065818], point +0.043327.
- Δfuture 21D worst-decile false-selection [+0.001082,+0.044391], point +0.024000.

The directly supervised logistic head is a **real skill improvement for its named upper-winner task**, even though it is not the best forecaster of the full continuous Tail score. But it selects more extreme future losers, violating the Tail safety guardrail. We do NOT authorize blindly injecting this head into the frozen ranker score or production V2.

**Next single-variable L02 subtest:** freeze the positive-event logistic model/output and add a separately trained bottom-decile classifier as a protective Tail penalty. Evaluate impact on future winner precision/recall *and* worst-decile false selection, not CAGR.

Future enhancement must be checked against the confirmed E2E system after separate L03–L06 gates; 2018–2026 is a highly explored research calendar, not an untouched holdout.
