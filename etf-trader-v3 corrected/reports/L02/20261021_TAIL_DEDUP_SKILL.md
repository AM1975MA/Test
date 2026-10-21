# V3 L02/01 — 60 duplicated Tail inputs vs 45 unique fields

**Status:** COMPLETED. Functional result nearly unchanged; no demonstrated predictive gain. **Do not modify Compact/L01 or blended score.**

- Verified [GitHub Actions 39654585994](https://github.com/AM1975MA/Test/actions/runs/39654585994), artifact **12371615813**.
- Frozen original 149-ETF source 39482809691, 500 fixed baskets; strict mature 63-trading-day forward multi-horizon Tail target, 98 evaluable monthly signals during 2018–2026.
- Same 60-column `TAIL_FEATURES` source schema and `Ridge(alpha=30)` with median imputation plus standardization. Alternative removes exactly the **15 demonstrated bit-identical alias columns**, otherwise untouched.
- Compete on the Tail's own mission: ranking strong winners and avoiding severe 21D false selections; no CAGR/portfolio.

| Metric | Full60 | Dedup45 |
|---|---:|---:|
| Tail top-decile event average precision | 0.269454 | 0.269720 |
| Tail top-decile event ROC-AUC | 0.710514 | 0.710625 |
| Top-15 elite recall | 0.246259 | 0.246259 |
| Tailmix monthly rank IC | 0.123519 | 0.123527 |
| Tail best-in-basket Top-1 capture | 0.145898 | 0.146286 |
| Tail best-in-basket Top-3 capture | 0.355163 | 0.354653 |
| Tail target regret of top-selected | 0.485948 | 0.485645 |
| Selected ETF in future 21D basket worst decile | 0.256224 | 0.256204 |

Paired monthly 6-month circular bootstrap:
- ΔAP +0.000266, CI [-0.000179,+0.000766].
- ΔTop-15 elite recall exactly 0.000000, CI [-0.003401,+0.002721].
- ΔTop-3 -0.000510, CI [-0.001633,+0.000612].
- Δfalse-selection rate -0.000020, CI [-0.001245,+0.001001].

**Decision:** `TAIL_DEDUP45` is a reasonable **versioned representation-simplification reference** (45 distinct inputs, no observed material functional change). It is not a proven winner. Any non-inferiority threshold must be registered before treating the result as confirmation. Keep `TAIL_FULL60` as oracle; neither is promoted to production.

Next L02 isolated test (same 45 features): replace the original squared-ordinal `y_tailmix` Ridge regression with a **binary upper-decile Tail event classification** model. Its sole objective is improving top-tail Average Precision/elite recall without changing feature inventory, calendar, L01 or execution.
