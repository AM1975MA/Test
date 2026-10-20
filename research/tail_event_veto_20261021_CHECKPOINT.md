# Extreme-selection-error veto — checkpoint 2026-10-21

Status: **EXPLORATORY / NOT PROMOTED**. No changes to ETF Trader V2 production.

Dataset: original149, 476 decision weeks 2017-01-05 to 2026-06-18; 149 ETF x 476 = 70,924 ETF-date observations. OOS base-score source: GitHub Actions run 39506868766, artifact 12304560383, SHA256 `0d50d0538efac1faf1ce7a76a32ff64f753985a6b450201b3ac3a7d8bce08e36`. Training predictors are frozen OOS ranks from XGB depth7 and B/C/D/E RMT models. **Not the exact original frozen 127-leaf ETF Trader V2 producer.**

Experiment: expanding annual walk-forward test on 325 decision weeks, 2020 to June 2026; *only matured* past 5-business-day labels enter fitting (`t_idx+6<=first test index`). Classification on the top20 alpha-ranked names; targets LOSS3 = forward return <= -3%, and LOSS3_REL = LOSS3 and bottom 20% of cross-sectional returns. Small regularized HistGradientBoostingClassifier; risk features are OOS rank/score disagreements, NOT contemporaneous raw RMT features.

AUC pooled among 6,500 Top20 test candidates: LOSS3 0.5443, LOSS3_REL **0.5848**. LOSS3_REL annual AUC: 2020 0.514 / 2021 0.669 / 2022 0.514 / 2023 0.658 / 2024 0.581 / 2025 0.545 / early 2026 0.725.

The **original RMT-ETF alpha ranking never changes**. Veto replaces at most one selection per week with a lower-alpha-rank backup. VETO95 requires predicted risk in highest 5% of top20 and above historical event prevalence; CAL95 additionally requires probability above the 95th percentile of preceding *historical OOS* Top5 risk predictions. NESTED can enable CAL95 only if its inner 35-week utility improvement meets predetermined alpha-retention conditions.

Net estimate assumes 20 bps × fraction of equal-weight names replaced at each weekly rebalance; maximum drawdown measured on weekly NAV.

| K | Policy | est. net CAGR | weekly net MaxDD | Veto-weeks |
|---:|---|---:|---:|---:|
| 1 | frozen RMT ETF | 13.82% | -50.37% | 0% |
| 1 | LOSS3_REL VETO95 | 23.89% | -51.07% | 37.54% |
| 1 | LOSS3_REL CAL95 | 12.23% | -51.75% | 11.08% |
| 3 | frozen RMT ETF | 20.35% | -41.31% | 0% |
| 3 | LOSS3_REL VETO95 | 22.07% | -37.44% | 64.00% |
| 3 | LOSS3_REL CAL95 | 19.74% | -41.31% | 16.62% |
| 5 | frozen RMT ETF | 20.20% | -39.76% | 0% |
| 5 | LOSS3_REL VETO95 | 21.62% | -37.20% | 77.54% |
| 5 | LOSS3_REL CAL95 | 19.94% | -39.76% | 20.31% |
| 5 | LOSS3_REL NESTED | 20.64% | -39.76% | 7.08% |

Paired moving-block bootstrap (5000 replicates, 8-week blocks) 95% interval for mean weekly net return uplift:
- Top 1 VETO95: +0.1174 pp/week, CI [-0.2732, +0.5656].
- Top 3 VETO95: +0.0060 pp/week, CI [-0.1525, +0.1770].
- Top 5 VETO95: +0.0154 pp/week, CI [-0.0924, +0.1376].
- Top 5 NESTED: +0.0075 pp/week, CI [-0.0152, +0.0373].

**All these intervals contain zero.** Broad veto is not truly rare and is not a defensible extreme-event overlay. Top5 broad veto underperforms the benchmark notably in early 2026; per-year calibration drifts.

**Decision:** no promotion. Keep baseline unchanged; pre-register small, fixed rules for strictly future data (CAL95 and NESTED are research candidates, not selected winners). Prioritize *as-of* market regime / co-movement / raw RMT / volatility features and original exact 127-leaf parity. Test execution with daily NAV and realistic costs. The historical 2020–2026 set has been researched extensively: not a pristine out-of-sample gate.

Reproducible complete Python sources and score outputs are packaged as conversation artifact `Tail_Event_Veto_Research_20261021.zip`, SHA256 `18f8cf5dc12dc46d4b3db8f074543a534506751414cab534b353407183bf6d3e`. Source contents: `tail_event_veto_walkforward.py`, `tail_event_robustness.py`, `TAIL_EVENT_VETO_RESEARCH_20261021.md`, `tail_event_results/*`. GitHub Actions score-export workflow and preceding research checkpoint remain on this branch.