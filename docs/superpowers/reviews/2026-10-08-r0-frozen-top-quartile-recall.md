# R0-C — Frozen LTR top-quartile winner recall (READ-ONLY; not a trading backtest)

**Date:** 2026-10-08. **Scope:** `AM1975MA/Test`, branch `research/v2-xgb-immutable-checkpoints-20261008`. No new training, no prior tests rerun, no V2 risk or source change. This diagnostic follows the user's explicit authorization to examine a first-level ~75%-elimination cascade analytically.

## Inputs: immutable, already OOS in historical experiment

1. [Retriever full scores](../../../evidence_v1/checkpoints/retriever_ltr_v1/OOS_PREDICTIONS.csv), Git blob `1745a6d12b6957bc629998c7ac3417550ac9bceb`, 1,318,640 bytes; 27,162 rows over 186 historical signal dates, `signal_date,ticker,LTR_SCORE,LTR_RANK,LTR_POSITION`.
2. [Prior cascade month ledger](../../../evidence_v1/results/cascade_v1_ltr_top5_hybrid24/MONTHLY.csv), Git blob `85ce4db4600efdb701b045d87d89cd099310459a`, 20,374 bytes; 114 rows from 2017-01-31 to 2026-06-30, including `global_winner` defined by **ex-post forward 21-day total-return winner**, and frozen Top5 flag.
3. [Retriever historical summary](../../../evidence_v1/results/retriever_ltr_v1/SUMMARY.json). Annual expanding fit with maturity gates is *historical source provenance*, not a retrain performed now.

## Fixed rule (no outcome-based threshold optimization)

For each of 114 evaluation dates, choose `K=ceil(0.25×N_t)`; all 114 dates contain **149** distinct ETF candidates, giving `K=38`. A month is a **winner-retention success** if the ex-post global 21-day winner has frozen `LTR_RANK<=38`. This is a retrospective upper bound for a second-stage selector *using this retriever*, not the performance of a real cascade. No new features, fitted models or orders.

### Recomputed result

| Frozen LTR shortlist | Months containing actual best 21d ETF | Historical recall |
|---|---:|---:|
| Top5 | 32 / 114 | 28.0702% |
| Top10 | 47 / 114 | 41.2281% |
| **Top38 of 149** | **97 / 114** | **85.0877%** |
| Top37 (rounding diagnostic only, NOT selected after returns) | 97 / 114 | 85.0877% |

Breakout:
- **2017–2022:** Top38 56/72 = 77.7778%.
- **2023–2026:** Top38 41/42 = 97.6190%.
- **17/114 actual best ETFs** are outside the Top38. The extreme upside losses of those 17 months were **NOT** quantified in this diagnostic.
- Yearly Top38 retention counts: 2017 10/12; 2018 11/12; 2019 8/12; 2020 8/12; 2021 8/12; 2022 11/12; 2023 12/12; 2024 11/12; 2025 12/12; 2026 Jan–Jun 6/6.

**Excluded monthly global winner, ticker and frozen LTR rank:**
2017-04-28 EWY #65; 2017-07-31 DBB #78; 2018-01-31 HACK #92;
2019-01-31 ASHR #51; 2019-02-28 EPI #57; 2019-04-30 CORN #68; 2019-08-30 PALL #46;
2020-05-29 KWEB #42; 2020-06-30 SLV #99; 2020-10-30 EWO #57; 2020-11-30 URA #60;
2021-02-26 PALL #48; 2021-03-31 CORN #72; 2021-07-30 ARGT #53; 2021-10-29 SMH #39;
2022-07-29 TUR #91; 2024-03-28 DBB #92.

## Fresh audit checks (all satisfied)

- 114/114 frozen month keys joined to full OOS scores; 149 unique candidates per month.
- 0 duplicate tickers per joined date; 0 duplicated `LTR_RANK` values; 0 missing global winner.
- The **32/114** Top5 recomputed flags agree **month-by-month** with the archived `top5_contains_global_winner` flags (**0 disagreements**).
- Top10 47/114 confirms `retriever_ltr_v1/SUMMARY.json` `winner21_hit_at_10 = 0.41228070175438597`.
- Original Top5→Hybrid24 cascade already **REJECTED**; Top10 paired/reranked methods already **REJECTED** (see [earlier expert brief](../reviews/2026-10-08-v2-xgb-leaf-mlp-cascade-expert-triage.md)). No attempts repeated.

## Important limitations and decision

- **Retriever LTR v1 is NOT canonical Compact21**; this does not measure the screening recall of ETF Trader V2 itself.
- `global_winner` is defined **using future realized 21d returns** but used **only for ex-post evaluation**. It cannot be a contemporaneously known target to drive a live screening decision.
- This does **NOT** estimate CAGRs, transaction costs, exposure of selected V2 top1/top2, ability of the second-stage model to choose the right winner, or cross-vintage robustness. It uses one original frozen training/data vintage, and the same already-used Original149 dates; **not new independent validation**.
- **High upper-bound recall ≠ approval of a hard screener**: 17 major opportunities were excluded, with worse performance in 2019–21, potentially harmful to strategy CAGR. No threshold selection, Top37 vs Top38 selection, cascade training or financial replay is authorized.

**R0-C disposition:** **Feasible to investigate further, but not eligible for strategy testing without** (a) frozen **canonical Compact21** Top38 rankings and a comparable outcome/position ledger, (b) exposure-weighted tail-miss regret rather than just hit counts, (c) vintage stability, (d) reviewer-approved prospective gate. If evidence not recoverable, mark `UNIDENTIFIABLE` and stop rather than refit old tests. 
