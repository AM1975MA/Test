# ETF Trader V3 Corrected — L00/01: Preserve missingness-regime information

**Date:** 21 October 2026  
**Status:** **FINISHED — TWO CANDIDATES REJECTED; L00 remains open for the next isolated feature-quality test.**  
**Production:** Untouched. **No promotion or merge.**

## Audited, successful reproducible run

[GitHub Actions run 39645036665](https://github.com/AM1975MA/Test/actions/runs/39645036665), result artifact **12368070748** (`v3-l00-complete-paired-rank-and-economics`), with per-year training shards and complete full-ETF OOS scores.

Source: `etf-trader-v3 corrected/src/etf_trader_v3/source_only/` contains a self-contained corrected copy of all 13 source-only modules. Test of 203 declared Compact/Tail/auxiliary features and temporal-causality synthetic conditions: **passed**.

The input is the immutable 149-ETF raw OHLCV snapshot from GitHub Actions **39482809691**; canonical 500 baskets of 24, and original V2 score controls fully refitted and certified in **39515716383**, with exact numerical replay vs official 127-leaf original over 15,198 ETF-months.

This is a strictly paired retrospective research replay, **not an independent previously untouched holdout**. All arms share exact labels, eligible ETF-months, years, seeds, original 30-of-125 feature availability gate, 360-round XGBRanker and max 127 leaves. No Tail, macro, expert allocation or risk controls.

## Predeclared feature arms (only L00 modified)

| Arm | # Columns | Engineering change |
|---|---:|---|
| LEGACY | 125 | Unmodified historical original for numerical oracle |
| CORRECTED | 125 | Mathematically valid downside deviation / RSI etc. |
| V3_GATE128 | 128 | CORRECTED + three binary indicators of the old `downvol` valid/NaN threshold |
| V3_CONDSTD128 | 128 | CORRECTED + explicitly named three negative-only conditional return stds; preserve genuine NaNs |

Both contenders were trained from scratch, chronologically, with labels only after actual maturation. Reference controls are the existing frozen OOS scores from run **39515716383**, not newly tuned.

## Predictive performance: 101 OOS months, 2018–May 2026

| Metric | LEGACY | CORRECTED | V3_GATE128 | V3_CONDSTD128 |
|---|---:|---:|---:|---:|
| Full-universe monthly Spearman IC | **0.042796** | 0.038536 | 0.034934 | 0.035510 |
| Basket Top-1 | **15.087%** | 14.552% | 14.655% | 14.014% |
| Basket Top-3 | **35.745%** | 35.471% | 34.729% | 34.956% |
| Mean basket 21D regret | **10.208%** | 10.412% | 10.331% | 10.580% |
| Mean basket selected excess return | **0.916%** | 0.712% | 0.793% | 0.544% |

Comparisons use monthly means over 500 **overlapping** baskets; basket rows are not independently resampled. Pairwise 6-calendar-month circular block bootstrap, 6,000 replicates:

- V3_GATE128 minus CORRECTED basket Top-3: **-0.743 pp**; exploratory 95% CI **[-1.998, +0.471] pp**.
- V3_CONDSTD128 minus CORRECTED basket Top-3: **-0.515 pp**; 95% CI **[-1.970, +0.915] pp**.
- Neither new challenger passed the **positive Top-3 uplift** condition, even before multiplicity adjustment. Therefore neither qualifies for promotion.
- The direction varies by historical period, but no post-hoc regime choice is justified by these data.

## Economic performance: 500 baskets, next-open 10bps traded-cost replay

From 2018-02-02 to 2026-07-01. Scores are percentiled cross-sectionally each signal month; monthly Top-2 75/25 or 100% Top-1 if rank gap ≥0.12. No Tail/Macro/risk.

| Metric | LEGACY | CORRECTED | V3_GATE128 | V3_CONDSTD128 |
|---|---:|---:|---:|---:|
| Basket mean CAGR | **13.297%** | 12.057% | 12.077% | 9.654% |
| Basket median CAGR | **14.470%** | 13.554% | 13.018% | 10.933% |
| Aggregated NAV CAGR | **15.941%** | 14.729% | 14.647% | 12.406% |
| Mean basket MaxDD | -51.289% | **-50.341%** | -51.541% | -52.615% |
| Mean Sharpe (RF=0) | **0.557** | 0.524 | 0.526 | 0.457 |
| Gross turnover per year | 17.094 | 16.983 | 17.104 | 16.971 |

Paired 21-trading-day calendar-block bootstrap on mean across baskets of daily *log* return differences, 4,000 replicates:

- V3_GATE128 minus CORRECTED annual log uplift **+0.050 pp**, 95% CI **[-2.317,+2.314] pp**.
- V3_CONDSTD128 minus CORRECTED annual log uplift **-2.185 pp**, 95% CI **[-4.562,+0.075] pp**.
- V3_CONDSTD128 minus LEGACY annual log uplift **-3.308 pp**, 95% CI **[-5.916,-0.728] pp**.

This is an **XGB-only** economic test, not the full ETF-trader-V2 production stack or previously published full scorer CAGR.

## Decision and sequential next step

**Reject both challengers** in this L00 sub-experiment. Retain `CORRECTED 125` as the V3 mathematical **research reference**, without claiming it is a higher-performing winner versus `LEGACY`. The earlier raw mathematical bug must not be reintroduced under the misleading `downvol` name.

L00 itself is **NOT CLOSED**: before L01 ranker experiments, the next distinct, preregistered feature-quality operation is to audit causality/data semantics (adjusted OHLCV volume-proxy issue; missingness in _pct/_dev; robust-zero MAD; redundant aliases; conditioning on ETF age/category; full-price-history availability) and isolate only demonstrable defects or new orthogonal signals. Do not combine such changes with L01 leaf/architecture tuning. No layer below L00 is changed until L00 input semantics and selected reference are frozen.

If statistical evidence remains ambiguous, prefer fewer genuine economic features and explicit definitions, and require an independently unseen validation vintage before any production transition.
