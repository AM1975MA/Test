# V3 L02.4 — rare-event Tail logistic: class_weight balanced → None

**21 October 2026: completed, NOT promoted.** [Success run 39675781293](https://github.com/AM1975MA/Test/actions/runs/39675781293), artifact **12381171838**. Same 149 ETFs, 500 baskets, 98 fully mature 63D Tail-label OOS months; unchanged 45 unique Tail features, same elite future-event target, same C=.2 logistic regression with median imputation/standardization and same chronological annual train. **One intervention only:** class_weight balanced → None; no changes to risk, ranker, blend or CAGR.

| Tail intrinsic functional metric | Frozen balanced | Class-weight none |
|---|---:|---:|
| Upper-tail elite event Average Precision | **0.288357** | 0.285796 |
| ROC-AUC | **0.744162** | 0.742014 |
| Elite recall in top15 forecasted ETFs | 26.9388% | **27.5510%** |
| Actual best-Tail ETF in basket Top3 | **39.7980%** | 39.6490% |
| Future 21D bottom-decile false selection | 28.0204% | **27.8388%** |

Paired 6-calendar-month block bootstrap: elite recall difference **+0.612 pp**, 95% CI **[+0.068,+1.225] pp**; AP difference **−0.002561**, CI [−0.007178,+0.002054]; basket Tail Top3 difference **−0.149 pp**, CI [−0.925,+0.563] pp. Both AP and Top3 show no convincing improvement; the recall increase is small, potentially a different tradeoff rather than genuine stronger specialist performance.

**Decision: retain original balanced Tail45 logistic** as upper-winner specialist. No independent untouched calendar is available for broader claims.
