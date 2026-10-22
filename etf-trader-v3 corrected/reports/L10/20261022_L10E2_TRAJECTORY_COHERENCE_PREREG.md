# L10.E2 — post-ML trajectory coherence veto (frozen BEFORE evaluation)

Date: 2026-10-22. Scope: 149 unchanged original ETFs, 500 canonical 24-name baskets and 101 mature monthly evaluation signals, 2018–2026. All historical vintages heavily explored: descriptive research, **not virgin holdout**.

## Causal intervention and rationale

**CORRECTED Pairwise127 ML rank is the authoritative ordering.** Only audit original top-3 selections *after* ML ranking, and only modify suspicious selected slots. Maintain same slot weights [0.5,0.3,0.2] and highest original ML-ranked unflagged replacement among ranks 4–24. No Top5 generator yet; no new fit, no CAGR, no re-ranking analytically.

One isolated *additional* condition relative to L10.E1: distinguish a fairly coherent 21-day negative trajectory from choppy/reversing 21-day corrections using **Kaufman efficiency ratio**, computed from the last 21 daily adjusted log price changes:

`coherence21 = |log(C_t/C_{t-21})| / sum_{j=0}^{20} |log(C_{t-j}/C_{t-j-1})|`

Complete 22 trading-day observations required; if denominator ≤1e-12 or missing, fail closed (do not veto).

New E2 veto iff **all three**:
- E1 condition: 21d log momentum < 0,
- E1 condition: 63-trading-day rolling high drawdown ≤ -10%,
- one NEW E2 causal trajectory-coherence condition: `coherence21 >= 0.45`.

Threshold 0.45 chosen a priori as a descriptive "net displacement is at least 45% of gross movement" heuristic, *not* based on evaluated 2018–2026 outcomes. No parameter/horizon optimization; no other use of coherence to rank ETFs. E1 and E2 must be recalculated identically on the same 101 months; E2 is a strict subset of E1's warnings. Evaluate signal quality on distinct initially selected ETF-months and actual substitution changes within 500 original baskets.

## Primary acceptance hierarchy (all measured)

1. **Avoid erroneously excluding actual future basket winners** compared with E1. Also compare vs original unmodified CORRECTED; keep false-veto cost primary.
2. Retain or improve protection against *future absolute 21D loss ≥10%*, including flagged-event precision and original portfolio's future loss weight.
3. Preserve weighted future-rank, winner weight, 21D weighted regret, 21D weighted return and fraction of baskets changed. Include per-year results and month-level six-calendar-month circular paired block bootstrap (6000 resamples) for both E2−BASE and E2−E1.
4. Maintain 149 ticker×101 signals data parity, 500 baskets×24 frozen SHA `36a45916b5d8191f3ccd206f39bf3fd3f1ed4bcaffd474e352b69c598f2b6a5e`, input certified OHLCV run 39482809691, original CORRECTED scores run 39700865721, mature forward return labels solely *after* scoring; all features as-of t. Test synthetic future-perturbation invariance.
5. No promotion even on promising exploratory results unless newer untouched source vintage independently confirms them. Never change original V2, previously frozen V3 or L10.E1 source.

IMPORTANT: Comparing E2 with a previously-rejected E1 is only an attribution test. Reducing harm versus E1 by avoiding most interventions does not establish benefit versus BASE. Report absolute number of interventions/actual winners removed, not just ratios. If reduced loss exposure disappears, record the hypothesis as failed. No economic test if functional gate fails.
