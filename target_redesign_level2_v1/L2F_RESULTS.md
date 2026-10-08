# L2-F — fixed 75% Ridge core / 25% XGB opportunity sleeve

**Run date:** 2026-10-08. **Status:** completed, independently audited, **EXPLORATORY — NOT PROMOTED**. Repo `AM1975MA/Test` only; **no modifications to Etf_trader**.

[Protocol registered before THIS overlay outcomes](L2F_PREREGISTRATION.md), after L2-E had been observed. Source: frozen Original149 149 tickers × three Yahoo 2026 acquisition vintages (artifact [11272972639](https://github.com/AM1975MA/Test/actions/runs/37121749852)), 113 monthly signal dates 2017-02 through 2026-06, **112 nonoverlapping next-open holding periods**; BIL no cash target (ordinary ticker only).

## Design and accounting

Exactly **one capital allocation**: 75% marked-to-market equity in the ETF selected by independently fitted stable Ridge, 25% in original XGBoost's ETF. Overlapping choices combined into one position. Same individual ticker score series as L2-D; no new training, no lookahead/future labels in each decision, no hyperparameter/wt optimization.

Three books were **all independently reconstructed** with identical mathematical transaction-cost rules: Ridge100%, XGB100%, Core75/Satellite25%. First buy at March 2017 next-session OPEN, 112 subsequent nonoverlapping monthly periods ending July 2026 next-session OPEN, no phantom acquisition of a last unmatched position, final complete sell. Mark to adjusted Yahoo Opens. Every rebalance exactly solves self-financing constraint `Wpost + 0.001 * sum_i |Wpost * w_target_i - holdings_before_i| = Wpre`. Buy and sell are charged 0.1% per traded notional, including initial purchase and final liquidation; no leverage or free turnover.

**Important audit correction to the previous L2-D / L2-E single-name proxy**: L2-D applied an additional round-trip switch fee when the last, never-held signal named a different ETF; L2-F excludes this non-existent terminal switch. The resulting baseline CAGR changes are **+0.026–0.030 percentage points**, with wealth changes ~+0.21%; the original L2-D headline 17.09% vs 17.12% etc. should therefore be considered *slightly understated*; the side-by-side table below consistently uses the corrected fee policy for all models. This known legacy discrepancy was transparently flagged by QA rather than hidden or treated as a new alpha source.

## Exact comparable fixed-capital results (CAGR proxy %, monthly-sampled max drawdown %)

| vintage | Ridge100 CAGR | XGB100 CAGR | **Ridge75/XGB25 CAGR** | Ridge100 max DD | XGB100 max DD | **Ridge75/XGB25 max DD** |
|---|---:|---:|---:|---:|---:|---:|
| repeat1 | 17.12 | 19.58 | **19.50** | -31.66 | -52.68 | **-25.66** |
| repeat2 | 17.15 | 22.17 | **19.93** | -31.66 | -41.88 | **-24.47** |
| repeat3 | 17.12 | 31.91 | **22.37** | -31.66 | -46.84 | **-25.66** |

Capital output **does not prove positive live alpha**. XGB still has higher historical CAGR in repeat2/3; static overlay has a narrower observed CAGR range, and DD on *monthly samples* lower than either standalone in all 3 replays. These are NOT the complete Hybrid24 portfolio CAGR, nor valid unseen out-of-sample tests; slippage, market impact, taxes, constrained liquidity, intramonth stop/risk engine absent. Adjusted Yahoo OHLC and modern ETF survivorship introduce more uncertainty.

## Cross-vintage sensitivity of live portfolio allocation

Average exact target-weight overlap `1 - 0.5 Σ |weights_repeatA - weights_repeatB|`, 113 dates:

| Vintage pair | Ridge100 | XGB100 | 75/25 overlay |
|---|---:|---:|---:|
| repeat1 vs repeat2 | 99.12% | 45.13% | **85.62%** |
| repeat1 vs repeat3 | 100.00% | 56.64% | **89.16%** |
| repeat2 vs repeat3 | 99.12% | 46.90% | **86.06%** |

Allocation stability is **not** proof the underlying XGB model or its predicted Top1 ranking has become stable. Unstable sleeve remains capped to only 25% of notional, not eliminated.

Mean *absolute difference* in corresponding portfolio **monthly logarithmic returns** across vintage pairs:
- Ridge100 ~0.00000011–0.0000228
- XGB100 ~0.02257–0.03797
- Core75/Satellite25 **~0.005625–0.009471**, roughly one quarter of XGB's vintage-level monthly return sensitivity, consistent with the sleeve weight.

Paired 3-calendar-month moving block bootstrap on 112 matched monthly dates, 10,000 draws, vintage averaged within date (unadjusted 95% descriptive CI):
- CORE75 − Ridge100 mean log monthly return difference **+0.002430**, CI **[-0.001985,+0.006297]**.
- CORE75 − XGB100 mean log monthly return difference **−0.002620**, CI **[-0.014704,+0.011417]**.

Both intervals contain zero: **no statistically convincing return superiority**, especially after the many historical experiments in this research line.

## Integrity checks and specialists' lenses

Source `l2f_portfolio.py`; independent audit `l2f_independent_audit.py` provided in the conversation reproducibility ZIP; source input SHA pinned by L2-E and prior work.

- **ML / causality**: all selections at signal date from frozen learner predictions, separate by vintage; no future returns in allocation.
- **Quant statistics**: matched monthly data, three vintages treated as near-identical copies rather than three market repetitions, block bootstrap with uncertainty, no p-hacking declaration.
- **Portfolio/risk**: notional-level 75/25 with portfolio drift, exact monthly self-financing fee, turn counts, month-sampled DD vs actual intramonth uncertainty, no guarantee in catastrophic gaps.
- **Execution**: 0.1% per traded notional for both buy/sell; no terminal phantom trade; first buy and last sell charged; no negative positions.
- **Independent QA:** `l2f_independent_audit.py` **PASS**; recomputes 9 portfolio books × 113 execution dates, 112 monthly returns each, target allocation invariants, cost conservation, CAGR from final wealth, per-pair exact total-variation weights. Prior terminal overcharge quantitatively reconciled.

## Conclusions and recommended next engineering gate

This is a **useful risk-control prototype**: substantially tighter *allocation/return* robustness than pure XGB and lower retrospectively observed sampled DD, with some opportunity capture beyond 100% Ridge. It **does not meet** the earlier objective of an inherently stable nonlinear ranker and does not prove positive future excess returns. Do not promote or tune 75/25 on Original149. A true next model-development phase requires a preregistered **training-level stability method** (regularized nonlinear/student-ranker with a training perturbation consistency penalty, or controlled bootstrap-of-training vintages) on a newly obtained *prospective* period. Full Hybrid24 risk and portfolio replay must be separately wired and checked before any production substitution.
