# Evidence V1 — Allocation v1: frozen LTR EW5

Status: **PREREGISTERED BEFORE EXECUTION**

## Context

The deterministic reranker line on Original149 is closed after four preregistered failures (v1–v4). Evidence V1 still supports the frozen LTR retriever as a top-k retriever: on the certified 114-period development window the full-universe 21d winner is present in frozen Top5 on 32/114 dates and in Top10 on 47/114 dates.

The new hypothesis is therefore portfolio-level rather than single-winner prediction:

> a simple allocation across the frozen LTR Top5 can monetize retrieval recall and reduce single-name selection error without relying on uncalibrated score margins.

This is not a K sweep. `K=5` is fixed before execution because Top5 is an already validated retriever checkpoint and offers a direct breadth/recall trade-off without introducing Top10 dilution as a second configuration.

## Frozen inputs

- Development universe: frozen Original149 only; it is burned and cannot provide promotion evidence.
- Retriever: frozen Retriever LTR v1 checkpoint; no retraining.
- Allocation membership: `evidence_v1/checkpoints/retriever_ltr_v1/TOP5.csv`.
- Top1 comparator: highest frozen `LTR_SCORE` within the same Top5.
- Return source: frozen Original149 panel rebuilt from `evidence_v1/data/original149/` and source-only baseline builder.
- Return horizon: `fwd_ret_21`, identical open-to-open 21-trading-day proxy used by the existing retriever/reranker diagnostics.
- Holdout70 is not used.

## Allocation — single frozen configuration

`LTR-EW5`:
- at every evaluation signal date, hold exactly the five frozen LTR Top5 names;
- weight each name `20%`;
- no score-proportional weighting;
- no confidence/margin filter;
- no volatility targeting;
- no cluster caps;
- no K tuning;
- rebalance on each frozen monthly signal date.

The monthly return proxy is the arithmetic mean of the five constituent `fwd_ret_21` values.

## Comparators

On exactly the same dates and return definitions:

1. **Frozen LTR Top1** — return of the highest frozen `LTR_SCORE` name.
2. **Eligible-universe EW** — equal-weight mean `fwd_ret_21` across all available frozen LTR OOS candidate rows on that signal date. This is a passive cross-sectional benchmark, not a selectable model configuration.

The evaluator must fail closed unless it reproduces the certified frozen retriever values:
- 114 evaluation dates;
- LTR Top1 CAGR proxy `0.220630708412056`;
- Top5 contains the global 21d winner on `32/114` dates.

## Evaluation window

`2017-01-01 <= signal_date < 2026-07-01`, exactly 114 monthly periods.

Report:
- full 2017–2026;
- 2017–2022;
- 2023–2026.

## Portfolio metrics

For Top1, EW5, and universe-EW:
- geometric CAGR using 12 periods/year;
- annualized volatility (`std(monthly) * sqrt(12)`);
- Sharpe with zero risk-free rate;
- max drawdown on the compounded monthly equity curve;
- Calmar ratio;
- positive-period rate;
- best/worst period;
- mean period return.

EW5 membership turnover is diagnostic only and is defined as `1 - |Top5_t ∩ Top5_{t-1}| / 5`, ignoring intra-period weight drift.

No transaction-cost assumption is part of the primary gate in v1 because the existing Evidence V1 comparators are gross-return development evidence. Cost sensitivity can only be added later as a separately preregistered implementation test if the allocation architecture passes.

## Primary advancement rule — frozen before execution

Allocation v1 advances on the burned development set only if **all three** conditions hold on the full 114-period window:

1. `CAGR(EW5) > CAGR(LTR Top1)`;
2. `MaxDrawdown(EW5) >= MaxDrawdown(LTR Top1)` (less negative / no worse drawdown);
3. `CAGR(EW5) > CAGR(eligible-universe EW)`.

Subperiod performance, Sharpe, Calmar, turnover and other diagnostics cannot override this rule.

## Decision consequences

### If v1 passes

- retain `K=5` fixed;
- do not sweep K on Original149;
- next allowed step is a separately preregistered **sizing/risk-control** hypothesis on the same frozen Top5 (for example, a single risk-balancing rule), not another retriever/reranker variant;
- before any final promotion claim, a new disjoint Holdout-B must be frozen and tested once.

### If v1 fails

- do not try Top3/Top10 merely because EW5 failed;
- treat simple equal-weight top-k allocation as rejected;
- inspect diagnostics and require a genuinely new portfolio hypothesis before any further allocation test.

## Frozen source

Executed evaluator path:

`evidence_v1/src/allocation_v1_ltr_ew5.py`

Git blob:

`0525cd787681d97a5c7134c73116d91ea0aa3e7d`
