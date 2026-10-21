# V3 L02/02 — Tail event-classification test, unchanged corrected feature schema

Date: 21 October 2026. **Completed and independently reproduced.** 
Result provenance: [successful Action 39655513813](https://github.com/AM1975MA/Test/actions/runs/39655513813), artifact `12370967578`. Repeated successful execution: [39657129881](https://github.com/AM1975MA/Test/actions/runs/39657129881).

## Functional test, not financial optimization

- Source-only frozen 149-ETF OHLCV snapshot from run `39482809691`, canonical 500 baskets.
- 98 month signals with fully mature 63-day labels in 2018–2026, expanding annual refits. Calendar already extensively examined (NOT virgin independent holdout).
- **Frozen 45 unique corrected Tail columns**; same training rows, ETF-months, imputer, scaling, and label maturity.
- Control: original `Ridge(alpha=30)` trained on quartic ordinal `y_tailmix` with 21/42/63-day information.
- Challenger: `LogisticRegression(C=.2,class_weight=balanced)` trained to classify top 10% of the *same future matured Tail target*. Only objective and learner change as a related functional intervention; Compact/ranker, macro, blends, weights and risk remain disabled.
- No CAGR, full strategy performance or stock trading objective used.

## Results — 98 matured OOS months

| Tail functional metric | Ridge45 | Elite Logistic45 | Paired delta |
| --- | ---: | ---: | ---: |
| Top-tail Average Precision | 0.269720 | **0.288357** | **+0.018637**, 95% CI [+0.005488,+0.032322] |
| Top-tail ROC AUC | 0.710625 | **0.744162** | **+0.033536**, CI [+0.020925,+0.046868] |
| Elite recall among top 15 scores | 24.626% | **26.939%** | **+2.313 pp**, CI [+1.020,+3.673] pp |
| Basket best-Tail Top-3 winner capture | 35.465% | **39.798%** | **+4.333 pp**, CI [+2.122,+6.582] pp |
| Tail target IC | **0.123527** | 0.111076 | -0.012452, CI [-0.030552,+0.006072] |
| 21-day bottom-decile false selections | **25.620%** | 28.020% | **+2.400 pp**, CI [+0.108,+4.439] pp |

Paired uncertainty unit is shared **calendar month**, 6-month circular block bootstrap, 6000 replications; 500 overlapping baskets are not treated as independent. The positive elite metrics indicate better winner identification, **but** the deterioration in bottom-decile selection rejects unconditional substitution before addressing tail-risk classification.

## Decision

**PROMISING BUT NOT YET LOCKED:** the classifier meaningfully strengthens the Tail's designated upper-tail retrieval task, but increases errors involving bad 21-day ETF outcomes. The next L02 single-variable subtest retains its elite scores literally unchanged and only adds a separately trained negative-tail predictive head with a predeclared, small rank penalty. Promote the Tail to any blend only after showing the incremental head can mitigate this specific defect without losing elite capture. No changes to L00/L01 are authorized.
