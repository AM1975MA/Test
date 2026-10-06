# Evidence V1 — Allocation v2 causal expert blend

Status: **PREREGISTERED BEFORE EXECUTION**

## Hypothesis

Allocation v1 established a genuine concentration/diversification trade-off: frozen LTR Top1 had higher full-window CAGR, while frozen LTR-EW5 had materially lower volatility/drawdown and better 2023–2026 performance. The observed subperiod split is diagnostic only and must not be converted into a hard-coded calendar regime.

The single v2 hypothesis is instead causal and strategy-internal:

> allocate continuously between the two already-frozen experts according to their relative compounded skill over the most recent 12 **matured** OOS periods.

No market-state feature, date breakpoint, LTR margin, new ranker, K choice or parameter sweep is allowed.

## Frozen experts

1. `Top1`: highest frozen LTR score from `evidence_v1/checkpoints/retriever_ltr_v1/TOP5.csv`.
2. `EW5`: equal 20% weight across the same frozen Top5.

Both expert return streams are reconstructed for the full frozen OOS checkpoint beginning in 2011 using the same `fwd_ret_21` open-to-open proxy and frozen Original149 panel.

No retraining occurs.

## Causal maturity gate

At current signal date `t`, a historical expert period `j` may enter the meta allocator only if:

- `signal_date_j < t`, and
- `exit_date_21_j < t`.

Thus a prior signal whose 21d outcome has not fully matured is invisible.

Take the 12 most recent rows satisfying both conditions.

Because the frozen checkpoint starts in 2011, the 2017–2026 evaluation is expected to have at least 12 mature rows at every date. The source contains a 50/50 bootstrap for general completeness, but the evaluation must fail closed if that bootstrap is actually used in the 114-period window.

## Single frozen allocation rule

For each expert `i ∈ {Top1, EW5}` over the 12 mature rows:

`wealth_i = Π_j (1 + r_{i,j})`

Then:

`weight_i = wealth_i / (wealth_Top1 + wealth_EW5)`

Current meta return:

`r_meta,t = weight_Top1,t * r_Top1,t + weight_EW5,t * r_EW5,t`

Properties fixed ex ante:
- lookback: exactly **12 mature periods**;
- continuous weights, no hard switch;
- long-only;
- no leverage;
- weights sum to one;
- no temperature / learning-rate parameter;
- no volatility scaling;
- no market features;
- no score or margin confidence.

Executed source path:
`evidence_v1/src/allocation_v2_causal_expert_blend.py`

Frozen Git blob:
`6ac01ebacf7af9795bba660465bcef057e5a12b6`

## Evaluation

Exactly 114 dates:
`2017-01-01 <= signal_date < 2026-07-01`.

The evaluator must reproduce before judging v2:
- frozen Top1 CAGR: `0.220630708412056`;
- frozen EW5 CAGR: `0.20360068077564386`;
- frozen Top1 max drawdown: `-0.5147222930936663`.

Report full window plus 2017–2022 and 2023–2026 diagnostics.

Metrics:
- CAGR;
- annualized volatility;
- Sharpe rf0;
- max drawdown;
- Calmar;
- positive period rate;
- best/worst period;
- mean return;
- mean/median/min/max Top1 weight;
- mean absolute month-to-month Top1 weight change.

## Primary advancement rule — frozen before execution

Allocation v2 advances on burned Original149 development evidence only if BOTH hold on the full 114-period window:

1. `CAGR(meta) > CAGR(frozen Top1)`;
2. `MaxDrawdown(meta) >= MaxDrawdown(frozen Top1)`.

Subperiod performance and all other metrics are diagnostic only and cannot override this rule.

## Consequences

### If v2 passes

- no further tuning on Original149;
- freeze a **new disjoint Holdout-B** before observing performance;
- execute one promotion test only, using this exact frozen meta rule.

### If v2 fails

- do not sweep 6/9/18/24-month lookbacks;
- do not introduce temperature, hard switching, a 2023 date rule or market-regime features ex post;
- stop adaptive-allocation tuning on Original149 and reassess the architecture before any new test.

Holdout70 remains burned and is not used.
