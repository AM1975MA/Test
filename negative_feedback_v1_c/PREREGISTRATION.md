# ETF_TRADER_NEGATIVE_FEEDBACK_V1 — NF_V1_C_CONFIDENCE_FEEDBACK

Status: PREREGISTERED BEFORE RESULT OBSERVATION  
Date: 2026-10-03

## Hypothesis

The ex-post matured ranking error can be used as a causal negative-feedback signal to modulate **risk gain only**, without changing ETF_trader's ranking, Top1/Top2 identities, score matrix, margin, or allocation weight1.

The objective is not to improve CAGR ex post. The objective is to reduce the economic dispersion caused by microscopic raw-data perturbations while retaining most of the baseline economic return and not worsening risk-adjusted performance materially.

## Frozen datasets

Use exactly the three frozen Yahoo/yfinance perturbation snapshots from workflow run `37121749852`:

- `_repeat1`
- `_repeat2`
- `_repeat3`

No new market-data download is permitted in this experiment.

## Frozen productive pipeline

Use the same canonical source-only ETF_trader V2 / Stage19 source chain and the same pinned environment already hash-gated in NF_V1_A/B.

Repeat2 baseline parity gate:

`CAGR = 0.30843704925646037`

with absolute tolerance `< 1e-12`.

## Causal feedback state

At each signal date, compute the canonical Stage19 score ranking. For each historical signal date whose 63-session target has fully matured (`exit_date_63 < current_signal_date`), compute cross-sectional pairwise ranking accuracy against the matured `HYBRID_TARGET`.

Maintain an EWMA reliability state:

`q_t = (1-alpha) * q_{t-1} + alpha * accuracy_t`

with frozen `alpha = 1/3`.

Rationale: the target horizon is 63 trading sessions, approximately three monthly signal cohorts. This is a structural horizon choice, not a performance-tuned value.

Require at least 3 matured signal dates before feedback becomes active.

## Negative-feedback gain

Random pairwise ranking has accuracy 0.5. The controller may only reduce risk when matured reliability is below this null benchmark:

`gain_t = clip(2 * q_t, 0, 1)`

if feedback is active, otherwise `gain_t = 1`.

Thus:

- q >= 0.50 -> gain = 1.00
- q = 0.40 -> gain = 0.80
- q = 0.30 -> gain = 0.60

The controller can never increase canonical risk above baseline.

The gain is mapped to the same daily allocation interval used by the canonical producer (`entry_date:exit_date`), with later signal dates overwriting overlapping prior intervals exactly as `allocations_from_score` does.

## Invariants — mandatory fail-closed gates

NF_V1_C MUST NOT alter:

- Stage19 scores
- Top1 ticker
- Top2 ticker
- d1/d2 allocation arrays
- weight1
- margin
- model predictions
- Titanium
- MA3 panel

It may only multiply the canonical daily risky-gross state by a gain in [0,1].

Top1/Top2 and allocation arrays must be exactly identical between baseline and feedback replay for each snapshot.

## Primary metrics

Across the three frozen snapshots:

1. CAGR span in percentage points.
2. Mean CAGR retention versus baseline.
3. Mean MaxDD.
4. Mean Sharpe.
5. Feedback active fraction and mean active gain.
6. Exact decision-identity gate.

## Preregistered promising gate

NF_V1_C is `PROMISING` only if ALL conditions hold:

1. exact decision identity = PASS on all snapshots;
2. Repeat2 baseline parity = PASS;
3. feedback is actually active on at least one evaluation interval;
4. feedback CAGR span <= 75% of baseline CAGR span;
5. mean feedback CAGR >= 90% of mean baseline CAGR;
6. mean feedback MaxDD is no worse than mean baseline MaxDD;
7. mean feedback Sharpe is no more than 0.02 below mean baseline Sharpe.

Otherwise the current controller is `REJECT_NF_V1_C_CURRENT_CONTROLLER`.

CAGR improvement alone cannot promote the experiment.

## Anti-overfit rule

No alpha/gain/floor/window sweep is allowed after results are observed. Any later controller must be a separately named and preregistered experiment.
