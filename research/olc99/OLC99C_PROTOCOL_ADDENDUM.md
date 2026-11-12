# OLC99C — Native economic label for Top10 instead of price-only outcome

**Exploratory follow-up registered after OLC99A and B failed, before OLC99C outcomes; NOT independent validation.**

The originally registered Top10 model learns next-month opening-to-opening relative returns, but its selections are evaluated after portfolio delays, V6 and FAST_LOCK3. This experiment isolates that target mismatch without altering candidate features, hyperparameters or account execution:

1. Run unchanged OLC19 context/50-50/DELAY3/FAST_LOCK3 at legacy fee .001 and save full pre-trade accounting snapshots at each monthly event. Verify bitwise parity with OLC19 native full replay.
2. At every event clone that same **OLC19 pre-trade state** ten times. For each original FUSION Top10 candidate run a single-ETF (`d1=d2`, weight=1) DELAY3 month to next event with identical future OHLC, costs, stops and frozen V6. Store its log-return relative to median of the ten candidate counterfactual returns. The label is matched-state simulator-relative economic utility, not an estimate of exogenous market impact or investable oracle.
3. Train the same one-model-per-market prequential Ridge with original twelve pre-signal features, alpha 100, month weights 1/10, clipped training labels +-2500 logbp, >=24 prior matured months, cutoff `event_index<=current-2`; predict candidates within the **same original FUSION Top10**. Combine 80% contextual rank +20% predicted native utility rank. No other variants, tuning, regimes or policy selection.
4. Replay original OLC19 native selection changed solely by this Top10 reranking, with DELAY3/FAST_LOCK3/50-50 and fees .001/.003; compare against unchanged context same timing. Measure 2021-24 FULL and annual, maxdd, Top2 changes and paired descriptive bootstrap. Do not optimize allocations on this follow-up.

Retrospective 2019-Jul2026 already mined; do not promote even if historically successful without genuinely future data.